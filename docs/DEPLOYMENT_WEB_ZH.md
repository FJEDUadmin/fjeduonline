# 網頁上線部署指南（Production）

本文件說明如何把 DNA Adductomics 系統部署成可對外連線的網頁服務。

---

## 方案 A：VPS + Docker Compose（建議）

### 1) 伺服器需求

- Linux VPS（Ubuntu 22.04+）
- Docker + Docker Compose plugin
- 一個可用網域（例如 `adductomics.yourlab.org`）

### 2) 下載程式碼

```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>/backend
```

### 3) 準備 production 參數

```bash
cp .env.prod.example .env.prod
```

編輯 `.env.prod`：

- `DOMAIN=你的網域`
- `ACME_EMAIL=你的 email`

### 4) 啟動 production stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

此流程會啟動：

- `api`（FastAPI + gunicorn）
- `caddy`（反向代理 + HTTPS 憑證自動簽發）

### 5) 驗證

- 瀏覽器打開：`https://你的網域/`
- API 文件：`https://你的網域/docs`

---

## 方案 B：先本機對外測試（不含 TLS）

```bash
cd backend
docker compose up --build
```

打開：

- `http://<server-ip>:8000/`

---

## 重要維運建議

1. **定期備份資料夾**
   - `backend/data/`（SQLite、上傳檔、R 報告輸出）
2. **設定監控**
   - health endpoint：`/health`
3. **啟用防火牆**
   - 只開 `80/443`
4. **版本固定**
   - 每次上線前在 staging 先驗證 `pytest`

---

## 上線後快速檢查清單

- [ ] 首頁可開啟
- [ ] `/docs` 可開啟
- [ ] Demo 按鈕可跑成功
- [ ] HMDB/MassBank 上傳可成功
- [ ] Tool export (MS-DIAL/MZmine/Skyline) 可分析
- [ ] R report endpoint 回傳 `completed` 或 `skipped`（未安裝 R 時）
