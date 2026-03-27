# 画像8色減色プロジェクト

## プロジェクト概要
画像を誤差拡散（ディザリング）を使ってRGB各3bit（512色）の中から最適な8色に自動減色するツール群。
複数のディザリングアルゴリズムを実装し、比較できる。

## 元の要件
- 640 x 400 の画像を 640 x 200 (縦長ピクセル)で同時8色の画像データにする
- 使える色はRGB各3bit、合計9bit（512色）中8色
- 画像一枚につき4ファイル使用。パレットファイルと1ピクセル1ビットで表したRGBそれぞれのファイル

## 実装した機能

### 1. 基本的な8色減色（reduce_colors.py）
- RGB各3bit（0-7の範囲）の512色空間から画像に最適な8色をk-meansクラスタリングで自動選択
- Floyd-Steinberg誤差拡散で減色
- 縦長ピクセル化は方法A（先にLANCZOSで縦半分縮小 → ディザリング → np.repeatで縦2倍）

### 2. 複数ディザリング手法の比較（dither_comparison.py）
以下の8種類のディザリング手法を実行して比較（デフォルトはatkinsonのみ）：
- **Floyd-Steinberg誤差拡散**: 最も一般的な誤差拡散アルゴリズム
- **Atkinson誤差拡散**: 初期Macで使用、75%拡散、細部保持に最適
- **Burkes誤差拡散**: 速度と品質のバランス型
- **Sierra Lite誤差拡散**: 高速、3ピクセルのみ拡散
- **Jarvis-Judice-Ninke誤差拡散**: 12ピクセルに誤差を拡散、最も滑らか
- **Bayer 4x4順序ディザリング**: 規則的なパターン、レトロゲーム風
- **2x2順序ディザリング**: より粗いパターン
- **ディザリングなし**: 単純な最近傍色選択、ポスタリゼーション効果

#### パレット強制色機能
画像のk-means自動選択では埋もれてしまう色（例：少ない面積の目の色など）を、
パレットの1枠として強制的に確保できる。

- 指定色の分だけk-meansのクラスタ数を減らし（8 - N色）、残りをk-meansで選ぶ
- 強制色に近いピクセルをk-meansの入力から除外することで、他の色選択に影響しない
- 元画像にない鮮やかな色（例：暗い緑→鮮やかな緑）に置き換えることも可能

### 3. テスト画像生成（create_test_image.py）
カラフルな図形を配置したテスト画像を生成

### 4. 縦長ピクセル化方法の比較（compare_vertical_methods.py）
2つの処理順序（先に縦半分 vs 最後に縦半分）を比較

### 5. 縮小方法の比較（compare_resize_methods.py）
3種類の縮小方法（LANCZOS、NEAREST、LANCZOS+シャープ化）を比較
Atkinsonディザリングと組み合わせて、細い線の保持状態を検証

### 6. PC-8801用ファイルエクスポート（export_pc88.py）
8色に減色した画像からPC-8801アナログ/デジタル8色モード用のファイルを生成する。

- **入力**: PNG（640x400）または元画像（BMP等）
  - PNG入力: 8色以下ならそのままパレット使用、8色超ならk-meansで自動選択、8色未満は黒で補完
  - BMP入力: LANCZOSで縦半分縮小→ディザリング→エクスポートを自動実行
- **出力（デフォルト）**: `.PAL`（パレット）、`.BLZ`/`.RLZ`/`.GLZ`（LZE圧縮済みプレーン）、`_preview.png`（BMP入力時のみ）
- **出力（`--save-planes`）**: 上記に加えて `.B`/`.R`/`.G`（生プレーン）も出力
- **出力（`--digital`）**: PALなし、`.BLZ`/`.RLZ`/`.GLZ`のみ（デジタル8色固定パレット使用）
- `--force-color R,G,B`: 強制パレット色を指定（複数指定可、BMP入力時のみ有効、PNG・`--digital` では無視）
- `--auto-green`: 目の緑色を自動検出してパレットに強制追加（`--force-color` と併用可、`--digital` では無視）
- `--method`: ディザリング手法を指定（デフォルト: `atkinson`、BMP入力時のみ有効）
- lze.pyを利用してビットプレーンを自動圧縮、圧縮率は画像により10〜40%程度
- 入力画像サイズは問わない（640x400以外も640x200に自動リサイズ）

