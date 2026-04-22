# 本機線上質譜統計分析系統

這是一個可在本機執行的網頁工具（Streamlit），專為質譜方法開發與常見期刊分析流程設計。

你可以：
- 上傳 CSV
- 勾選要做的統計分析
- 一鍵產生統計表與學術風格圖表
- 每次分析自動保存執行程式碼與結果（不需要每次手寫程式）

---

## 功能總覽

### 1) 常見質譜方法開發分析
- Descriptive statistics + 分布檢查（histogram/KDE/boxplot + Shapiro）
- Calibration curve（OLS / 1/x / 1/x²）
- LOD / LOQ（以 SD/slope 公式估算）
- Precision & Accuracy（CV%、RE%）
- Matrix effect / Recovery / Process efficiency

### 2) 常見 LC-MS 研究分析
- Two-group t-test + FDR + Volcano plot
- One-way ANOVA + FDR
- PCA（score plot + explained variance）

### 3) 可追蹤稽核紀錄（每次分析）
每次按下執行後，會在本機建立：

`analysis_runs/<timestamp>/`

內容包含：
- `input_<原始檔名>.csv`
- `metadata.json`
- `tables/*.csv`
- `figures/*.png`（300 dpi）
- `run_report.md`
- `run_code.py`（本次分析實際執行程式碼片段）

---

## 安裝與啟動

> 建議 Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

啟動後打開瀏覽器：

`http://localhost:8501`

---

## CSV 欄位需求建議

系統是「欄位可選式」，你可自由對應欄位；但不同分析需要不同資料欄位：

- Calibration / LOD-LOQ：至少要有 concentration 和 response 欄位
- Precision & Accuracy：需要 nominal 與 measured 欄位
- Matrix/Recovery：需要 level、sample type、response
  - sample type 需包含：`pre_spike`, `post_spike`, `neat`
- Two-group / ANOVA / PCA：需要群組欄位（類別）與多個數值特徵欄位

---

## 期刊等級圖表設定

已預設 publication-oriented 風格：
- 高解析度輸出（300 dpi）
- 白底與可讀格線
- 色盲友善配色（colorblind palette）
- 可直接在報告與投影片中使用

---

## 來源依據（分析項目設計）

分析項目對齊常見質譜/代謝體研究與方法驗證流程，涵蓋：
- 校正曲線與加權回歸
- LOD/LOQ 估算
- QC 精密度與準確度
- 基質效應與回收率
- t-test/ANOVA + FDR
- PCA 與火山圖（Volcano）

---

## 注意

- 本工具是本機分析輔助系統，不會自動取代法規審查或完整 SOP。
- 若需符合法規提交（例如 FDA/ICH），請依你的實驗室 SOP、儀器流程與指南進一步確認判定閾值。
