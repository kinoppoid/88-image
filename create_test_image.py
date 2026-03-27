#!/usr/bin/env python3
"""
テスト画像生成スクリプト
カラフルな図形を配置したテスト画像（800x600）を生成する
"""

from PIL import Image, ImageDraw


def create_test_image(output_path='colorful_test.png', width=800, height=600):
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 赤い四角
    draw.rectangle([50, 50, 200, 200], fill=(255, 0, 0))

    # 青い四角
    draw.rectangle([250, 50, 400, 200], fill=(0, 0, 255))

    # 緑の四角
    draw.rectangle([450, 50, 600, 200], fill=(0, 200, 0))

    # 黄色い四角
    draw.rectangle([650, 50, 780, 200], fill=(255, 255, 0))

    # シアンの円
    draw.ellipse([50, 250, 250, 450], fill=(0, 255, 255))

    # マゼンタの円
    draw.ellipse([280, 250, 480, 450], fill=(255, 0, 255))

    # オレンジの円
    draw.ellipse([510, 250, 710, 450], fill=(255, 165, 0))

    # 紫の四角
    draw.rectangle([50, 480, 300, 580], fill=(128, 0, 128))

    # グレーのグラデーション風の横帯
    for i in range(500):
        gray = int(i / 500 * 255)
        draw.line([(300, 480 + i // 10), (300 + i // 5, 480 + i // 10)],
                  fill=(gray, gray, gray))

    # グラデーション帯（赤→青）
    for i in range(width):
        r = int(255 * (1 - i / width))
        b = int(255 * (i / width))
        draw.line([(i, 490), (i, 580)], fill=(r, 0, b))

    img.save(output_path)
    print(f"テスト画像を生成しました: {output_path} ({width}x{height})")


if __name__ == '__main__':
    create_test_image()