### 7. LZE圧縮（lze.py）
PC-8801実機プログラムで使われているLZE圧縮アルゴリズムのPythonポート。

- C#実装（lze.cs、Copyright (C)1995,2008 GORRY、C# port by Kei Moroboshi）をPythonに移植
- `BZCOMPATIBLE=True`、`SPEED=True` でビルドされた lze.exe と互換
- `encode(data: bytes) -> bytes`: 4バイト大エンディアンサイズヘッダ付きで圧縮
- `decode(data: bytes) -> bytes`: 圧縮データを展開
- CLIとしても使用可能: `python3 lze.py e infile outfile` / `python3 lze.py d infile outfile`

#### アルゴリズム詳細
- LZ77方式、辞書バッファ N=16384、最大一致長 F=256
- ハッシュテーブル IDX=8192（SPEED=True）
- ビットフラグ形式: `1`=リテラル、`00xx`=近距離一致（距離≤256、長さ2〜5）、`01`=遠距離一致（距離≤8192、長さ2〜256）
- BZCOMPATIBLE: 先頭1バイトはそのまま出力

## ファイル構成

```
88image/
├── requirements.txt               # 依存パッケージ
├── requirements.md                # このドキュメント
├── reduce_colors.py               # 基本的な8色減色スクリプト
├── dither_comparison.py           # 複数ディザリング手法比較スクリプト
├── compare_vertical_methods.py    # 縦長ピクセル化方法の比較スクリプト
├── compare_resize_methods.py      # 縮小方法の比較スクリプト
├── create_test_image.py           # テスト画像生成スクリプト
├── export_pc88.py                 # PC-8801用PAL/R/G/B/BLZ/RLZ/GLZファイルエクスポート
└── lze.py                         # LZE圧縮/展開モジュール
```

## 依存パッケージ（requirements.txt）

```
Pillow>=10.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

## インストール

```bash
pip3 install --break-system-packages -r requirements.txt
```

または仮想環境を使用：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 使い方

### 1. 基本的な8色減色

```bash
python3 reduce_colors.py <入力画像> [出力画像]
```

例：
```bash
python3 reduce_colors.py photo.jpg output.png
```

### 2. 複数のディザリング手法で比較

```bash
# デフォルト: atkinsonのみ実行
python3 dither_comparison.py <入力画像>

# 手法を指定（複数可）
python3 dither_comparison.py <入力画像> --method floyd-steinberg --method atkinson

# 全手法を実行
python3 dither_comparison.py <入力画像> --all

# パレットに色を強制追加（複数可）
python3 dither_comparison.py <入力画像> --force-color 73,182,73

# 組み合わせ
python3 dither_comparison.py <入力画像> --force-color 73,182,73 --method atkinson
```

`--method` に指定できる文字列一覧：

| 文字列 | 手法 |
|--------|------|
| `floyd-steinberg` | Floyd-Steinberg誤差拡散 |
| `atkinson` | Atkinson誤差拡散（デフォルト） |
| `burkes` | Burkes誤差拡散 |
| `sierra-lite` | Sierra Lite誤差拡散 |
| `jarvis` | Jarvis-Judice-Ninke誤差拡散 |
| `bayer4x4` | Bayer 4x4順序ディザリング |
| `ordered2x2` | 2x2順序ディザリング |
| `none` | ディザリングなし |

デフォルト（atkinson）の出力ファイル：
- `入力画像名_atkinson.png`（強制色なし）
- `入力画像名_forced_atkinson.png`（`--force-color` 指定時）

`--all` 指定時に生成される全ファイル：
- `入力画像名_floyd-steinberg.png`
- `入力画像名_atkinson.png`
- `入力画像名_burkes.png`
- `入力画像名_sierra-lite.png`
- `入力画像名_jarvis.png`
- `入力画像名_bayer4x4.png`
- `入力画像名_ordered2x2.png`
- `入力画像名_none.png`

### 3. テスト画像の生成

```bash
python3 create_test_image.py
```

`colorful_test.png`が生成される（800x600、白背景にカラフルな図形）

### 4. 縦長ピクセル化方法の比較

```bash
python3 compare_vertical_methods.py <入力画像>
```

2つの処理方法（AtkinsonとFloyd-Steinberg）×2つの順序（方法A/B）の4ファイルが生成される：
- `入力画像名_atkinson_methodA.png` - 先に縦半分
- `入力画像名_atkinson_methodB.png` - 最後に縦半分
- `入力画像名_floyd-steinberg_methodA.png` - 先に縦半分
- `入力画像名_floyd-steinberg_methodB.png` - 最後に縦半分

**推奨**: 方法A（先に縦半分）が横縞が出ず自然

### 5. 縮小方法の比較

```bash
python3 compare_resize_methods.py <入力画像>
```

3種類の縮小方法で処理した結果が生成される：
- `入力画像名_resize_lanczos.png` - LANCZOS（高品質縮小）
- `入力画像名_resize_nearest.png` - NEAREST（単純間引き）
- `入力画像名_resize_lanczos_sharpen.png` - LANCZOS + シャープ化

**推奨**: LANCZOSで十分（3つともほぼ同じ結果）

### 6. PC-8801用ファイルエクスポート

```bash
# 8色PNGから生成（既に減色済みの場合）
python3 export_pc88.py <8色PNG> [-o 出力ベース名]

