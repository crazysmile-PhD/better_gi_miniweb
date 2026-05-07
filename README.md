# Better GI MiniWeb - 專案結構說明

本專案是一個基於 Flask 的 BetterGI Webhook 接收器，用於接收 BetterGI 發送的通知、截圖與事件資訊，並透過 SQLite 保存資料與 Web 頁面進行展示。

目前專案已可正常運作，但整體仍偏向「原型階段」，部分模組存在：

* 耦合過高
* 邏輯集中
* 缺少分層
* 缺少錯誤處理
* 可維護性不足

本文件主要用於：

* 開發者理解架構
* 後續重構
* 問題定位
* 功能擴充

---

# 專案結構

```text id="f8f4y7"
better_gi_miniweb/
│
├── app.py                # Flask 主入口
├── run.py                # 啟動腳本
├── models.py             # SQLite 資料模型
├── webhook.py            # Webhook 接收邏輯
├── routes.py             # Web 路由
├── templates/            # HTML 頁面
├── static/               # CSS / JS / 圖片
├── database.db           # SQLite 資料庫
└── requirements.txt      # Python 依賴
```

---

# 核心模組分析

## app.py

Flask 主程序。

目前問題：

* 初始化邏輯過多
* 路由與資料庫初始化混在一起
* 缺少 application factory
* 不利於大型化擴充

建議：

* 改成 create_app()
* 將 config 拆分
* 分離 blueprint

---

## webhook.py

負責接收 BetterGI POST webhook。

目前功能：

* 接收 JSON
* 解析通知內容
* 保存截圖
* 寫入 SQLite

目前問題：

### 1. 缺少驗證

目前任何人都能 POST：

```text id="z9n3eu"
http://127.0.0.1:222/
```

沒有：

* token
* signature
* source verify

存在安全風險。

---

### 2. Base64 截圖直接寫資料庫

目前直接保存 Base64：

問題：

* SQLite 容易膨脹
* 查詢速度下降
* 記憶體占用增加

建議：

```text id="s92a3s"
截圖保存成檔案
資料庫只保存路徑
```

---

### 3. 缺少錯誤處理

目前若：

* JSON 格式錯誤
* 截圖損壞
* 欄位缺失

可能直接報錯。

建議增加：

```python id="c4f0rk"
try:
    ...
except Exception:
    ...
```

並加入 logging。

---

## models.py

SQLite 資料模型。

目前問題：

* 欄位定義不明確
* 缺少 migration
* 缺少 ORM abstraction

建議：

* 使用 SQLAlchemy
* 加入 Alembic
* 增加 index

---

## routes.py

Web Dashboard 路由。

目前功能：

* 顯示最近通知
* 顯示截圖
* 顯示時間資訊

目前問題：

### 1. 無分頁

當資料量變大：

* 首頁會變慢
* SQLite 查詢壓力增加

建議：

```sql id="tr7yma"
LIMIT 50
OFFSET x
```

---

### 2. 缺少搜尋

目前只能看最近通知。

建議增加：

* 關鍵字搜尋
* 日期篩選
* 任務分類

---

## templates/

HTML 模板。

目前問題：

* UI 與邏輯耦合
* 缺少 component 化
* 缺少 loading 狀態
* 缺少即時更新

建議：

* 改用 Vue / React
* WebSocket 即時刷新
* 分離 API 與 Frontend

---

# 目前主要技術債

## 高耦合

目前：

```text id="b0i1n7"
Webhook
↓
資料處理
↓
SQLite
↓
HTML
```

幾乎全部直接耦合。

問題：

* 很難測試
* 很難替換資料庫
* 很難擴充 API

---

## 缺少分層

目前偏：

```text id="h8n6qz"
Route = Business Logic
```

應改成：

```text id="g5u8kx"
Route
↓
Service
↓
Repository
↓
Database
```

---

## 缺少 Logging

目前 debug 能力不足。

建議：

* logging module
* rotating log
* request log
* error trace

---

## 缺少 Config 管理

目前設定可能散落。

建議：

```text id="p7r2lc"
config/
├── dev.py
├── prod.py
└── default.py
```

---

# 建議重構方向

## Phase 1 - 穩定化

目標：

* 增加錯誤處理
* 增加 logging
* 增加 request validation
* 分離設定檔

預估：

1~2 天

---

## Phase 2 - 架構整理

目標：

* Flask Blueprint
* Service Layer
* SQLAlchemy ORM
* API 分層

預估：

3~5 天

---

## Phase 3 - 即時化

目標：

* WebSocket
* 即時通知
* 自動刷新
* 多裝置同步

預估：

5~7 天

---

# 未來可擴充方向

## BetterGI 控制中心

可進一步擴充：

* 多設備管理
* 任務控制
* 腳本狀態
* 遠端啟停
* OCR 結果分析

---

## 通知系統

未來可接入：

* Telegram
* Discord
* LINE Notify
* Email

---

## 資料分析

可加入：

* 任務成功率
* 執行時間統計
* 錯誤分析
* 長時間掛機分析

---

# 結論

目前專案已具備：

* Webhook 接收
* 本地保存
* 基礎 Dashboard

但仍偏向：

```text id="h2z5bm"
Prototype / MVP
```

若未來要大型化：

* 必須分層
* 必須降低耦合
* 必須增加 logging
* 必須拆分資料流
* 必須改善錯誤處理
