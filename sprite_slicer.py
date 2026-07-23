# -*- coding: utf-8 -*-
"""
角色设定图自动切片工具
- 用 numpy 连通区域检测自动找到设定图中每个角色/表情的边界框
- 按行分组映射为 pose1-6 / action1-6 / face1-8
"""
import os
import numpy as np
from PIL import Image
from collections import deque


def _create_foreground_mask(img_array):
    """创建前景二值掩码：非透明 或 与背景色差异大的像素为前景"""
    h, w = img_array.shape[:2]
    if img_array.shape[2] == 4:
        # 有 alpha 通道：alpha > 10 为前景
        mask = img_array[:, :, 3] > 10
    else:
        # 无 alpha 通道：用四角像素的均值作为背景色，色差大的为前景
        corners = [
            img_array[0, 0, :3],
            img_array[0, -1, :3],
            img_array[-1, 0, :3],
            img_array[-1, -1, :3],
        ]
        bg = np.mean(corners, axis=0)
        diff = np.abs(img_array[:, :, :3].astype(int) - bg.astype(int))
        mask = np.sum(diff, axis=2) > 60
    return mask


def _find_connected_components(mask):
    """用 BFS 找连通区域，返回 [(min_x, min_y, max_x, max_y, area), ...]"""
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    components = []

    for y in range(h):
        for x in range(w):
            if mask[y, x] and not visited[y, x]:
                # BFS
                queue = deque([(x, y)])
                visited[y, x] = True
                min_x, min_y = x, y
                max_x, max_y = x, y
                area = 0

                while queue:
                    cx, cy = queue.popleft()
                    area += 1
                    if cx < min_x:
                        min_x = cx
                    if cx > max_x:
                        max_x = cx
                    if cy < min_y:
                        min_y = cy
                    if cy > max_y:
                        max_y = cy

                    # 检查4邻域
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            queue.append((nx, ny))

                if area >= 500:  # 过滤小噪点
                    components.append((min_x, min_y, max_x, max_y, area))

    return components


def _trim_transparent(img):
    """裁除图片四周的透明边缘"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    if arr.shape[2] == 4:
        alpha = arr[:, :, 3]
        rows = np.any(alpha > 10, axis=1)
        cols = np.any(alpha > 10, axis=0)
        if not rows.any() or not cols.any():
            return img
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        return img.crop((cmin, rmin, cmax + 1, rmax + 1))
    return img


def _group_by_rows(components, expected_rows=3):
    """按 Y 坐标聚类分组，返回 [[comp1, comp2, ...], [comp3, ...], ..."""
    if not components:
        return []

    # 按 Y 中心排序
    sorted_by_y = sorted(components, key=lambda c: (c[1] + c[3]) / 2)

    # 计算每个组件的 Y 中心
    y_centers = [(c[1] + c[3]) / 2 for c in sorted_by_y]

    # 用间隔聚类：找到 Y 中心的大跳跃点作为行分隔
    sorted_ys = sorted(y_centers)
    if len(sorted_ys) <= 1:
        return [sorted_by_y]

    # 计算相邻 Y 中心的间隔
    gaps = [sorted_ys[i + 1] - sorted_ys[i] for i in range(len(sorted_ys) - 1)]
    avg_gap = sum(gaps) / len(gaps) if gaps else 0

    # 间隔大于平均间隔2倍的点为行分隔
    threshold = max(avg_gap * 2, 50)
    split_points = [i + 1 for i, gap in enumerate(gaps) if gap > threshold]

    # 分组
    rows = []
    prev = 0
    for sp in split_points:
        rows.append(prev)
        prev = sp
    rows.append(prev)

    grouped = []
    for i, start in enumerate(rows):
        end = rows[i + 1] if i + 1 < len(rows) else len(sorted_ys)
        row_components = sorted_by_y[start:end]
        # 行内按 X 排序
        row_components.sort(key=lambda c: (c[0] + c[2]) / 2)
        grouped.append(row_components)

    return grouped


def slice_character_sheet(image_path, output_dir, bg_color=None, tolerance=30):
    """
    自动切片角色设定图，保存到 output_dir。

    参数:
        image_path: 设定图路径
        output_dir: 输出目录（sprites/）
        bg_color: 可选背景色 (R,G,B)，若提供则用色差判断前景
        tolerance: 背景色容差

    返回:
        (results, log_lines)
        results: [(name, path, width, height), ...]
        log_lines: [str, ...] 日志信息
    """
    log_lines = []
    log_lines.append(f"开始切片: {image_path}")

    img = Image.open(image_path).convert("RGBA")
    img_array = np.array(img)
    h, w = img_array.shape[:2]
    log_lines.append(f"图片尺寸: {w}x{h}")

    # 如果指定了背景色，用色差判断前景
    if bg_color:
        bg = np.array(bg_color[:3])
        diff = np.abs(img_array[:, :, :3].astype(int) - bg.astype(int))
        mask = np.sum(diff, axis=2) > tolerance * 3
    else:
        mask = _create_foreground_mask(img_array)

    fg_pixels = int(mask.sum())
    log_lines.append(f"前景像素数: {fg_pixels} ({fg_pixels / (h * w) * 100:.1f}%)")

    # 连通区域检测
    components = _find_connected_components(mask)
    log_lines.append(f"检测到 {len(components)} 个连通区域")

    if not components:
        log_lines.append("错误: 未检测到任何连通区域")
        return [], log_lines

    # 按行分组
    grouped = _group_by_rows(components, expected_rows=3)
    log_lines.append(f"分为 {len(grouped)} 行")

    # 精灵名称映射
    row_names = [
        [f"pose{i}" for i in range(1, 7)],      # 第1行: 6个pose
        [f"action{i}" for i in range(1, 7)],     # 第2行: 6个action
        [f"face{i}" for i in range(1, 9)],      # 第3行: 8个face
    ]

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for row_idx, row_comps in enumerate(grouped):
        if row_idx >= len(row_names):
            log_lines.append(f"第{row_idx + 1}行超出预期，跳过")
            continue

        names = row_names[row_idx]
        log_lines.append(f"第{row_idx + 1}行: 检测到 {len(row_comps)} 个区域, 预期 {len(names)} 个")

        for i, comp in enumerate(row_comps):
            if i >= len(names):
                log_lines.append(f"  第{row_idx + 1}行第{i + 1}个超出预期数量，跳过")
                continue

            min_x, min_y, max_x, max_y, area = comp
            name = names[i]

            # 裁剪
            crop = img.crop((min_x, min_y, max_x + 1, max_y + 1))
            # 裁除透明边缘
            crop = _trim_transparent(crop)

            # 保存
            out_path = os.path.join(output_dir, f"{name}.png")
            crop.save(out_path)
            cw, ch = crop.size
            results.append((name, out_path, cw, ch))
            log_lines.append(f"  已保存: {name}.png ({cw}x{ch})")

    log_lines.append(f"切片完成: 共保存 {len(results)} 个精灵到 {output_dir}")
    return results, log_lines
