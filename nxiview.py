#!/usr/bin/env python3
"""
nxiview.py - viewer for ZX Spectrum Next .NXI pictures (258x108)
(c) 2026 SM7I Projects

Usage:  python nxiview.py [file.nxi]
Keys:   O open   + / -  (or mouse wheel) zoom   T toggle transparency checkerboard   Esc quit

Layout: 512-byte palette (256 x 2 bytes: RRRGGGBB, 0000000b), then 258x108 pixel
indices stored column by column: pixel(x,y) = data[512 + x*108 + y].
Index 227 (palette E3 01) is transparent.
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

W, H = 258, 108
PAL_BYTES = 512
SIZE = PAL_BYTES + W * H          # 28376
TRANSP = 227


def decode(data, checker=True):
    """Return rows of '#rrggbb' strings (top-down)."""
    pal = []
    for i in range(256):
        b0, b1 = data[i*2], data[i*2 + 1]
        r, g, b = b0 >> 5, (b0 >> 2) & 7, ((b0 & 3) << 1) | (b1 & 1)
        pal.append("#%02x%02x%02x" % (r*255//7, g*255//7, b*255//7))
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            idx = data[PAL_BYTES + x * H + y]
            if idx == TRANSP and checker:
                row.append("#c8c8c8" if ((x >> 2) + (y >> 2)) & 1 else "#909090")
            else:
                row.append(pal[idx])
        rows.append(row)
    return rows


class Viewer:
    def __init__(self, root):
        self.root = root
        self.data = None
        self.path = ""
        self.scale = 3
        self.checker = True
        self.photo = None
        self.canvas = tk.Canvas(root, bg="#555555", highlightthickness=0,
                                width=W * self.scale, height=H * self.scale)
        self.canvas.pack(fill="both", expand=True)
        root.bind("<Key>", self.on_key)
        root.bind("<MouseWheel>", lambda e: self.set_scale(self.scale + (1 if e.delta > 0 else -1)))
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.update_title()

    def update_title(self):
        if self.data:
            self.root.title("NXI Viewer (c) 2026 SM7I Projects - %s  (%dx%d, x%d)" % (os.path.basename(self.path), W, H, self.scale))
        else:
            self.root.title("NXI Viewer (c) 2026 SM7I Projects - press O to open a file")

    def load(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            messagebox.showerror("NXI Viewer", "Cannot open file:\n%s" % e)
            return
        if len(data) != SIZE:
            messagebox.showerror("NXI Viewer",
                                 "Not a valid NXI file (size must be exactly %d bytes, got %d)." % (SIZE, len(data)))
            return
        self.data, self.path = data, path
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        self.update_title()
        if not self.data:
            return
        rows = decode(self.data, self.checker)
        img = tk.PhotoImage(width=W, height=H)
        img.put(" ".join("{" + " ".join(r) + "}" for r in rows))
        self.photo = img.zoom(self.scale, self.scale)     # integer zoom = pixel replication
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_image(max(0, (cw - W*self.scale)//2), max(0, (ch - H*self.scale)//2),
                                 image=self.photo, anchor="nw")

    def set_scale(self, s):
        s = max(1, min(16, s))
        if s != self.scale:
            self.scale = s
            self.canvas.config(width=W * s, height=H * s)
            self.root.geometry("")            # let the window resize to fit
            self.redraw()

    def on_key(self, e):
        k = e.keysym.lower()
        if k == "o":
            p = filedialog.askopenfilename(filetypes=[("NXI pictures", "*.nxi"), ("All files", "*.*")])
            if p:
                self.load(p)
        elif k == "t":
            self.checker = not self.checker
            self.redraw()
        elif k in ("plus", "equal", "kp_add"):
            self.set_scale(self.scale + 1)
        elif k in ("minus", "kp_subtract"):
            self.set_scale(self.scale - 1)
        elif k == "escape":
            self.root.destroy()


def main():
    root = tk.Tk()
    v = Viewer(root)
    if len(sys.argv) > 1:
        v.load(sys.argv[1])
    root.mainloop()


if __name__ == "__main__":
    main()
