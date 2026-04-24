# 高中物理講義圖片轉 Word 工具

這個小工具可以把你提供的題目/講義圖片，轉成可編輯的 `.docx` 檔案，方便後續人工校對與美編。

## 你可以做到的事情

- 批次讀取圖片（支援檔案路徑與 glob pattern）
- 自動 OCR 轉文字
- 產生含章節分頁的 Word 講義
- 套用基礎排版（標題、段落行距、字型）
- **可選**：接上 Mathpix API，讓數學公式以 LaTeX 形式輸出（辨識品質通常優於純 OCR）

## 安裝

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

另外請先安裝 Tesseract OCR 與繁中語言包：

- Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-tra`
- macOS (Homebrew): `brew install tesseract tesseract-lang`

## 使用方式

### 1) 基本模式（本機 Tesseract）

```bash
python lecture_builder.py "sci_*.jpg" -o physics_handout.docx --title "高二物理複習講義"
```

### 2) 公式優化模式（Mathpix，可選）

```bash
export MATHPIX_APP_ID=your_id
export MATHPIX_APP_KEY=your_key
python lecture_builder.py "sci_*.jpg" -o physics_handout.docx
```

## 注意事項

1. OCR 結果一定要人工校對（特別是題號、單位、上下標、圖說）。
2. 若要「重新繪圖」，建議把原圖拆成「文字層 + 圖形層」後，搭配專門繪圖工具（如 draw.io、Inkscape、GeoGebra）再貼回 Word。
3. Word 原生方程式物件（OMML）自動化較複雜；目前工具以高可用為主，建議搭配 MathType 或 Word 方程式編輯器做最後精修。

## 範例

```bash
python lecture_builder.py sci_1_cover.jpg sci_1_q16.jpg sci_1_q18.jpg -o sample.docx
```

輸出後你會得到一份 `sample.docx`，每張圖對應一個分頁段落。
