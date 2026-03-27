#!/usr/bin/env python3
"""
PC-8801 アナログ8色モード用エクスポートスクリプト
8色PNGから .PAL / .R / .G / .B ファイルを生成する

PALファイル形式（16バイト）:
  8色 × 2バイト
  バイト1: 0b00_RRR_BBB  (bit7,6=00: R,B設定)
  バイト2: 0b01_000_GGG  (bit7,6=01: G設定)
  RGB各値は3bit (0-7) = 8bitの上位3bit (>> 5)

プレーンファイル形式（各16,000バイト）:
  640x200ピクセル、1ピクセル1ビット
  1バイト = 8ピクセル（MSBが左端）
  80バイト × 200行
  パレットインデックスのbit0=Bプレーン、bit1=Rプレーン、bit2=Gプレーン
"""

import sys
import os
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans, DBSCAN
import lze
from dither_comparison import METHODS as DITHER_METHODS

DITHER_FUNCS = dict(DITHER_METHODS)


# デジタル8色固定パレット（インデックス bit2=G, bit1=R, bit0=B）
DIGITAL_PALETTE = np.array([
    [  0,   0,   0],  # 0: 黒
    [  0,   0, 255],  # 1: 青
    [255,   0,   0],  # 2: 赤
    [255,   0, 255],  # 3: 紫
    [  0, 255,   0],  # 4: 緑
    [  0, 255, 255],  # 5: 水色
    [255, 255,   0],  # 6: 黄
    [255, 255, 255],  # 7: 白
], dtype=np.uint8)


def detect_eye_green(img, verbose=True):
    """
    画像全体から目の緑色を自動検出して返す。
    緑ピクセルをDBSCANでクラスタリングし、最大クラスタの平均色を返す。
    画像全体の5%超のクラスタは背景とみなして除外。見つからない場合は None を返す。
    """
    arr = np.array(img.convert('RGB'))
    h, w = arr.shape[:2]

    flat = arr.reshape(-1, 3).astype(float)
    coords = np.array([[y, x] for y in range(h) for x in range(w)])

    green_mask = (
        (flat[:, 1] > flat[:, 0] * 1.2) &
        (flat[:, 1] > flat[:, 2] * 1.2) &
        (flat[:, 1] > 60)
    )
    green_pixels = flat[green_mask]
    green_coords = coords[green_mask]

    if len(green_pixels) < 5:
        if verbose:
            print("auto-green: 緑ピクセルが見つかりませんでした")
        return None

    eps = max(w, h) * 0.05
    db = DBSCAN(eps=eps, min_samples=3).fit(green_coords)
    labels = db.labels_

    best_color = None
    best_count = 0
    threshold = h * w * 0.05  # 全体の5%を超えるクラスタは背景とみなす
    for lbl in set(labels):
        if lbl == -1:
            continue
        mask = labels == lbl
        count = mask.sum()
        if count > best_count and count < threshold:
            best_count = count
            best_color = green_pixels[mask].mean(axis=0).astype(int)

    if best_color is None:
        if verbose:
            print("auto-green: 背景以外の緑クラスタが見つかりませんでした")
        return None

    color = best_color.tolist()
    if verbose:
        r3, g3, b3 = color[0] >> 5, color[1] >> 5, color[2] >> 5
        print(f"auto-green: 検出色 RGB({color[0]},{color[1]},{color[2]}) → 3bit({r3},{g3},{b3})  ({best_count}px)")
    return color


def select_8_colors_with_auto_green(img_half, eye_green, forced_colors=None, verbose=True):
    """
    auto-green用のパレット選択。
    1. まずk-means8色で自動選択し、目の緑の3bit値が既にあれば流用（スロットを節約）。
    2. カバーされていない場合のみ目の緑を強制追加し、
       k-means結果中に目の緑と3bit値が同じ冗長な緑があれば削除して別の色を補充する。
    """
    eye_3bit = tuple(int(c) >> 5 for c in eye_green)

    # まず8色フルでk-means
    full_palette = select_8_colors(img_half, forced_colors=forced_colors)
    full_3bits = [tuple(int(c) >> 5 for c in color) for color in full_palette]

    if eye_3bit in full_3bits:
        if verbose:
            print(f"auto-green: 3bit{eye_3bit} は既にパレットに含まれています（スロット節約）")
        return full_palette

    # カバーされていない → 強制追加
    # forced_colorsにeye_greenを追加してk-means7色
    fc = list(forced_colors) if forced_colors else []
    fc.append(eye_green)
    new_palette = select_8_colors(img_half, forced_colors=fc)

    if verbose:
        print(f"auto-green: 3bit{eye_3bit} をパレットに強制追加しました")
    return new_palette


