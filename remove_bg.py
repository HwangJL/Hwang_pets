# -*- coding: utf-8 -*-
"""将 sprites 目录下所有图片的背景色替换为透明"""
import os
from PIL import Image

SPRITES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
BG_COLOR = (253, 237, 173)  # 背景色
TOLERANCE = 25  # 颜色容差

for fname in sorted(os.listdir(SPRITES_DIR)):
    if not fname.endswith(".png"):
        continue
    path = os.path.join(SPRITES_DIR, fname)
    img = Image.open(path).convert("RGBA")
    arr = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = arr[x, y]
            if (abs(r - BG_COLOR[0]) < TOLERANCE and
                abs(g - BG_COLOR[1]) < TOLERANCE and
                abs(b - BG_COLOR[2]) < TOLERANCE):
                arr[x, y] = (0, 0, 0, 0)
    img.save(path)
    print(f"Processed {fname}")

print("Done!")
