#!/usr/bin/env python3
"""
縦長ピクセル化方法の比較スクリプト
方法A（先に縦半分→ディザリング→縦2倍）と
方法B（ディザリング→2行ずつ同じ色）を比較する
"""

import sys
import os
import numpy as np
from PIL import Image
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


def floyd_steinberg_dithering(image, palette):
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            if x + 1 < w:
                img[y, x+1] += err * 7/16
            if y + 1 < h:
                if x > 0:
                    img[y+1, x-1] += err * 3/16
                img[y+1, x] += err * 5/16
                if x + 1 < w:
                    img[y+1, x+1] += err * 1/16
    return out


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


def method_a(image, palette, dither_func):
    """方法A: 先に縦半分 → ディザリング → 縦2倍"""
    w, h = image.size
    img_half = image.resize((w, h // 2), Image.LANCZOS)
    dithered = dither_func(img_half, palette)
    return np.repeat(dithered, 2, axis=0)


def method_b(image, palette, dither_func):
    """方法B: 縮小（縦長維持）→ ディザリング → 2行ずつ同じ色"""
    w, h = image.size
    img_resized = image.resize((w, h), Image.LANCZOS)
    dithered = dither_func(img_resized, palette)
    # 2行ずつ同じ色
    result = dithered.copy()
    for y in range(0, h - 1, 2):
        result[y + 1] = result[y]
    return result


def process_image(input_path):
    img = Image.open(input_path)
    base = os.path.splitext(input_path)[0]
    print(f"入力: {img.size[0]}x{img.size[1]}")

    # パレット選択（方法Aベース）
    w, h = img.size
    img_half = img.resize((w, h // 2), Image.LANCZOS)
    print("8色パレット選択中...")
    palette = select_8_colors_from_image(img_half)

    dithers = [
        ('atkinson', atkinson_dithering),
        ('floyd-steinberg', floyd_steinberg_dithering),
    ]

    for name, func in dithers:
        # 方法A
        print(f"{name} 方法A 処理中...")
        result_a = method_a(img, palette, func)
        path_a = f"{base}_{name}_methodA.png"
        Image.fromarray(result_a).save(path_a)
        print(f"  → {path_a}")

        # 方法B
        print(f"{name} 方法B 処理中...")
        result_b = method_b(img, palette, func)
        path_b = f"{base}_{name}_methodB.png"
        Image.fromarray(result_b).save(path_b)
        print(f"  → {path_b}")

    print("完了")
    print("\n推奨: 方法A（先に縦半分）— 横縞が出ず自然")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"使い方: python3 {sys.argv[0]} <入力画像>")
        sys.exit(1)

    process_image(sys.argv[1])