def quantize_to_9bit(colors):
    return np.round(colors / 255.0 * 7).astype(int)


def dequantize_from_9bit(quantized_colors):
    return np.round(quantized_colors / 7.0 * 255).astype(np.uint8)


def select_8_colors(image, forced_colors=None):
    img_array = np.array(image.convert('RGB'), dtype=float)
    pixels = img_array.reshape(-1, 3)
    quantized = quantize_to_9bit(pixels)

    if forced_colors:
        n_kmeans = 8 - len(forced_colors)
        mask = np.ones(len(quantized), dtype=bool)
        for fc in forced_colors:
            fc_3bit = np.round(np.array(fc) / 255.0 * 7)
            dists = np.sum((quantized - fc_3bit) ** 2, axis=1)
            mask &= (dists > 4)
        kmeans = KMeans(n_clusters=n_kmeans, random_state=42, n_init=10)
        kmeans.fit(quantized[mask])
        palette = dequantize_from_9bit(kmeans.cluster_centers_)
        palette = np.vstack([palette, np.array(forced_colors, dtype=np.uint8)])
    else:
        kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
        kmeans.fit(quantized)
        palette = dequantize_from_9bit(kmeans.cluster_centers_)

    return palette


def atkinson_dithering(image, palette):
    img = np.array(image.convert('RGB'), dtype=float)
    h, w = img.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = img[y, x]
            dists = np.sum((palette.astype(float) - old) ** 2, axis=1)
            idx = np.argmin(dists)
            new = palette[idx].astype(float)
            out[y, x] = new.astype(np.uint8)
            err = old - new
            for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err / 8
    return out


def map_to_palette_indices(image_array, palette):
    """各ピクセルを最近傍パレットインデックスにマッピング（ベクトル化）"""
    h, w = image_array.shape[:2]
    flat = image_array.reshape(-1, 3).astype(float)
    dists = np.sum(
        (flat[:, np.newaxis, :] - palette[np.newaxis, :, :].astype(float)) ** 2,
        axis=2
    )
    return np.argmin(dists, axis=1).reshape(h, w).astype(np.uint8)


def make_pal_file(palette_8bit):
    """
    palette_8bit: shape (8, 3), RGB 0-255
    → 16バイトのPALデータを返す
    """
    data = bytearray()
    for color in palette_8bit:
        r3, g3, b3 = [int(v) >> 5 for v in color]  # 上位3bit
        byte1 = (r3 << 3) | b3          # 0b00_RRR_BBB
        byte2 = 0x40 | g3               # 0b01_000_GGG
        data.append(byte1)
        data.append(byte2)
    return bytes(data)


def make_plane_files(index_map_200x640):
    """
    index_map_200x640: shape (200, 640), パレットインデックス (0-7)
    → B, R, G プレーンの生バイト列を返す（各16,000バイト）

    パレットインデックスのビット構成:
      bit0 = Bプレーン
      bit1 = Rプレーン
      bit2 = Gプレーン
    """
    b_plane = (index_map_200x640 & 1).astype(np.uint8)
    r_plane = ((index_map_200x640 >> 1) & 1).astype(np.uint8)
    g_plane = ((index_map_200x640 >> 2) & 1).astype(np.uint8)

    def pack_plane(plane):
        # (200, 640) → (200, 80, 8) → packbits → (200, 80) → bytes
        bits = plane.reshape(200, 80, 8)
        packed = np.packbits(bits, axis=2, bitorder='big').reshape(200, 80)
        return packed.tobytes()

    return pack_plane(b_plane), pack_plane(r_plane), pack_plane(g_plane)


