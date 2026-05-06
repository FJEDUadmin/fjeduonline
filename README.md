# 飛翔少年 AI 助教網站（Gemini）

這個 repo 現在提供一個可直接開啟的 **AI 解題網站 MVP**：

- `backend/`：FastAPI 後端 + 網站頁面
  - 首頁 `/`：飛翔少年 AI 助教網站介面（註冊/登入/解題）
  - API：`/auth/register`、`/auth/login`、`/me`、`/solve`
  - Gemini 解題串接（未設定金鑰時可 mock）
- `mobile/`：先前建立的 Expo 手機端範例（可選）

## 1) 啟動網站

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY（可先留空做流程測試）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

啟動後開啟：
- 網站首頁：`http://localhost:8000/`
- API 文件：`http://localhost:8000/docs`

## 2) 權限規則

- `in_company_class=true`：公司上課學生，免費使用
- `in_company_class=false`：註冊起算 `TRIAL_DAYS`（預設 30 天）

## 3) 環境變數（backend/.env）

- `GEMINI_API_KEY=`：Gemini API 金鑰
- `GEMINI_MODEL=gemini-1.5-flash`
- `ALLOW_MOCK_GEMINI=true`：未設定金鑰時是否允許 mock 回應
- `APP_DATABASE_PATH=./app.db`
- `TRIAL_DAYS=30`

## 4) 測試

```bash
cd backend
python3 -m unittest tests/test_entitlements.py
```

## 5) 上線前建議

- 串公司 SSO / 學生名單作為正式免費資格來源
- 增加 rate limit、行為審計與敏感題目安全策略
- 加上付費訂閱流程（試用到期後）
