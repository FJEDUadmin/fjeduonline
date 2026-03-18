# Part IV. Project timeline (Gantt-style, 18 months)

目標：**18 個月內完成 ACS 投稿**，並同步建立可落地的「機器學習比對模組（ML comparison module）」。

> 若 NSTC 核定年期更長，可直接將 M11–M18 的外部驗證與法證化指標強化延伸到 24–36 個月。

## 18 個月期程（研究 + ML 模組）

| Phase / Months | Key objectives | Experiments / Outputs | Data / Model work | Deliverables |
|---|---|---|---|---|
| **M1–M2** Setup | 儀器與材料就緒、資料標準先行 | 採購 standards/columns；建立 sample ID；blank/QC 系統；玻璃/塑膠 swab 回收率試作 | 建立 Skyline 匯出模板；定義 feature（IS ratio、log-ratio）；建立資料字典與欄位稽核規則 | SOP v0.9；分析物清單；資料模板 v1 |
| **M3–M4** Method dev | 完成 Module 1–3 MRM 方法雛形 | 優化 transitions；校正曲線；LOD/LOQ；dry vs wet swab；極性/脂質萃取分流 | 建立 QC 接受門檻；分析腳本雛形；pilot PCA/OPLS-DA；建立 pair 生成規則（same/different） | Transition 表；方法驗證報告；ML baseline 規格書 |
| **M5–M6** Layer A complete | 受控條件 SOP 驗證 | Layer A 蒐集（10 donors × 2 days × full/partial × 2 conditions）；材質比較；儲存 mini-study（1d/7d/30d） | 建立初版 pair dataset；訓練 baseline（logistic / RF / XGBoost 擇一）；設定 donor-wise split | 內部可行性報告；基線模型 v0.1；robustness 初報 |
| **M7–M10** Layer B main collection | 建立核心 donor 資料庫 | 招募 80–120 donors；3 sessions；full+partial prints；重複 swab；批次隨機化 + 嚴格 QC | 進行 drift 監測；批次效應修正；持續訓練與版本化；建立 calibration pipeline（score→LR） | Dataset v1（≥3000 samples）；排名效能初報；模型 v0.5 |
| **M11–M12** Layer C challenges | 情境化外部驗證 | Powder+tape；aging（0–15d + 0–64d subset）；接觸污染情境；完成 storage challenge | 穩健性與錯誤分析；臨界條件失效模式；完成校正模型並固定 decision protocol | 外部驗證報告；最終模型候選（locked） |
| **M13–M14** Manuscript build | 圖表、SI、重現性封裝 | 重複關鍵實驗；最終方法表；案例型示範圖組 | 最終指標輸出（ROC、Cllr、Tippett、CMC）；整理可釋出程式與資料切分 | 論文草稿 + SI（SOP、表格、程式） |
| **M15–M16** Internal review | 投稿前內審與法規稽核 | 實驗紀錄與 raw file 稽核；IRB/ethics 確認；參考文獻與敘事收斂 | 敏感度分析；限制與適用範圍定稿；final reproducibility check | Manuscript v2；投稿期刊定案 |
| **M17–M18** Submission | 送件並保留修稿緩衝 | ACS 投稿；cover letter；回覆初步 editorial checks | 修稿實驗預案（buffer）；版本凍結（code/data/model） | 投稿完成證明；revision-ready 套件 |

---

## 機器學習比對模組（可實作規格）

### 1) 模組輸入
- **樣本層資料**：`sample_id`, `donor_id`, `session_id`, `phase`
- **定量通道**：analyte 訊號與 internal standard 訊號（`x`, `x_is`）
- **QC 附註**：blank、QC level、batch、operator、instrument date

### 2) 特徵工程
- 主特徵：`log((x+eps)/(x_is+eps))`
- 輔特徵：`log1p(channel)`、批次與漂移校正後殘差
- Pair 特徵：`abs_diff`、`feature product`（同向變動訊息）

### 3) 模型輸出
- `P(same donor | pair)`（校正後機率）
- `LR = p / (1-p)`（prior odds=1）
- 報告指標：AUC、EER、Cllr、Tippett、CMC Top-k

### 4) 開發門檻（建議 Go/No-Go）
- M6：donor-wise AUC 達成內部門檻（例如 >0.80）
- M10：跨批次效能衰退在可接受範圍（預先定義）
- M12：Layer C 情境下 Cllr 與錯判率可接受
- M16：可重現性與資料稽核完整，達投稿品質

---

## 與本 repo 目前程式對應

已建立 `ml_comparison_module/` 可直接支援：
- schema 驗證與 feature 建立
- same/different pair 生成
- donor-wise 訓練/驗證（避免身分洩漏）
- 機率校正與 LR 轉換
- ROC/Cllr/Tippett/CMC 指標輸出

可從 `python -m ml_comparison_module.demo` 先跑合成資料 smoke test，
再替換為你實際 Skyline 匯出資料。
