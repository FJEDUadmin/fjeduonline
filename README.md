# DNA Adductomics Platform (Foundation Build)

這個 repository 是一個 **DNA adductomics 分析平台** 的起始實作，目標是建立可投稿等級（可重現、可擴充、可驗證）的系統基礎。

目前版本提供：

- DNA adduct 資料庫統一 schema（可匯入多來源資料）
- HMDB + MassBank CSV connector（已具備兩個正式 databank adapter）
- MS-DIAL / MZmine / Skyline tool export parser hub
- LC-MS MRM / Neutral Loss (NL) 分析流程
- Adduct 候選識別與信心分數排序（scoring model v3，含 confidence level）
- 初版 pathway enrichment 分析
- FastAPI 服務介面與測試
- Web dashboard（檔案上傳 + 分析結果可視化）
- 分析 run metadata（run_id、參數、版本）可追溯
- R 統計模組骨架（API 可觸發，輸出 report artifact）

---

## 1) 系統目標

你希望的最終系統包含：

1. 整合學術 adductomics data bank（多資料源、可持續更新）
2. 接收 LC-MS MRM / NL 數據進行分析
3. 回傳可能 adduct identity
4. 進行代謝途徑／pathway 層級解釋
5. 具備期刊發表所需的再現性（reproducibility）與審計能力

本版本先完成「可運作骨架」，為後續擴充建立乾淨架構。

---

## 2) 專案結構

```text
backend/
  src/adductomics_api/
    main.py                 # FastAPI entrypoint
    config.py               # runtime settings
    schemas.py              # pydantic schemas
    repository.py           # sqlite repository
    static/                 # dashboard UI (HTML/CSS/JS)
    services/
      connectors.py         # data-bank connector abstraction
      identifier.py         # adduct candidate scoring
      pathway.py            # pathway enrichment
      pipeline.py           # end-to-end orchestration
  tests/
  data/
  Dockerfile
  docker-compose.yml
docs/
  ARCHITECTURE.md
```

---

## 3) 本地執行

### Python 直接啟動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn adductomics_api.main:app --reload
```

API 啟動後：

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Docker 啟動

```bash
cd backend
docker compose up --build
```

---

## 4) 快速工作流程

1. 匯入 adduct 資料庫（CSV）
2. 提交 MRM/NL transition（JSON 或 CSV）
3. 取得候選 adduct 與 pathway enrichment
4. 保存/比對每次分析 metadata（參數與 scoring 版本）
5. 透過 R module 產生統計摘要報告

詳細 API payload 請看 `/docs` 自動文件。

Dashboard：

- `http://127.0.0.1:8000/`

---

## 5) 下一步建議（期刊等級）

1. **資料庫連接器擴充**：PubChem、METLIN 匯出、文獻 supplementary table（HMDB/MassBank 已完成）
2. **結構層級特徵**：同位素 pattern、RT model、MS/MS fragment rules
3. **統計嚴謹化**：FDR 控制、批次效應校正、跨儀器校準
4. **可追溯性**：分析參數版本化、immutable run artifact、審計日誌
5. **前端與協作**：使用者/角色權限、專案管理、結果分享與審閱

---

## 6) 注意事項

目前 sample data 為示範資料，不代表完整生物學知識庫。實際研究發表前，需建立：

- 資料源授權與版本策略
- 實驗與計算管線 SOP
- 外部驗證資料集與 blind test protocol