def export_from_png(png_path, output_base=None, verbose=True, save_planes=False):
    """
    8色に減色済みのPNG（640x400）からPC-8801用ファイルを出力する。

    出力:
      {base}.PAL          - パレットファイル（16バイト）
      {base}.BLZ/RLZ/GLZ  - LZE圧縮済みプレーン
      {base}.B/R/G        - 生プレーン（save_planes=True のときのみ）
    """
    img = Image.open(png_path).convert('RGB')
    w, h = img.size

    if output_base is None:
        output_base = os.path.splitext(png_path)[0]

    if verbose:
        print(f"入力: {png_path} ({w}x{h})")

    # 640x400 → 640x200（縦2倍になっているので1行おきに取得）
    arr = np.array(img)
    if h == 400:
        arr200 = arr[::2]   # 偶数行のみ（200行）
    elif h == 200:
        arr200 = arr
    else:
        # その他の高さは縦方向にリサイズ
        img200 = img.resize((w, 200), Image.NEAREST)
        arr200 = np.array(img200)

    if verbose:
        print(f"実効解像度: {arr200.shape[1]}x{arr200.shape[0]}")

    # パレット抽出（PNGに使われている色を収集）
    flat = arr200.reshape(-1, 3)
    unique_colors = np.unique(flat, axis=0)

    if len(unique_colors) > 8:
        if verbose:
            print(f"警告: 画像に {len(unique_colors)} 色存在。上位8色をk-meansで選択します。")
        kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
        kmeans.fit(quantize_to_9bit(flat))
        palette = dequantize_from_9bit(kmeans.cluster_centers_)
    else:
        palette = unique_colors.astype(np.uint8)
        # 8色未満の場合は黒で補完
        while len(palette) < 8:
            palette = np.vstack([palette, [[0, 0, 0]]])

    if verbose:
        print("パレット (インデックス: RGB → 3bit):")
        for i, c in enumerate(palette):
            r3, g3, b3 = int(c[0]) >> 5, int(c[1]) >> 5, int(c[2]) >> 5
            print(f"  [{i}] RGB({c[0]:3d},{c[1]:3d},{c[2]:3d}) → ({r3},{g3},{b3})")

    # パレットインデックスにマッピング
    index_map = map_to_palette_indices(arr200, palette)

    # PALファイル生成
    pal_data = make_pal_file(palette)
    pal_path = output_base + '.PAL'
    with open(pal_path, 'wb') as f:
        f.write(pal_data)
    if verbose:
        print(f"PAL: {pal_path} ({len(pal_data)} bytes)")
        print(f"  hex: {pal_data.hex(' ')}")

    # プレーンファイル生成
    b_data, r_data, g_data = make_plane_files(index_map)
    for ext, data, lze_ext in [('.B', b_data, '.BLZ'), ('.R', r_data, '.RLZ'), ('.G', g_data, '.GLZ')]:
        if save_planes:
            path = output_base + ext
            with open(path, 'wb') as f:
                f.write(data)
            if verbose:
                print(f"{ext} : {path} ({len(data)} bytes)")

        compressed = lze.encode(data)
        lze_path = output_base + lze_ext
        with open(lze_path, 'wb') as f:
            f.write(compressed)
        if verbose:
            print(f"{lze_ext}: {lze_path} ({len(compressed)} bytes, {100*len(compressed)/len(data):.1f}%)")

    if verbose:
        print("完了")

    return palette, index_map


