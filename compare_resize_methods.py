#!/usr/bin/env python3
"""
縮小方法の比較スクリプト
LANCZOS、NEAREST、LANCZOS+シャープ化の3種類をAtkinsonディザリングと組み合わせて比較する
"""

import sys
import os
import numpy as np
from PIL import Image, ImageFilter
from sklearn.cluster import KMeans


def quantize_to_9bit(colors):
    return np.round(colors / 255.0 * 7).astype(int)


def dequantize_from_9bit(quantized_colors):
    return np.round(quantized_colors / 7.0 * 255).astype(np.uint8)


def select_8_colors_from_image(image):
    img_array = np.array(image.convert('RGB'), dtype=float)
    pixels = img_array.reshape(-1, 3)
    quantized = quantize_to_9bit(pixels)
    kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
    kmeans.fit(quantized)
    return dequantize_from_9bit(kmeans.cluster_centers_)


def find_closest_color(pixel, palette):
    distances = np.sum((palette.astype(float) - pixel) ** 2, axis=1)
    idx = np.argmin(distances)
    return idx, palette[idx].astype(float)


def atkinson_dithering(image, palette):
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err / 8
    return out


def resize_lanczos(image, target_w, target_h):
    """LANCZOS（高品質縮小）"""
    return image.resize((target_w, target_h), Image.LANCZOS)


def resize_nearest(image, target_w, target_h):
    """NEAREST（単純間引き）"""
    return image.resize((target_w, target_h), Image.NEAREST)


def resize_lanczos_sharpen(image, target_w, target_h):
    """LANCZOS + シャープ化"""
    resized = image.resize((target_w, target_h), Image.LANCZOS)
    return resized.filter(ImageFilter.SHARPEN)


RESIZE_METHODS = [
    ('lanczos', resize_lanczos),
    ('nearest', resize_nearest),
    ('lanczos_sharpen', resize_lanczos_sharpen),
]


def process_image(input_path):
    img = Image.open(input_path)
    base = os.path.splitext(input_path)[0]
    w, h = img.size
    target_w = w
    target_h = h // 2
    print(f"入力: {w}x{h} → 縦半分: {target_w}x{target_h}")

    # パレット選択（LANCZOSベース）
    img_ref = resize_lanczos(img, target_w, target_h)
    print("8色パレット選択中...")
    palette = select_8_colors_from_image(img_ref)

    for name, resize_func in RESIZE_METHODS:
        print(f"{name} 処理中...")
        img_resized = resize_func(img, target_w, target_h)
        dithered = atkinson_dithering(img_resized, palette)
        result_full = np.repeat(dithered, 2, axis=0)
        out_path = f"{base}_resize_{name}.png"
        Image.fromarray(result_full).save(out_path)
        print(f"  → {out_path}")

    print("完了")
    print("\n推奨: LANCZOS（3つともほぼ同じ結果）")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"使い方: python3 {sys.argv[0]} <入力画像>")
        sys.exit(1)

    process_image(sys.argv[1])
