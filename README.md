# 88image

PC-8801用の画像変換ツール群。画像を8色に減色してPC-8801のアナログ/デジタル8色モード向けのファイルを生成する。

## 機能

- **8色減色**: k-meansクラスタリングでRGB各3bit（512色）から最適な8色を自動選択
- **複数のディザリング手法**: Floyd-Steinberg / Atkinson / Burkes / Sierra Lite / Jarvis / Bayer 4x4 / 順序ディザ / なし
- **パレット強制色**: 少面積の色（目の色など）をパレットに強制的に確保する機能
- **PC-8801用エクスポート**: `.PAL`（パレット）+ `.BLZ/.RLZ/.GLZ`（LZE圧縮済みビットプレーン）を生成
- **デジタル8色モード対応**: `--digital` オプションで固定パレット使用
- **LZE圧縮**: PC-8801実機プログラム互換の圧縮（10〜40%程度）

## ファイル構成

```
88image/
├── export_pc88.py          # メインツール：PC-8801用ファイルのエクスポート
├── lze.py                  # LZE圧縮/展開モジュール
├── reduce_colors.py        # 基本的な8色減色スクリプト
├── dither_comparison.py    # 複数ディザリング手法の比較
├── compare_vertical_methods.py  # 縦長ピクセル化方法の比較
├── compare_resize_methods.py    # 縮小方法の比較
├── create_test_image.py    # テスト画像の生成
├── requirements.txt        # 依存パッケージ
└── requirements.md         # 設計ドキュメント・開発経緯
```

## インストール

```bash
pip install -r requirements.txt
```

## 使い方

### PNG から変換（8色以下の画像）

```bash
python3 export_pc88.py input.png output_name
```

### BMP から変換（自動リサイズ・ディザリング）

```bash
python3 export_pc88.py input.bmp output_name
```

入力サイズは問わず、自動で640x200にリサイズされる。

### 主なオプション

| オプション | 説明 |
|---|---|
| `--digital` | デジタル8色モード（固定パレット、PAL不要） |
| `--method atkinson` | ディザリング手法を指定（デフォルト: atkinson） |
| `--force-color R,G,B` | パレットに強制追加する色（複数指定可） |
| `--auto-green` | 目の緑色を自動検出してパレットに追加 |
| `--save-planes` | 圧縮前の生プレーン（.B/.R/.G）も保存 |

### 出力ファイル

| ファイル | 内容 |
|---|---|
| `.PAL` | パレットデータ（アナログモード用） |
| `.BLZ` / `.RLZ` / `.GLZ` | LZE圧縮済みBlue/Red/Greenビットプレーン |
| `_preview.png` | プレビュー画像（BMP入力時のみ） |

### LZE圧縮単体での使用

```bash
python3 lze.py e input.bin output.lze   # 圧縮
python3 lze.py d input.lze output.bin   # 展開
```

## 依存パッケージ

- [Pillow](https://pillow.readthedocs.io/) >= 10.0.0
- [NumPy](https://numpy.org/) >= 1.24.0
- [scikit-learn](https://scikit-learn.org/) >= 1.3.0