def export_from_bmp(bmp_path, output_base=None, forced_colors=None, verbose=True, save_planes=False, digital=False, auto_green=False, method='atkinson'):
    """
    元のBMPから直接ディザリング→エクスポートまで行う。
    digital=True のときはデジタル8色固定パレットを使用し、PALファイルを出力しない。
    auto_green=True のときは目の緑色を自動検出して強制パレット色に追加する。
    """
    img = Image.open(bmp_path)
    w, h = img.size

    if output_base is None:
        output_base = os.path.splitext(bmp_path)[0]

    if verbose:
        print(f"入力: {bmp_path} ({w}x{h})")

    # 方法A: 先に縦半分
    img_half = img.resize((640, 200), Image.LANCZOS)
    if verbose:
        print(f"縦半分: {img_half.size[0]}x{img_half.size[1]}")

    # パレット選択
    if digital:
        palette = DIGITAL_PALETTE
        if verbose:
            print("デジタル8色固定パレットを使用")
    elif auto_green:
        green = detect_eye_green(img, verbose=verbose)
        if green is not None:
            palette = select_8_colors_with_auto_green(img_half, green,
                                                      forced_colors=forced_colors,
                                                      verbose=verbose)
        else:
            palette = select_8_colors(img_half, forced_colors)
        if verbose:
            print("パレット選択完了")
    else:
        palette = select_8_colors(img_half, forced_colors)
        if verbose:
            print("パレット選択完了")

    # ディザリング
    dither_func = DITHER_FUNCS.get(method)
    if dither_func is None:
        valid = ', '.join(DITHER_FUNCS.keys())
        raise ValueError(f"不明なmethod: '{method}'。有効な値: {valid}")
    if verbose:
        print(f"ディザリング中... ({method})")
    dithered = dither_func(img_half, palette)  # (200, 640, 3)

    # エクスポート
    if verbose:
        print("パレット (インデックス: RGB):")
        for i, c in enumerate(palette):
            print(f"  [{i}] RGB({c[0]:3d},{c[1]:3d},{c[2]:3d})")

    index_map = map_to_palette_indices(dithered, palette)

    if not digital:
        pal_data = make_pal_file(palette)
        pal_path = output_base + '.PAL'
        with open(pal_path, 'wb') as f:
            f.write(pal_data)
        if verbose:
            print(f"PAL: {pal_path} ({len(pal_data)} bytes)")
            print(f"  hex: {pal_data.hex(' ')}")

    b_data, r_data, g_data = make_plane_files(index_map)
    for ext, data, lze_ext in [('.B', b_data, '.BLZ'), ('.R', r_data, '.RLZ'), ('.G', g_data, '.GLZ')]:
        if save_planes:
            path = output_base + ext
            with open(path, 'wb') as f:
                f.write(data)
            if verbose:
                print(f"{ext} : {path} ({len(data)} bytes)")

        compressed = lze.encode(data)
        lze_path = output_base + lze_ext
        with open(lze_path, 'wb') as f:
            f.write(compressed)
        if verbose:
            print(f"{lze_ext}: {lze_path} ({len(compressed)} bytes, {100*len(compressed)/len(data):.1f}%)")

    # プレビュー用PNG（640x400）も出力
    result_full = np.repeat(dithered, 2, axis=0)
    preview_path = output_base + '_preview.png'
    Image.fromarray(result_full).save(preview_path)
    if verbose:
        print(f"プレビュー: {preview_path}")
        print("完了")

    return palette, index_map


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='PC-8801用 PAL/R/G/B ファイルエクスポート',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input', help='入力ファイル（8色PNG または 元画像BMP）')
    parser.add_argument('-o', '--output', help='出力ファイルのベース名（省略時は入力と同名）')
    parser.add_argument('--force-color', action='append', metavar='R,G,B',
                        help='強制追加するパレット色（BMPからの変換時のみ有効）')
    parser.add_argument('--save-planes', action='store_true',
                        help='圧縮前の生プレーンファイル（.B/.R/.G）も出力する')
    parser.add_argument('--digital', action='store_true',
                        help='デジタル8色固定パレットを使用（PALファイルを出力しない）')
    parser.add_argument('--auto-green', action='store_true',
                        help='目の緑色を自動検出してパレットに強制追加する')
    valid_methods = list(DITHER_FUNCS.keys())
    parser.add_argument('--method', default='atkinson', choices=valid_methods,
                        help=f'ディザリング手法（デフォルト: atkinson）。選択肢: {", ".join(valid_methods)}')
    args = parser.parse_args()

    forced = None
    if args.force_color:
        forced = [list(map(int, c.split(','))) for c in args.force_color]

    ext = os.path.splitext(args.input)[1].lower()
    if ext == '.png':
        export_from_png(args.input, args.output, save_planes=args.save_planes)
    else:
        export_from_bmp(args.input, args.output, forced,
                        save_planes=args.save_planes, digital=args.digital,
                        auto_green=args.auto_green, method=args.method)
