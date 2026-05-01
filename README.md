# 飛翔少年教育機構｜線上排課系統

這是一個可直接放在 GitHub（靜態網頁）使用的排課系統，支援：

- 排課（每週 / 每月）
- 依日期自動顯示星期
- 依上課 / 下課時間自動計算時數
- 每堂課費用、每月費用、總費用與成本計算
- 停課（跳課）日期、補課日期
- 排課後可直接在表格中更正日期
- 後台主檔管理（老師、年級、科目、時薪方案）
- 匯入主檔 Excel
- 匯出排課結果 Excel

---

## 1. 如何啟用

這個專案是純前端，無需安裝套件。

### 本機直接開啟
1. 下載專案
2. 直接用瀏覽器開啟 `index.html`

### 部署到 GitHub Pages（建議）
本專案已內建 `.github/workflows/deploy-pages.yml`，可用 GitHub Actions 自動部署。

1. Push 到 GitHub repository（`main` 或 `cursor/scheduling-system-3da6` 分支都會觸發）
2. 在 GitHub 專案設定 `Settings -> Pages`
3. Source 選擇 `GitHub Actions`
4. 到 `Actions` 頁面確認 `Deploy static site to GitHub Pages` 成功
5. 成功後在 Pages 頁面會看到上線網址

### 部署到 GitHub Pages（手動分支）
1. 在 GitHub 專案設定 `Settings -> Pages`
2. Source 選擇 `Deploy from a branch`
3. Branch 選 `main`（或你的分支）與 `/root`
4. 儲存後即可得到線上網址

---

## 2. 系統欄位對應（依需求）

1. 老師名稱 ✅  
2. 上課學生名稱 ✅  
3. 上課年級 ✅  
4. 上課科目 ✅  
5. 上課日期（自動帶出星期）✅  
6. 重複週期（每週 / 每月）✅  
7. 排課長度（月）✅  
8. 上課時間 ✅  
9. 下課時間（自動計算總時數）✅  
10. 課程學費時薪 ✅  
11. 每堂課費用 ✅  
12. 每個月費用 ✅  
13. 每次收的總費用 ✅（總覽卡片）

其他：
- 停課 / 跳課日期功能 ✅
- 補課日期功能 ✅
- 排課結果可更正日期 ✅
- 成本欄位（教師薪水、總成本）✅
- 後台可匯入 Excel 主檔 ✅
- 網頁顯示與 Excel 匯出 ✅

---

## 3. 主檔 Excel 匯入格式

建議在同一個 Excel 內建立以下工作表（Sheet）：

### Sheet: `Teachers`
欄位可用：
- `name` 或 `老師名稱`
- `salary` 或 `教師時薪`

### Sheet: `Grades`
欄位可用：
- `name` 或 `年級`

### Sheet: `Subjects`
欄位可用：
- `name` 或 `科目`

### Sheet: `HourlyRates`
欄位可用：
- `name` 或 `方案名稱`
- `value` 或 `時薪`

> 匯入時若某個工作表不存在，系統會保留原本資料。

---

## 4. 排課結果匯出

匯出 Excel 後會包含：

1. `排課明細`：每堂課完整資料
2. `月份費用`：每月堂數、時數、費用、成本、毛利
3. `總覽`：堂數、總時數、總費用、總成本、毛利

---

## 5. 技術說明

- `index.html`：頁面與表單
- `styles.css`：樣式
- `app.js`：所有業務邏輯（排課、計算、匯入匯出、儲存）
- 使用 `localStorage` 保留資料
- 使用 `SheetJS (xlsx)` 完成 Excel 匯入 / 匯出

