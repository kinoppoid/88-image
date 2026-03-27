#!/usr/bin/env python3
"""
複数ディザリング手法比較スクリプト
8種類のディザリング手法を一度に実行して比較画像を生成する
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


def select_8_colors_from_image(image, forced_colors=None):
    """
    画像から8色のパレットをk-meansで選択。
    forced_colors: 強制追加するRGB色のリスト（例: [[73,182,73]]）
                   指定した数だけk-meansのクラスタ数を減らして補う。
    """
    img_array = np.array(image.convert('RGB'), dtype=float)
    pixels = img_array.reshape(-1, 3)
    quantized = quantize_to_9bit(pixels)

    if forced_colors:
        n_kmeans = 8 - len(forced_colors)
        # 強制色に近いピクセルを除外してk-meansを実行
        mask = np.ones(len(quantized), dtype=bool)
        for fc in forced_colors:
            fc_3bit = np.round(np.array(fc) / 255.0 * 7)
            dists = np.sum((quantized - fc_3bit) ** 2, axis=1)
            mask &= (dists > 4)
        kmeans = KMeans(n_clusters=n_kmeans, random_state=42, n_init=10)
        kmeans.fit(quantized[mask])
        palette = dequantize_from_9bit(kmeans.cluster_centers_)
        forced = np.array(forced_colors, dtype=np.uint8)
        palette = np.vstack([palette, forced])
    else:
        kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
        kmeans.fit(quantized)
        palette = dequantize_from_9bit(kmeans.cluster_centers_)

    return palette


def find_closest_color(pixel, palette):
    distances = np.sum((palette.astype(float) - pixel) ** 2, axis=1)
    idx = np.argmin(distances)
    return idx, palette[idx].astype(float)


def floyd_steinberg_dithering(image, palette):
    """Floyd-Steinberg誤差拡散"""
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
    """Atkinson誤差拡散（75%拡散）"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new

            # 6方向に1/8ずつ（合計6/8 = 75%）
            for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err / 8
    return out


def burkes_dithering(image, palette):
    """Burkes誤差拡散"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    weights = [(0, 1, 8/32), (0, 2, 4/32),
               (1, -2, 2/32), (1, -1, 4/32), (1, 0, 8/32), (1, 1, 4/32), (1, 2, 2/32)]

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            for dy, dx, w_ in weights:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err * w_
    return out


def sierra_lite_dithering(image, palette):
    """Sierra Lite誤差拡散"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    weights = [(0, 1, 2/4), (1, -1, 1/4), (1, 0, 1/4)]

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            for dy, dx, w_ in weights:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err * w_
    return out


def jarvis_dithering(image, palette):
    """Jarvis-Judice-Ninke誤差拡散"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    weights = [
        (0, 1, 7/48), (0, 2, 5/48),
        (1, -2, 3/48), (1, -1, 5/48), (1, 0, 7/48), (1, 1, 5/48), (1, 2, 3/48),
        (2, -2, 1/48), (2, -1, 3/48), (2, 0, 5/48), (2, 1, 3/48), (2, 2, 1/48),
    ]

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            _, new = find_closest_color(old, palette)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            for dy, dx, w_ in weights:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err * w_
    return out


def bayer4x4_dithering(image, palette):
    """Bayer 4x4順序ディザリング"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    bayer = np.array([
        [ 0,  8,  2, 10],
        [12,  4, 14,  6],
        [ 3, 11,  1,  9],
        [15,  7, 13,  5]
    ]) / 16.0 - 0.5

    for y in range(h):
        for x in range(w):
            threshold = bayer[y % 4, x % 4]
            pixel = img[y, x] + threshold * (255.0 / 8)
            pixel = np.clip(pixel, 0, 255)
            _, new = find_closest_color(pixel, palette)
            out[y, x] = new.astype(np.uint8)
    return out


def ordered2x2_dithering(image, palette):
    """2x2順序ディザリング"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    pattern = np.array([
        [0, 2],
        [3, 1]
    ]) / 4.0 - 0.5

    for y in range(h):
        for x in range(w):
            threshold = pattern[y % 2, x % 2]
            pixel = img[y, x] + threshold * (255.0 / 8)
            pixel = np.clip(pixel, 0, 255)
            _, new = find_closest_color(pixel, palette)
            out[y, x] = new.astype(np.uint8)
    return out


def no_dithering(image, palette):
    """ディザリングなし（最近傍色選択）"""
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            _, new = find_closest_color(img[y, x], palette)
            out[y, x] = new.astype(np.uint8)
    return out


METHODS = [
    ('floyd-steinberg', floyd_steinberg_dithering),
    ('atkinson', atkinson_dithering),
    ('burkes', burkes_dithering),
    ('sierra-lite', sierra_lite_dithering),
    ('jarvis', jarvis_dithering),
    ('bayer4x4', bayer4x4_dithering),
    ('ordered2x2', ordered2x2_dithering),
    ('none', no_dithering),
]


def process_image(input_path, forced_colors=None, methods=None):
    img = Image.open(input_path)
    base = os.path.splitext(input_path)[0]
    suffix = '_forced' if forced_colors else ''

    # 方法A: 先に縦半分
    target_width = img.size[0]
    target_height = img.size[1] // 2
    img_half = img.resize((target_width, target_height), Image.LANCZOS)
    print(f"入力: {img.size[0]}x{img.size[1]} → 縦半分: {img_half.size[0]}x{img_half.size[1]}")

    print("8色パレット選択中...")
    palette = select_8_colors_from_image(img_half, forced_colors)
    print("パレット:")
    for i, c in enumerate(palette):
        tag = ' ← 強制' if forced_colors and i >= 8 - len(forced_colors) else ''
        print(f"  {i}: RGB({c[0]:3d},{c[1]:3d},{c[2]:3d}){tag}")

    selected = [(name, func) for name, func in METHODS if methods is None or name in methods]

    for name, func in selected:
        print(f"{name} 処理中...")
        result = func(img_half, palette)
        result_full = np.repeat(result, 2, axis=0)
        out_path = f"{base}{suffix}_{name}.png"
        Image.fromarray(result_full).save(out_path)
        print(f"  → {out_path}")

    print("完了")


METHOD_NAMES = [name for name, _ in METHODS]

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='8色ディザリング（デフォルト: atkinson）',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input', help='入力画像')
    parser.add_argument('--force-color', action='append', metavar='R,G,B',
                        help='強制追加するパレット色（例: 73,182,73）。複数指定可。')
    parser.add_argument('--method', action='append', metavar='NAME',
                        help=f'使用する手法（複数指定可）。省略時はatkinsonのみ。\n選択肢: {", ".join(METHOD_NAMES)}')
    parser.add_argument('--all', action='store_true',
                        help='全手法を実行する')
    args = parser.parse_args()

    forced = None
    if args.force_color:
        forced = [list(map(int, c.split(','))) for c in args.force_color]
        print(f"強制パレット色: {forced}")

    if args.all:
        methods = None
    elif args.method:
        invalid = [m for m in args.method if m not in METHOD_NAMES]
        if invalid:
            print(f"エラー: 不明な手法: {', '.join(invalid)}")
            print(f"選択肢: {', '.join(METHOD_NAMES)}")
            sys.exit(1)
        methods = args.method
    else:
        methods = ['atkinson']

    process_image(args.input, forced, methods)
