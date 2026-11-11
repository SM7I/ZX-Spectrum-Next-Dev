#!/usr/bin/env python3
"""
bmp2nxi.py - convert a BMP image to a ZX Spectrum Next .NXI picture (258x108)
(c) 2006 SM7I Projects

Usage:  python bmp2nxi.py [-t RRGGBB|none] in.bmp out.nxi
  -t  colour that becomes transparent (default FF00FF); 32-bit BMPs with
      alpha < 128 are also transparent.

NXI layout (28376 bytes):
  0..511     256 palette entries x 2 bytes: RRRGGGBB, 0000000b
             entries 0-15 fixed system colours, entry 227 = E3 01 (transparent),
             no other entry may start with E3
  512..      pixel indices, column-major: pixel(x,y) = data[512 + x*108 + y]
Input: uncompressed 8/24/32-bit BMP (scaled to 258x108 if another size).
"""
import struct
import sys

W, H = 258, 108
PAL_BYTES = 512
SIZE = PAL_BYTES + W * H          # 28376
TRANSP = 227
NFIXED = 16

FIXED_PAL = bytes([
    0x00,0x00, 0x01,0x00, 0x2a,0x01, 0xff,0x01,
    0x92,0x01, 0x25,0x01, 0x7b,0x01, 0xe4,0x01,
    0x59,0x00, 0x03,0x01, 0xfd,0x00, 0xf0,0x00,
    0xfc,0x01, 0xb7,0x00, 0x55,0x00, 0x17,0x00])


def load_bmp(path):
    """Return (width, height, pixels) with pixels = list of (r,g,b,a), top-down."""
    with open(path, "rb") as f:
        buf = f.read()
    if len(buf) < 54 or buf[:2] != b"BM":
        raise ValueError("not a BMP file")
    off, dib = struct.unpack_from("<II", buf, 10)
    w, h = struct.unpack_from("<ii", buf, 18)
    bpp, = struct.unpack_from("<H", buf, 28)
    comp, = struct.unpack_from("<I", buf, 30)
    ncol, = struct.unpack_from("<I", buf, 46)
    if dib < 40:
        raise ValueError("unsupported BMP header")
    topdown = h < 0
    h = abs(h)
    if w <= 0 or h <= 0:
        raise ValueError("bad BMP size")
    if comp != 0 and not (comp == 3 and bpp == 32):
        raise ValueError("compressed BMP not supported")
    if bpp not in (8, 24, 32):
        raise ValueError("only 8/24/32-bit BMP supported (got %d)" % bpp)
    pal = []
    if bpp == 8:
        ncol = ncol or 256
        p = 14 + dib
        for i in range(min(ncol, 256)):
            b, g, r = buf[p + i*4], buf[p + i*4 + 1], buf[p + i*4 + 2]
            pal.append((r, g, b, 255))
        pal += [(0, 0, 0, 255)] * (256 - len(pal))
    stride = (w * bpp + 31) // 32 * 4
    if off + stride * h > len(buf):
        raise ValueError("truncated BMP")
    pixels = []
    for y in range(h):
        row = off + stride * (y if topdown else h - 1 - y)
        for x in range(w):
            if bpp == 8:
                pixels.append(pal[buf[row + x]])
            elif bpp == 24:
                q = row + x*3
                pixels.append((buf[q+2], buf[q+1], buf[q], 255))
            else:
                q = row + x*4
                pixels.append((buf[q+2], buf[q+1], buf[q], buf[q+3]))
    return w, h, pixels


def to3(v):
    return (v * 7 + 127) // 255


def code333(r, g, b):
    return (r << 6) | (g << 3) | b


