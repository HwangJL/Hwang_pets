# -*- coding: utf-8 -*-
"""切片 Q版参考图.png，保存各角色精灵到 sprites/ 目录"""
import os
from PIL import Image

SRC = r"C:\Users\L.Hwang\Downloads\Q版参考图.png"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites")
os.makedirs(OUT, exist_ok=True)

img = Image.open(SRC)

# 各切片区域，根据连通区域分析结果确定
# (name, left, top, right, bottom)
SPRITES = [
    # --- 第2行：6个全身角色 (y ~85-364) ---
    ("pose1",  330,  80,  500, 370),   # 左1
    ("pose2",  505,  80,  675, 370),   # 左2
    ("pose3",  685,  80,  850, 370),   # 左3
    ("pose4",  865,  80, 1030, 370),   # 左4
    ("pose5", 1045,  80, 1210, 370),   # 左5
    ("pose6", 1205,  80, 1380, 370),   # 左6

    # --- 第3行：6个动作角色 (y ~446-687) ---
    ("action1",  55, 445,  210, 690),  # 左1
    ("action2", 245, 445,  405, 690),  # 左2
    ("action3", 470, 445,  650, 690),  # 左3
    ("action4", 700, 445,  880, 690),  # 左4
    ("action5", 900, 445, 1070, 690),  # 左5
    ("action6", 1100, 445, 1380, 690), # 左6

    # --- 第4行：8个表情头像 (y ~779-923) ---
    ("face1",  40, 770,  210, 935),
    ("face2", 215, 770,  390, 935),
    ("face3", 385, 770,  560, 935),
    ("face4", 570, 770,  745, 935),
    ("face5", 745, 770,  920, 935),
    ("face6", 910, 770, 1085, 935),
    ("face7",1075, 770, 1245, 935),
    ("face8",1235, 770, 1390, 935),
]

for name, l, t, r, b in SPRITES:
    crop = img.crop((l, t, r, b))
    # 裁去背景色边缘，保留透明背景
    crop.save(os.path.join(OUT, f"{name}.png"))
    print(f"Saved {name}.png  ({r-l}x{b-t})")

print(f"\nDone! {len(SPRITES)} sprites saved to {OUT}")
