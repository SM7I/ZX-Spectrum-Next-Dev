#!/usr/bin/env python3
"""
bmp2nxi.py - convert a BMP image to a ZX Spectrum Next .NXI picture (258x108)

Pure Python 3, no extra packages needed.

Usage:  python bmp2nxi.py [-t RRGGBB|none] [-d] [-n] [-k N] in.bmp out.nxi
  -t  colour that becomes transparent (default FF00FF); 32-bit BMPs with
      alpha < 128 are also transparent.
  -d  Floyd-Steinberg dithering (good for photos and gradients)
  -n  nearest-neighbour resizing instead of area averaging (good for pixel art)
  -k  palette refinement passes (default 6, 0 = off)

NXI layout (28376 bytes):
  0..511     256 palette entries x 2 bytes: RRRGGGBB, 0000000b
             entries 0-15 fixed system colours, entry 227 = E3 01 (transparent),
             no other entry may start with E3
  512..      pixel indices, column-major: pixel(x,y) = data[512 + x*108 + y]
Input: uncompressed 8/24/32-bit BMP (resized to 258x108 if another size).
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


def axis_weights(n_src, n_dst, nearest):
    """For each destination index, a list of (source index, weight)."""
    res = []
    if nearest or n_src <= n_dst:
        for d in range(n_dst):
            res.append([(min(n_src - 1, int((d + 0.5) * n_src / n_dst)), 1.0)])
    else:
        sc = n_src / n_dst
        for d in range(n_dst):
            a, b = d * sc, (d + 1) * sc
            lst = []
            for i in range(int(a), min(n_src - 1, int(b - 1e-9)) + 1):
                w = min(b, i + 1) - max(a, i)
                if w > 1e-9:
                    lst.append((i, w))
            res.append(lst)
    return res


def resample(img, iw, ih, key, nearest):
    """Area-average (or nearest) resample to WxH.
    Returns a list of (r,g,b) floats 0..255, or None for transparent pixels."""
    xw = axis_weights(iw, W, nearest)
    yw = axis_weights(ih, H, nearest)
    needed = sorted({i for lst in yw for i, _ in lst})
    hrows = {}
    for y in needed:                                  # horizontal pass
        base = y * iw
        row = []
        for lst in xw:
            sr = sg = sb = so = sw = 0.0
            for i, w in lst:
                r, g, b, a = img[base + i]
                sw += w
                if a >= 128 and not (key is not None and (r, g, b) == key):
                    sr += r * w; sg += g * w; sb += b * w; so += w
            row.append((sr, sg, sb, so, sw))
        hrows[y] = row
    out = []
    for lst in yw:                                    # vertical pass
        for x in range(W):
            sr = sg = sb = so = sw = 0.0
            for y, w in lst:
                a = hrows[y][x]
                sr += a[0]*w; sg += a[1]*w; sb += a[2]*w; so += a[3]*w; sw += a[4]*w
            if so <= 0 or so / sw < 0.5:
                out.append(None)
            else:
                out.append((sr / so, sg / so, sb / so))
    return out


def refine(centers, fixed, hist, iterations):
    """Lloyd/k-means refinement of generated palette centres (floats, 0..7 units).
    Fixed colours take part in the assignment but never move."""
    cols = [(c, hist[c], (c >> 6) & 7, (c >> 3) & 7, c & 7) for c in range(512) if hist[c]]
    nfix = len(fixed)
    for _ in range(iterations):
        allc = fixed + centers
        sums = [[0.0, 0.0, 0.0, 0.0] for _ in centers]
        for c, w, r, g, b in cols:
            best, bd = 0, 1e30
            for k, (pr, pg, pb) in enumerate(allc):
                d = (r-pr)**2 * 3 + (g-pg)**2 * 4 + (b-pb)**2 * 2
                if d < bd:
                    bd, best = d, k
            if best >= nfix:
                s = sums[best - nfix]
                s[0] += w*r; s[1] += w*g; s[2] += w*b; s[3] += w
        centers = [(s[0]/s[3], s[1]/s[3], s[2]/s[3]) if s[3] else c
                   for s, c in zip(sums, centers)]
    return centers


def convert(src, dst, key=(255, 0, 255), dither=False, nearest=False, kiter=6):
    iw, ih, img = load_bmp(src)
    if (iw, ih) != (W, H):
        print("note: %dx%d image resized to %dx%d (%s)" %
              (iw, ih, W, H, "nearest neighbour" if nearest else "area average"), file=sys.stderr)
    pix = resample(img, iw, ih, key, nearest)

    # histogram of the 9-bit colours, for building the palette
    hist = [0] * 512
    for p in pix:
        if p is not None:
            hist[code333(int(p[0]*7/255 + .5), int(p[1]*7/255 + .5), int(p[2]*7/255 + .5))] += 1

    pal = [None] * 256
    fixed = []
    for i in range(NFIXED):
        b0, b1 = FIXED_PAL[i*2], FIXED_PAL[i*2 + 1]
        pal[i] = ((b0 >> 5) << 6) | (((b0 >> 2) & 7) << 3) | (((b0 & 3) << 1) | (b1 & 1))
        fixed.append(((pal[i] >> 6) & 7, (pal[i] >> 3) & 7, pal[i] & 7))
    free = [i for i in range(NFIXED, 256) if i != TRANSP]          # 239 entries

    gen = median_cut(hist, len(free))
    centers = [(((c >> 6) & 7), ((c >> 3) & 7), (c & 7)) for c in gen]
    if kiter and centers:
        centers = refine([tuple(map(float, c)) for c in centers], fixed, hist, kiter)
    for i, (fr, fg, fb) in enumerate(centers):
        r, g, b = int(fr + .5), int(fg + .5), int(fb + .5)
        if ((r << 5) | (g << 2) | (b >> 1)) == 0xE3:               # avoid E3 first byte
            g = 1
        pal[free[i]] = code333(r, g, b)

    usable = [(i, (pal[i] >> 6) & 7, (pal[i] >> 3) & 7, pal[i] & 7)
              for i in range(256) if i != TRANSP and pal[i] is not None]
    cache = {}

    def nearest_idx(r, g, b):
        k = (int(r*16 + .5), int(g*16 + .5), int(b*16 + .5))
        v = cache.get(k)
        if v is None:
            best, bd = 0, 1e30
            for i, pr, pg, pb in usable:
                d = (r-pr)**2 * 3 + (g-pg)**2 * 4 + (b-pb)**2 * 2
                if d < bd:
                    bd, best = d, i
            cache[k] = v = best
        return v

    idx = [TRANSP] * (W * H)
    if not dither:
        for n, p in enumerate(pix):
            if p is not None:
                idx[n] = nearest_idx(p[0]*7/255, p[1]*7/255, p[2]*7/255)
    else:                                                          # Floyd-Steinberg, serpentine
        R = [p[0]*7/255 if p else 0.0 for p in pix]
        G = [p[1]*7/255 if p else 0.0 for p in pix]
        B = [p[2]*7/255 if p else 0.0 for p in pix]
        pc = {i: (pr, pg, pb) for i, pr, pg, pb in usable}
        for y in range(H):
            step = 1 if y % 2 == 0 else -1
            for x in (range(W) if step == 1 else range(W - 1, -1, -1)):
                n = y * W + x
                if pix[n] is None:
                    continue
                r = min(7.0, max(0.0, R[n])); g = min(7.0, max(0.0, G[n])); b = min(7.0, max(0.0, B[n]))
                k = nearest_idx(r, g, b)
                idx[n] = k
                er, eg, eb = r - pc[k][0], g - pc[k][1], b - pc[k][2]
                for dx, dy, f in ((step, 0, 7/16), (-step, 1, 3/16), (0, 1, 5/16), (step, 1, 1/16)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < W and yy < H:
                        m = yy * W + xx
                        if pix[m] is not None:
                            R[m] += er * f; G[m] += eg * f; B[m] += eb * f

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
            out[PAL_BYTES + x * H + y] = idx[y * W + x]
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s (%d bytes, %d palette colours generated)" % (dst, SIZE, len(gen)),
          file=sys.stderr)


def main(argv):
    key, files, dither, nearest, kiter, i = (255, 0, 255), [], False, False, 6, 1
    while i < len(argv):
        a = argv[i]
        if a == "-t" and i + 1 < len(argv):
            i += 1
            key = None if argv[i].lower() == "none" else tuple(bytes.fromhex(argv[i].zfill(6)))
        elif a == "-d":
            dither = True
        elif a == "-n":
            nearest = True
        elif a == "-k" and i + 1 < len(argv):
            i += 1
            kiter = int(argv[i])
        else:
            files.append(a)
        i += 1
    if len(files) != 2:
        print("usage: python bmp2nxi.py [-t RRGGBB|none] [-d] [-n] [-k N] in.bmp out.nxi\n"
              "  -t  transparent colour (default FF00FF)\n"
              "  -d  Floyd-Steinberg dithering (good for photos)\n"
              "  -n  nearest-neighbour resizing instead of area averaging (good for pixel art)\n"
              "  -k  palette refinement passes (default 6, 0 = off)", file=sys.stderr)
        return 1
    try:
        convert(files[0], files[1], key, dither, nearest, kiter)
    except (OSError, ValueError) as e:
        print("error:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