def median_cut(hist, maxn):
    """Median cut over the 512-bin histogram; returns list of 9-bit codes."""
    first = [c for c in range(512) if hist[c]]
    if not first:
        return []
    boxes = [first]
    pop = lambda bx: sum(hist[c] for c in bx)
    pops = [pop(first)]
    while len(boxes) < maxn:
        best, bch, bestscore = -1, 0, 0
        for i, bx in enumerate(boxes):
            if len(bx) < 2:
                continue
            br, bc = -1, 0
            for ch in range(3):
                vals = [(c >> (ch*3)) & 7 for c in bx]
                rng = max(vals) - min(vals)
                if rng > br:
                    br, bc = rng, ch
            if br <= 0:
                continue
            score = min(pops[i], 1000000) * (br + 1)
            if score > bestscore:
                bestscore, best, bch = score, i, bc
        if best < 0:
            break
        bx = sorted(boxes[best], key=lambda c: ((c >> (bch*3)) & 7, c))
        half = pops[best] // 2
        acc, split = 0, 1
        for k in range(len(bx) - 1):
            acc += hist[bx[k]]
            split = k + 1
            if acc >= half:
                break
        boxes[best], new = bx[:split], bx[split:]
        pops[best] = pop(boxes[best])
        boxes.append(new)
        pops.append(pop(new))
    out = []
    for bx in boxes:
        tot = sum(hist[c] for c in bx)
        sr = sum(hist[c] * ((c >> 6) & 7) for c in bx)
        sg = sum(hist[c] * ((c >> 3) & 7) for c in bx)
        sb = sum(hist[c] * (c & 7) for c in bx)
        out.append(code333((sr + tot//2)//tot, (sg + tot//2)//tot, (sb + tot//2)//tot))
    return out


def convert(src, dst, key=(255, 0, 255)):
    iw, ih, img = load_bmp(src)
    if (iw, ih) != (W, H):
        print("note: %dx%d image scaled to %dx%d (nearest neighbour)" % (iw, ih, W, H),
              file=sys.stderr)
    hist = [0] * 512
    opaque = [False] * (W * H)
    code = [0] * (W * H)
    for y in range(H):
        for x in range(W):
            r, g, b, a = img[(y * ih // H) * iw + (x * iw // W)]
            o = a >= 128
            if key is not None and (r, g, b) == key:
                o = False
            i = y * W + x
            opaque[i] = o
            code[i] = code333(to3(r), to3(g), to3(b))
            if o:
                hist[code[i]] += 1

    pal = [None] * 256
    for i in range(NFIXED):
        b0, b1 = FIXED_PAL[i*2], FIXED_PAL[i*2 + 1]
        pal[i] = ((b0 >> 5) << 6) | (((b0 >> 2) & 7) << 3) | (((b0 & 3) << 1) | (b1 & 1))
    free = [i for i in range(NFIXED, 256) if i != TRANSP]          # 239 entries
    gen = median_cut(hist, len(free))
    for i, c in enumerate(gen):
        r, g, b = (c >> 6) & 7, (c >> 3) & 7, c & 7
        if ((r << 5) | (g << 2) | (b >> 1)) == 0xE3:               # avoid E3 first byte
            g = 1
        pal[free[i]] = code333(r, g, b)

    usable = [(i, pal[i]) for i in range(256) if i != TRANSP and pal[i] is not None]
    lut = {}
    for c in set(code[i] for i in range(W * H) if opaque[i]):
        r, g, b = (c >> 6) & 7, (c >> 3) & 7, c & 7
        best, bd = 0, 1 << 30
        for i, p in usable:
            pr, pg, pb = (p >> 6) & 7, (p >> 3) & 7, p & 7
            d = (r-pr)**2 * 3 + (g-pg)**2 * 4 + (b-pb)**2 * 2
            if d < bd:
                bd, best = d, i
        lut[c] = best

    out = bytearray(SIZE)
    for i in range(256):
        p = pal[i]
        if p is None:
            continue
        out[i*2] = (((p >> 6) & 7) << 5) | (((p >> 3) & 7) << 2) | ((p & 7) >> 1)
        out[i*2 + 1] = p & 1
    out[0:32] = FIXED_PAL
    out[TRANSP*2], out[TRANSP*2 + 1] = 0xE3, 0x01
    for y in range(H):
        for x in range(W):
            i = y * W + x
            out[PAL_BYTES + x * H + y] = lut[code[i]] if opaque[i] else TRANSP
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s (%d bytes, %d palette colours generated)" % (dst, SIZE, len(gen)),
          file=sys.stderr)


def main(argv):
    key, files, i = (255, 0, 255), [], 1
    while i < len(argv):
        if argv[i] == "-t" and i + 1 < len(argv):
            i += 1
            key = None if argv[i].lower() == "none" else tuple(bytes.fromhex(argv[i].zfill(6)))
        else:
            files.append(argv[i])
        i += 1
    if len(files) != 2:
        print("usage: python bmp2nxi.py [-t RRGGBB|none] in.bmp out.nxi", file=sys.stderr)
        return 1
    try:
        convert(files[0], files[1], key)
    except (OSError, ValueError) as e:
        print("error:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
