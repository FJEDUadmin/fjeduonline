# AI 解題助教 App（Gemini）

這個 repo 現在包含一套可啟動的 MVP 架構：

- `backend/`：FastAPI 後端，負責
  - 註冊/登入（簡化版 token session）
  - 方案判斷：
    - 公司上課學生：免費
    - 非公司學生：註冊起 30 天試用
  - 串接 Gemini 解題（或未設定金鑰時 mock 回應）
- `mobile/`：Expo React Native 手機 App，提供
  - 註冊/登入
  - 顯示方案狀態
  - 發送題目到後端拿解答

## 1) 後端啟動

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY（可先留空做流程測試）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

主要 API：
- `POST /auth/register`
- `POST /auth/login`
- `GET /me`
- `POST /solve`

## 2) 手機端啟動

```bash
cd mobile
cp .env.example .env
# 如需連遠端 API，修改 EXPO_PUBLIC_API_BASE_URL
npm install
npm run start
```

## 3) 權限規則

- `in_company_class=true`：永久免費
- `in_company_class=false`：`trial_started_at + TRIAL_DAYS` 內可用（預設 30 天）

> 正式上線建議：
> - 將登入改為公司既有帳號系統（SSO / 校務系統）
> - 以後端資料庫權限為唯一判斷來源
> - 加上 rate limit、審計 log、訂閱/付款機制

## 4) 測試（後端規則）

```bash
cd backend
python3 -m unittest tests/test_entitlements.py
```
