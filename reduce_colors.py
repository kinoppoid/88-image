#!/usr/bin/env python3
"""
基本的な8色減色スクリプト
RGB各3bit（512色）から最適な8色をk-meansで選択し、Floyd-Steinberg誤差拡散で減色する
"""

import sys
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def quantize_to_9bit(colors):
    """RGB各3bit（0-7）に量子化"""
    return np.round(colors / 255.0 * 7).astype(int)


def dequantize_from_9bit(quantized_colors):
    """RGB各3bit（0-7）を0-255に戻す"""
    return np.round(quantized_colors / 7.0 * 255).astype(np.uint8)


def select_8_colors_from_image(image):
    """画像から8色のパレットをk-meansで選択"""
    img_array = np.array(image.convert('RGB'), dtype=float)
    pixels = img_array.reshape(-1, 3)

    # RGB各3bitに量子化
    quantized = quantize_to_9bit(pixels)

    # k-meansで8色選択
    kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
    kmeans.fit(quantized)
    centers = kmeans.cluster_centers_

    # 0-255に戻す
    palette = dequantize_from_9bit(centers)
    return palette


def find_closest_color(pixel, palette):
    """パレットから最も近い色を見つける"""
    distances = np.sum((palette.astype(float) - pixel) ** 2, axis=1)
    idx = np.argmin(distances)
    return idx, palette[idx].astype(float)


def floyd_steinberg_dithering(image, palette):
    """Floyd-Steinberg誤差拡散ディザリング"""
    img_array = np.array(image.convert('RGB'), dtype=float)
    height, width = img_array.shape[:2]
    output = np.zeros_like(img_array, dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            old_pixel = img_array[y, x]
            _, new_pixel = find_closest_color(old_pixel, palette)
            output[y, x] = new_pixel.astype(np.uint8)
            quant_error = old_pixel - new_pixel

            if x + 1 < width:
                img_array[y, x + 1] += quant_error * 7 / 16
            if y + 1 < height:
                if x > 0:
                    img_array[y + 1, x - 1] += quant_error * 3 / 16
                img_array[y + 1, x] += quant_error * 5 / 16
                if x + 1 < width:
                    img_array[y + 1, x + 1] += quant_error * 1 / 16

    return output



def process_image(input_path, output_path=None):
    """画像を8色に減色して保存"""
    img = Image.open(input_path)
    print(f"入力画像: {img.size[0]}x{img.size[1]}")

    # 方法A: 先に縦半分に縮小
    target_width = img.size[0]
    target_height = img.size[1] // 2
    img_half = img.resize((target_width, target_height), Image.LANCZOS)
    print(f"縦半分に縮小: {img_half.size[0]}x{img_half.size[1]}")

    # 8色パレット選択
    print("8色パレットを選択中...")
    palette = select_8_colors_from_image(img_half)
    print(f"選択された8色:")
    for i, color in enumerate(palette):
        print(f"  色{i+1}: RGB({color[0]}, {color[1]}, {color[2]})")

    # Floyd-Steinbergディザリング
    print("Floyd-Steinbergディザリング中...")
    dithered = floyd_steinberg_dithering(img_half, palette)

    # 縦を2倍に引き伸ばし
    result_full = np.repeat(dithered, 2, axis=0)
    print(f"縦2倍に引き伸ばし: {result_full.shape[1]}x{result_full.shape[0]}")

    # 保存
    if output_path is None:
        base = input_path.rsplit('.', 1)[0]
        output_path = f"{base}_8colors.png"

    Image.fromarray(result_full).save(output_path)
    print(f"保存: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"使い方: python3 {sys.argv[0]} <入力画像> [出力画像]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    process_image(input_path, output_path)