# 元画像から直接（アナログ8色、ディザリングも同時実行）
python3 export_pc88.py <元画像> [--force-color R,G,B] [-o 出力ベース名]

# ディザリング手法を指定（デフォルト: atkinson）
python3 export_pc88.py <元画像> --method floyd-steinberg [-o 出力ベース名]

# デジタル8色固定パレット（PALファイルなし）
python3 export_pc88.py <元画像> --digital [-o 出力ベース名]

# 生プレーンファイル（.B/.R/.G）も出力する
python3 export_pc88.py <元画像> --save-planes [-o 出力ベース名]
```

`--method` に指定できる文字列一覧：

| 文字列 | 手法 |
|--------|------|
| `floyd-steinberg` | Floyd-Steinberg誤差拡散 |
| `atkinson` | Atkinson誤差拡散（デフォルト） |
| `burkes` | Burkes誤差拡散 |
| `sierra-lite` | Sierra Lite誤差拡散 |
| `jarvis` | Jarvis-Judice-Ninke誤差拡散 |
| `bayer4x4` | Bayer 4x4順序ディザリング |
| `ordered2x2` | 2x2順序ディザリング |
| `none` | ディザリングなし |

例：
```bash
# アナログ8色・強制色指定あり（複数指定可）
python3 export_pc88.py images/1.bmp --force-color 73,182,73 -o images/1
python3 export_pc88.py images/1.bmp --force-color 71,102,154 --force-color 135,190,119 -o images/1

# 目の緑を自動検出してパレット強制追加
python3 export_pc88.py images/1.bmp --auto-green -o images/1

# --auto-green と --force-color の併用
python3 export_pc88.py images/1.bmp --auto-green --force-color 71,102,154 -o images/1

# デジタル8色
python3 export_pc88.py images/1.bmp --digital -o images/1

# 生プレーンも出力
python3 export_pc88.py images/1.bmp --force-color 73,182,73 --save-planes -o images/1
```

出力ファイル（アナログモード・BMP入力、例: `-o images/1` の場合）：
- `images/1.PAL`         — パレットファイル（16バイト固定）
- `images/1.BLZ`         — BプレーンのLZE圧縮（可変長）
- `images/1.RLZ`         — RプレーンのLZE圧縮（可変長）
- `images/1.GLZ`         — GプレーンのLZE圧縮（可変長）
- `images/1_preview.png` — プレビュー画像（640x400、縦2倍引き伸ばし）
- `images/1.B`           — Bプレーン（16,000バイト）※`--save-planes` 時のみ
- `images/1.R`           — Rプレーン（16,000バイト）※`--save-planes` 時のみ
- `images/1.G`           — Gプレーン（16,000バイト）※`--save-planes` 時のみ

デジタルモード（`--digital`）ではPALファイルは出力されない。

## 実装の詳細

### 目の緑色自動検出（--auto-green）

`detect_eye_green()` が画像全体から緑ピクセルをDBSCANでクラスタリングし、最も大きなクラスタの平均色を目の緑として検出する。

```
1. 緑ピクセルを抽出: G > R×1.2 かつ G > B×1.2 かつ G > 60
2. DBSCANでクラスタリング（eps=画像短辺の5%、min_samples=3）
3. 画像全体の5%超のクラスタは背景とみなし除外
4. 残る最大クラスタの平均色を目の緑として採用
```

検出後、`select_8_colors_with_auto_green()` でパレットを最適化する：

```
1. まず8色フルでk-meansを実行
2. 検出した目の緑の3bit値が既にパレットに含まれていれば流用（スロット節約）
3. 含まれていない場合のみ強制追加（k-meansは7色に減り、
   目の緑周辺ピクセルはk-means入力から除外されるため冗長な緑の重複を防ぐ）
