# CSV + GPT 自動統計分析頁面

本專案已改為「提示詞驅動」分析流程：

- 上傳 CSV
- 用白話輸入分析目標（提示詞）
- 系統透過 GPT 自動產生分析程式碼
- 自動執行並輸出統計表與圖表
- 每次分析自動保存程式碼與輸出

---

## 你會得到什麼

每次執行都會建立：

`analysis_runs/<timestamp>/`

包含：
- `input_<原始檔名>.csv`
- `metadata.json`
- `tables/*.csv`
- `figures/*.png`
- `run_report.md`
- `run_code.py`（GPT 生成並執行的程式碼）

---

## 安裝與啟動

> 建議 Python 3.12

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

啟動後開啟：

`http://localhost:8501`

---

## GPT 連動設定

側欄可設定：
- API Key
- 模型名稱（預設 `gpt-4o-mini`）
- Base URL（如使用相容 API 可填）

也可用環境變數：

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="..."
```

---

## 使用方式（最簡）

1. 上傳 CSV
2. 在「分析目標提示詞」輸入白話需求，例如：

   `請比較三組樣品在各 transition 的 absolute matrix effect，畫分組柱狀圖加 SD 誤差棒並加 y=1 參考線，列出每組平均值。`

3. 點擊「用 GPT 自動分析並產出圖表」

---

## 注意事項

- GPT 生成程式碼會在受限環境中執行，但仍建議僅用於研究分析與報表輔助。
- 若資料量很大，建議先在 CSV 做欄位精簡，可降低推理延遲。
