# ESP32 SCT-013-000 數據收集與網頁儀表板

本專案提供了一套完整的解決方案，用於將 ESP32 傳輸的 SCT-013-000 電流感測器數據解析並儲存至 SQLite 資料庫，並透過極具科技感的網頁儀表板 (Dashboard) 進行即時數據與歷史趨勢的視覺化呈現。

## 📂 檔案結構
- `db.py`: SQLite 資料庫模組，負責初始化資料庫、寫入與查詢讀數及計算統計指標。
- `parser.py`: 數據解析工具，支援「讀取 Log 檔案」與「即時串流 Serial COM Port」雙模式。
- `app.py`: Flask 後端伺服器，提供網頁 Dashboard 與 API 接口。
- `templates/index.html`: 前端 Dashboard 介面，使用 Chart.js 繪製電流與功率折線圖。
- `generate_mock_data.py`: 用於產生測試用的模擬 Log 檔案。

---

## 🛠️ 安裝與準備工作

1. **安裝 Python 3.x**
2. **安裝所需套件**
   在命令提示字元 (cmd/PowerShell) 中，切換至本專案目錄並執行：
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 使用說明

### 1. 匯入已存檔的 Log 文字檔 (檔案模式)
如果您已經有從 Arduino IDE 序列埠監控視窗複製下來的 Log 檔案（例如包含 `09:49:15.511 -> Current_RMS(A):0.050,Apparent_Power(W):5.5` 內容的文字檔 `logs.txt`）：

將檔案放入專案目錄，並執行：
```bash
python parser.py --file logs.txt
```
*提示：預設會將日期設定為今天 (例如 `2026-06-02`)。如果您需要指定特定日期，可加入 `--date` 參數：*
```bash
python parser.py --file logs.txt --date 2026-06-01
```

### 2. 即時讀取 ESP32 序列埠資料 (序列埠模式)
如果您的 ESP32 正接在電腦上，想要即時讀取資料並儲存：

確認您的 ESP32 COM Port 編號（例如 `COM3`），然後執行：
```bash
python parser.py --port COM3 --baud 115200
```
*程式將即時在螢幕印出讀數，並寫入 `sensor_data.db` 資料庫。按 `Ctrl + C` 可安全退出。*

### 3. 開啟網頁 Dashboard 監控儀表板
啟動網頁伺服器：
```bash
python app.py
```
啟動後，使用瀏覽器打開以下網址：
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

網頁包含：
- **關鍵指標 (KPIs)**: 最新電流、最大電流、最新功率、累計筆數、估算消耗電能。
- **即時圖表**: 每 3 秒自動更新的電流與視在功率折線圖。
- **歷史數據**: 最近 20 筆記錄的詳細列表。

---

## 🧪 測試驗證 (產生模擬數據)
如果您手邊暫時沒有 Log 檔或 ESP32 硬體，可以執行以下指令來生成模擬資料並進行測試：

1. 產生 50 筆模擬 Log 檔：
   ```bash
   python generate_mock_data.py
   ```
2. 將模擬資料寫入資料庫：
   ```bash
   python parser.py --file mock_logs.txt
   ```
3. 啟動網頁伺服器查看 Dashboard：
   ```bash
   python app.py
   ```
