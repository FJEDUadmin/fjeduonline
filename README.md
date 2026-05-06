# 飛翔少年 AI 助教網站（Gemini）

這個 repo 現在提供一個可直接開啟的 **AI 解題網站 MVP**，核心是「引導式思考」流程：

- 至少 **4 輪引導提問**後，才給詳細解析
- 學生答對：下一題升級（更進階）
- 學生答錯：下一題降階（更基礎）
- 若連續 3 次回答「不知道」：拒絕解答，請學生先回去思考後再回來

## 專案內容

- `backend/`：FastAPI 後端 + 網站頁面
  - 首頁 `/`：飛翔少年 AI 助教網站（註冊/登入/引導式對話）
  - API：`/auth/register`、`/auth/login`、`/me`
  - 引導式 API：`/coach/start`、`/coach/reply`
  - 備用直答 API：`/solve`

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

## 2) 引導式 API 流程

1. `POST /coach/start`
   - 輸入：`problem`, `grade`
   - 輸出：`session_id`, `question`, `step`

2. `POST /coach/reply`
   - 輸入：`session_id`, `answer`
   - 輸出：
     - `status=active` + `next_question`（繼續追問）
     - `status=completed` + `final_explanation`（完成解析）
     - `status=refused`（連續三次不知道，暫停解答）

## 3) 使用資格規則

- `in_company_class=true`：公司上課學生，免費使用
- `in_company_class=false`：註冊起算 `TRIAL_DAYS`（預設 30 天）

## 4) 環境變數（backend/.env）

- `GEMINI_API_KEY=`：Gemini API 金鑰
- `GEMINI_MODEL=gemini-1.5-flash`
- `ALLOW_MOCK_GEMINI=true`：未設定金鑰時是否允許 mock 回應
- `APP_DATABASE_PATH=./app.db`
- `TRIAL_DAYS=30`

## 5) 測試

```bash
cd backend
python3 -m unittest tests/test_entitlements.py tests/test_tutor_service.py
```

## 6) 上線前建議

- 串公司 SSO / 學生名單，做正式免費資格判斷
- 加入完整學習歷程儀表板（每輪答題診斷）
- 針對不同科目加上專屬 rubric 與評分規則