```

### 8色の選択アルゴリズム

1. 入力画像の全ピクセルをRGB各3bit（0-7）に量子化
2. 量子化された色空間でk-meansクラスタリング（k=8）を実行
3. 8つのクラスタ中心を代表色として選択
4. 0-255の範囲に逆量子化

```python
def quantize_to_9bit(colors):
    """RGB各3bit（0-7）に量子化"""
    return np.round(colors / 255.0 * 7).astype(int)

def dequantize_from_9bit(quantized_colors):
    """RGB各3bit（0-7）を0-255に戻す"""
    return np.round(quantized_colors / 7.0 * 255).astype(np.uint8)
```

### Floyd-Steinberg誤差拡散

量子化誤差を以下の重みで周囲4ピクセルに拡散：

```
    現在  7/16
3/16 5/16 1/16
```

実装：
```python
def floyd_steinberg_dithering(image, palette):
    img_array = np.array(image, dtype=float)
    height, width = img_array.shape[:2]
    output = np.zeros_like(img_array, dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            old_pixel = img_array[y, x]
            _, new_pixel = find_closest_color(old_pixel, palette)
            output[y, x] = new_pixel
            quant_error = old_pixel - new_pixel

            # 誤差を周囲に拡散
            if x + 1 < width:
                img_array[y, x + 1] += quant_error * 7 / 16
            if y + 1 < height:
                if x > 0:
                    img_array[y + 1, x - 1] += quant_error * 3 / 16
                img_array[y + 1, x] += quant_error * 5 / 16
                if x + 1 < width:
                    img_array[y + 1, x + 1] += quant_error * 1 / 16

    return output
```

### Atkinson誤差拡散

誤差を1/8ずつ6方向に拡散（合計6/8、意図的に100%拡散しない）：

```
     現在  1/8  1/8
1/8  1/8  1/8
     1/8
```

特徴：明るめで繊細な仕上がり

### Burkes誤差拡散

誤差を7ピクセルに拡散（合計32/32）：

```
        現在  8/32  4/32
2/32 4/32 8/32 4/32 2/32
```

特徴：速度と品質のバランス型、Floyd-Steinbergより少し滑らか

### Sierra Lite誤差拡散

誤差を3ピクセルに拡散（合計4/4）：

```
    現在  2/4
1/4 1/4
```

特徴：最速、シンプル、ただし細い線は消える

### Jarvis-Judice-Ninke誤差拡散

誤差を12ピクセルに拡散（合計48/48）：

```
           現在  7/48  5/48
3/48 5/48  7/48  5/48  3/48
1/48 3/48  5/48  3/48  1/48
```

特徴：最も滑らかだが処理時間がかかる、細い線が消える

### Bayer 4x4順序ディザリング

4x4のBayerマトリクスを使用：

```python
bayer_matrix = np.array([
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5]
]) / 16.0 - 0.5
```

特徴：規則的なパターン、レトロゲーム風

### 2x2順序ディザリング

2x2のパターン：

```python
pattern = np.array([
    [0, 2],
    [3, 1]
]) / 4.0 - 0.5
```

特徴：より粗いパターン

### 縦長ピクセル化（方法A）

先にLANCZOSで縦半分に縮小してからディザリングし、最後にnp.repeatで縦2倍に引き伸ばす：

```python
# 縦半分に縮小
img_half = img.resize((width, height // 2), Image.LANCZOS)

# ディザリング
dithered = atkinson_dithering(img_half, palette)

# 縦2倍に引き伸ばし（各行を2回繰り返す）
result_full = np.repeat(dithered, 2, axis=0)
```

## 縦長ピクセル化の処理順序

縦長ピクセル（1:2）を実現する際、処理順序によって結果が大きく変わる。

### 2つの方法

#### 方法A: 先に縦半分 → ディザリング → 縦2倍
```
高解像度イラスト（例：1600x1200）
  ↓
縦を半分に縮小（例：800x600）
  ↓
パレット選択（8色）
  ↓
ディザリング
  ↓
縦を2倍に引き伸ばし（例：800x1200、縦長ピクセル表示用）
```

#### 方法B: ディザリング → 2行ずつ同じ色
```
高解像度イラスト（例：1600x1200）
  ↓
縮小（例：800x1200）
  ↓
パレット選択（8色）
  ↓
ディザリング
  ↓
2行ずつ同じ色に（縦長ピクセル化）
```

### 実験結果（800x600のカラフルなテスト画像）

| 観点 | 方法A（先に縦半分） | 方法B（最後に縦半分） |
|------|-------------------|---------------------|
| **処理速度** | ★★★★★ 2倍速い | ★★★☆☆ 遅い |
| **メモリ** | ★★★★★ 半分 | ★★★☆☆ 多い |
| **横縞** | ★★★★★ 出ない | ★☆☆☆☆ 非常に目立つ |
| **パターンの自然さ** | ★★★★★ 等方的 | ★★☆☆☆ 横方向に偏る |
| **Floyd-Steinberg** | 自然なディザリング | 横縞が顕著 |
| **Atkinson** | ドット状、均等分散 | 斜め線状パターン |

### 方法Aの利点（実験で確認）

1. **横縞が出ない**
   - 最初から半分の行数でディザリングするため、自然に2行分のパターンになる
   - 後から強制的に横縞化されない

2. **パターンが等方的で自然**
   - Atkinson: ドット状で均等に分散
   - Floyd-Steinberg: 自然なディザリング

3. **処理速度が約2倍**
   - 半分のピクセル数で処理
   - 特にJarvisなど重いアルゴリズムで効果大

4. **メモリ効率が良い**
   - 誤差拡散の作業用配列が半分

### 方法Bの問題点（実験で確認）

1. **横縞が非常に目立つ**
   - 特にFloyd-Steinbergで顕著
   - 紫の四角に明確な横縞模様

2. **ディザリングパターンが不自然**
   - Atkinsonのオレンジの円が線状に
   - 等方的なディザリングが失われる

3. **ディザリングと縦長化の不整合**
   - ディザリングは正方形ピクセル前提で動作
   - 後から2行ずつ潰すとパターンが壊れる

### 推奨：方法A（先に縦半分）

**縦長ピクセル化する場合は方法A一択**

理由：
- 横縞が出ない
- パターンが自然
- 速度とメモリの効率が良い
- 懸念していた「縦方向の解像度損失」は実用上問題なし

### 推奨処理フロー

```python
# 1. 高品質縮小（縦を半分に）
img = Image.open("high_res.png")
target_width = 640
target_height = 300  # 最終的に600行になる予定の半分
img = img.resize((target_width, target_height), Image.LANCZOS)

# シャープ化は不要（実験で効果なしと判明）

# 2. 8色パレット選択
palette = select_8_colors_from_image(img)

# 3. ディザリング（Atkinson推奨）
result = atkinson_dithering(img, palette)

# 4. 縦を2倍に引き伸ばし（各行を2回繰り返す）
result_full = np.repeat(result, 2, axis=0)

# 完成：640x600（縦長ピクセル表示用）
```

### 縮小方法の選択

#### 推奨：LANCZOS（高品質縮小）

```python
img = img.resize((target_width, target_height), Image.LANCZOS)
```

**理由（実験で確認）:**
- LANCZOS vs NEAREST vs LANCZOS+シャープ化を比較した結果、**3つともほぼ同じ結果**
- 2倍程度の縮小では、縮小方法の違いは実用上無視できる
- LANCZOSは標準的で汎用性が高い
- Atkinsonディザリングと組み合わせれば、細い線も保持される

#### 他の選択肢

**NEAREST（単純間引き）:**
```python
img = img.resize((target_width, target_height), Image.NEAREST)
```

使うべき場合：
- ドット絵・ピクセルアート
- 整数倍の縮小（640→320など）
- レトロゲーム風の見た目
- 処理速度最優先

**シャープ化:**
- **不要**（実験で効果なしと判明）
- 2倍程度の縮小では差が出ない
- 超高解像度から大幅縮小する場合でも効果は限定的

### 例外：方法Bが適している場合

- **縦長ピクセル化しない場合**（普通の正方形ピクセル）
- その場合は高解像度でディザリングした方が品質が高い

### 実装例・比較ツール

**縦長ピクセル化方法の比較:**
```bash
python3 compare_vertical_methods.py <入力画像>
```

出力：
- `*_methodA.png`: 方法A（先に縦半分）
- `*_methodB.png`: 方法B（最後に縦半分）

**縮小方法の比較:**
```bash
python3 compare_resize_methods.py <入力画像>
```

出力：
- `*_resize_lanczos.png`: LANCZOS
- `*_resize_nearest.png`: NEAREST
- `*_resize_lanczos_sharpen.png`: LANCZOS+シャープ化

## 各手法の比較

### 誤差拡散系の特徴

#### Floyd-Steinberg (1976)
- **拡散**: 4ピクセル、100%拡散
- **長所**: バランスが良く標準的、汎用性高い
- **短所**: 斜めのワームパターンが出ることがある
- **用途**: 一般的な画像処理

#### Atkinson (1980s)
- **拡散**: 6ピクセル、75%拡散（25%を捨てる）
- **長所**: 細い線が残る、明るくシャープ、コントラスト高い
- **短所**: 暗部が潰れやすい
- **用途**: **8色制限のイラスト、UI、白黒印刷**

#### Burkes (1988)
- **拡散**: 7ピクセル、100%拡散
- **長所**: Floyd-Steinbergより少し滑らか、速度も良い
- **短所**: 細い線は消える
- **用途**: 写真、グラデーション重視

#### Sierra Lite
- **拡散**: 3ピクセル、100%拡散
- **長所**: 最速、シンプル
- **短所**: 細い線は消える、ノイズ多め
- **用途**: リアルタイム処理、速度優先

#### Jarvis-Judice-Ninke (1976)
- **拡散**: 12ピクセル、100%拡散
- **長所**: 非常に滑らか、ノイズ最小
- **短所**: 細い線が完全に消える、処理が遅い
- **用途**: 写真の高品質処理、色数が多い場合

### 順序ディザリング系（Bayer, 2x2）
- **長所**: 規則的、処理が軽い、レトロな雰囲気
- **短所**: パターンが目立つ
- **用途**: レトロゲーム風、ドット絵

### ディザリングなし
- **長所**: はっきりした境界、ポスター風
- **短所**: 階調が失われる
- **用途**: ポスター、イラスト風

## 色数制限とアルゴリズム選択

### なぜ8色制限でAtkinsonが優れているのか

#### 初期Macとの共通点
1984年の初期Macintosh（白黒2色のみ）で開発されたAtkinsonアルゴリズムは、**少ない色数で細部を保持する**という課題に最適化されています。

- **初期Mac**: 白黒2色でUI、アイコン、細い線を表示
- **8色制限**: RGB各3bitから8色でイラストの細い線を保持

どちらも同じ課題：**色数制限下での細部保持**

#### Atkinsonの設計思想

```
通常の誤差拡散: 100%拡散 → 滑らかさ優先
Atkinson:      75%拡散  → 明瞭さ優先（25%の誤差を捨てる）
```

**25%の誤差を捨てる効果:**
- コントラストが保たれる
- 「線があるかないか」の二値的情報を優先
- 細い線（1-2ピクセル幅）が消えない

#### 色数が少ない場合の問題

1. **パレットの色が離れている**
   - 8色しかないため、隣接色の距離が大きい
   - 中間色を正確に表現できない

2. **100%誤差拡散の問題**
   - 細い線の情報が周囲に薄く広がる
   - 拡散後の色が元の線とかけ離れる
   - 結果として線が見えなくなる

3. **Atkinsonの解決策**
   - 誤差を完全に拡散しない
   - エッジ情報（コントラスト）を保持
   - 細い線が認識可能な状態を維持

### 実験結果：アニメイラストの口の線

テスト画像（両目の間、顎上の細い線）での結果：

| アルゴリズム | 拡散 | 口の線 | 評価 |
|------------|------|--------|------|
| **Atkinson** | 6px, 75% | ✓ 見える | ★★★★★ |
| Floyd-Steinberg | 4px, 100% | ✗ ほぼ消える | ★★☆☆☆ |
| Burkes | 7px, 100% | ✗ ほぼ消える | ★★☆☆☆ |
| Sierra Lite | 3px, 100% | ✗ ほぼ消える | ★☆☆☆☆ |
| Jarvis | 12px, 100% | ✗ 完全に消える | ★☆☆☆☆ |

**結論**: 8色制限では**Atkinsonのみ**が細い線を保持できる

### アルゴリズム選択ガイド

#### 8色制限 + アニメイラスト/UI
→ **Atkinson** 一択
- 細い線（口、まつげ、輪郭線）が保持される
- シャープな仕上がり

#### 8色制限 + 写真/グラデーション重視
→ **Floyd-Steinberg** または **Burkes**
- 滑らかなグラデーション
- 細部より階調を優先

#### 色数が多い（256色以上）
→ どのアルゴリズムでも可
- パレットが密なので細部も保持される
- Jarvisなど滑らか系も使える

#### レトロ効果
→ **Bayer**, **Ordered 2x2**
- 規則的なパターンでドット絵風

#### ポスター/ポップアート
→ **ディザリングなし**
- ベタ塗り、はっきりした境界

### 歴史的意義

Bill Atkinsonが1980年代に設計したこのアルゴリズムは、**制約のある環境での最適化**の好例です。40年以上経った現在でも、色数制限という同じ制約下で最適な選択肢となっています。

## テスト結果

### 森の写真（ダウンロード.jpg）
- 緑系の濃淡8色が自動選択された
- 誤差拡散で滑らかなグラデーションを表現

### アニメイラスト（ダウンロード (1).jpg）
- 肌色、シアン（目）、グレー（髪）、赤などが選択された
- **Atkinsonが最適**: 細い線（口）がくっきり保持される
- Floyd-Steinberg, Burkes, Sierra Lite: 口の線がほぼ消える
- Jarvis: 滑らかだが細部が完全に消える
- **重要な発見**: 8色制限では75%拡散のAtkinsonが細部保持に圧倒的に有利

### カラフルなテスト画像（colorful_test.png）
- 原色（赤、青、緑）、補色（黄、シアン、マゼンタ）、白、紫が選択された
- オレンジ→黄色+赤のディザリング
- 紫→赤+青の縞模様
- 手法によるパターンの違いが明確

### 縦長ピクセル化の処理順序実験（colorful_test.png、800x600）

**方法A（先に縦半分→ディザリング→縦2倍）:**
- Atkinson: オレンジの円が細かいドットパターン、均等分散、自然
- Floyd-Steinberg: ディザリングパターンが自然
- **横縞なし**

**方法B（ディザリング→2行ずつ同じ色）:**
- Atkinson: オレンジの円が斜め線状パターン、横方向に構造
- Floyd-Steinberg: 紫の四角に明確な横縞模様
- **横縞が非常に目立つ**

**結論**: 縦長ピクセル化する場合は**方法A（先に縦半分）を推奨**
- 横縞が出ない
- パターンが自然で等方的
- 処理速度が約2倍速い
- メモリ効率が良い

### 縮小方法の比較実験（アニメイラスト310x163、カラフルな画像800x600）

**3つの縮小方法をAtkinsonディザリングと組み合わせて比較:**

1. **LANCZOS（高品質縮小）**
   - アニメイラスト：口の線が点線状だが見える
   - カラフルな画像：オレンジの円が細かいドットパターン

2. **NEAREST（単純間引き）**
   - アニメイラスト：口の線が点線状だが見える（LANCZOSとほぼ同じ）
   - カラフルな画像：オレンジの円が細かいドットパターン（LANCZOSとほぼ同じ）

3. **LANCZOS + シャープ化**
   - アニメイラスト：口の線が点線状だが見える（LANCZOSとほぼ同じ）
   - カラフルな画像：オレンジの円が細かいドットパターン（LANCZOSとほぼ同じ）

**重要な発見：3つともほぼ同じ結果**

**なぜ差が出ないのか:**
- 縮小率が2倍程度（163→81行、600→300行）では、LANCZOS vs NEARESTの差が小さい
- 8色という制約が支配的で、縮小時の微妙な色の違いはディザリング時に吸収される
- Atkinsonの75%拡散特性が、縮小方法の違いを覆い隠す
- シャープ化は元が低解像度なので効果が限定的

**結論：LANCZOSで十分**
- NEARESTやシャープ化は不要
- LANCZOSは標準的で汎用性が高い
- より大きな縮小率でも安定

**例外（NEARESTを使うべき場合）:**
- ドット絵・ピクセルアートを扱う場合
- 整数倍の縮小（640→320など）
- レトロゲーム風の見た目が欲しい場合

## PC-8801 アナログ8色モードのファイル形式

### PALファイル（16バイト）

I/Oポート $54〜$5B（各ポートがパレットインデックス0〜7に対応）に書き込む値を
そのままシーケンシャルに並べたもの。1色につき2バイト、同一ポートに連続出力する。

```
バイト1: 0b00_RRR_BBB  (bit7,6=00: R,Bプレーン設定)
バイト2: 0b01_000_GGG  (bit7,6=01: Gプレーン設定)
```

RGBの各値は3bit（0〜7）= 8bit値の上位3bit（`value >> 5`）

```python
r3, g3, b3 = r8 >> 5, g8 >> 5, b8 >> 5
byte1 = (r3 << 3) | b3   # 0b00_RRR_BBB
byte2 = 0x40 | g3         # 0b01_000_GGG
```

### プレーンファイル（.B / .R / .G、各16,000バイト）

640×200ピクセルのビットプレーン。1ピクセル1ビット、MSBが左端。
80バイト×200行 = 16,000バイト。

パレットインデックスとプレーンのビット対応：
```
インデックスのbit0 → Bプレーン（I/Oポート $5C）
インデックスのbit1 → Rプレーン（I/Oポート $5D）
インデックスのbit2 → Gプレーン（I/Oポート $5E）
```

デジタル8色のパレット（インデックス=ポート設定値）との対応：
| インデックス | G | R | B | 色 | RGB |
|------------|---|---|---|----|-----|
| 0 | 0 | 0 | 0 | 黒 | (0,0,0) |
| 1 | 0 | 0 | 1 | 青 | (0,0,255) |
| 2 | 0 | 1 | 0 | 赤 | (255,0,0) |
| 3 | 0 | 1 | 1 | 紫 | (255,0,255) |
| 4 | 1 | 0 | 0 | 緑 | (0,255,0) |
| 5 | 1 | 0 | 1 | 水色 | (0,255,255) |
| 6 | 1 | 1 | 0 | 黄 | (255,255,0) |
| 7 | 1 | 1 | 1 | 白 | (255,255,255) |

アナログモードではこのインデックスに任意の9bit色（512色中）を割り当て可能。
デジタルモードではこのパレットが固定で、PALファイルは不要（`--digital` オプション使用時）。

### 関連ファイル（圧縮後）

実機ディスクでは `.B`/`.R`/`.G` をLZE圧縮した `.BLZ`/`.RLZ`/`.GLZ` を使用。
export_pc88.py がデフォルトで圧縮済みファイルのみ出力し、`--save-planes` で生ファイルも出力できる。

## 今後の拡張案

1. 他の誤差拡散手法（Stucki, Sierra, Sierra-2, Stevenson-Arce）の追加
2. GUIツールの作成
3. バッチ処理機能
4. 動画への対応
5. アルゴリズム自動選択機能（画像の特徴から最適手法を提案）
