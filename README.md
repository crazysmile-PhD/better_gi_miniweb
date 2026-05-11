# Better GI MiniWeb

Better GI MiniWeb 是一個輕量級 Flask Web 應用，用來接收 BetterGI 的 Webhook 通知、結果、時間戳與 Base64 截圖，並將資料寫入 SQLite，再透過瀏覽器 Dashboard 顯示最新事件。

本次重構已移除對舊版 Runtime 的硬性依賴，專案目標是降低使用者電腦上的多版本環境負擔：本分支目前以 Python 3.14 為目標版本；若後續希望支援更多使用者環境，可以再評估放寬到 Python 3.12 或 3.13。

## 專案用途

* 接收 BetterGI 以 `POST /` 發送的 JSON Webhook。
* 將事件資料寫入本機 SQLite 資料庫 `bettergi.db`。
* 以 `GET /` 顯示最近 10 筆通知與截圖。
* 以 `GET /image/<int:image_id>` 讀取資料庫中的 Base64 截圖並回傳 PNG。
* 以 `GET /health` 提供啟動與監控驗證。

## 目前 Runtime 與套件版本

| 類別 | 版本策略 |
| --- | --- |
| Python | `>=3.14,<3.15`，本分支目前以 Python 3.14 為目標 |
| Flask | `>=3.1.3,<3.2` |
| Flask-SQLAlchemy | `>=3.1.1,<3.2` |
| SQLAlchemy | `>=2.0.49,<2.1`，使用 SQLAlchemy 2.x 查詢與 Session API |
| gevent | `>=26.4.0,<27.0` |
| Werkzeug | `>=3.1.8,<3.2` |
| Jinja2 | `>=3.1.6,<3.2` |
| MarkupSafe | `>=3.0.3,<3.1` |
| itsdangerous | `>=2.2.0,<2.3` |
| click | `>=8.3.3,<8.4` |

> 專案目前沒有 Node.js、Frontend build pipeline、.NET、Dockerfile 或 docker-compose 設定，因此不需要額外安裝 Node.js、npm、.NET Runtime 或 Docker 才能啟動。

## 檔案結構

```text
better_gi_miniweb/
├── .github/workflows/python-app.yml  # GitHub Actions：Python 3.14 安裝、Ruff lint、pytest
├── app.py                            # WSGI / Flask CLI / python app.py 相容入口
├── bettergi_miniweb/                 # Flask package：factory、config、models、routes、services
│   ├── app_factory.py                # create_app、extensions 初始化、blueprint registration
│   ├── config.py                     # BASE_DIR、DB URI、PORT、LOG_LEVEL、Webhook auth 與基本 config mapping
│   ├── extensions.py                 # Flask extension instances
│   ├── models.py                     # SQLAlchemy models
│   ├── routes/                       # Blueprint route modules
│   └── services/                     # Webhook service logic
├── docs/ARCHITECTURE.md              # 開發者架構與維護規則
├── init_database.py                  # SQLite 初始化與 post_load 匯入工具
├── main.py                           # 舊入口相容層，保留 from main import app 用法
├── pyproject.toml                    # 專案 metadata、Python 版本要求、pytest / ruff 設定
├── requirements.txt                  # Runtime 相依套件版本範圍
├── run.py                            # gevent 啟動器與 Runtime / 依賴檢查
├── static/css/style_v2.css           # Dashboard 樣式
├── templates/base.html               # Dashboard Jinja2 模板
├── test.py                           # 開發用原始 Webhook 請求捕捉服務
└── tests/test_app.py                 # 基本啟動、Webhook、SQLite、圖片端點測試
```

## 主要檔案功能

### `app.py`

相容入口，包含：

* `app = create_app()`：保留 WSGI / Flask CLI / `python app.py` 用法。
* 匯出 `create_app`、`db`、`PostData`、`normalize_webhook_payload`、`save_webhook_payload`。
* 不放 route、model 或 service 實作。

### `bettergi_miniweb/`

核心 Flask package，包含：

* `app_factory.py`：建立 Flask app、套用設定、初始化 SQLAlchemy、註冊 blueprints。
* `config.py`：集中管理 `BASE_DIR`、預設 DB URI、預設 port、`LOG_LEVEL`、Webhook auth env vars 與基本 config mapping。
* `models.py`：SQLite 資料模型。
* `routes/`：`POST /`、`GET /`、`GET /health`、`GET /image/<int:image_id>` blueprints。
* `services/`：Webhook payload 驗證、正規化與保存邏輯。

### `run.py`

正式啟動入口，負責：

* 檢查 Python 是否為 `3.14+`。
* 檢查 Flask / gevent 等依賴是否已安裝。
* 自動建立 SQLite tables。
* 使用 gevent WSGI server 啟動服務。

### `init_database.py`

資料庫工具，負責：

* 建立 SQLite tables。
* 匯入 `post_load/*.txt` 中由 `test.py` 捕捉的 JSON。

### `main.py`

相容舊版使用方式。新程式碼建議直接使用 `app.py`，但既有 `from main import app` 或 `Post_data` 用法仍可運作。

### `test.py`

開發輔助服務，用來把收到的原始 Webhook request 存到 `post_load/`，方便排查 BetterGI 實際送出的 payload。

## 安裝方式

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

### Windows CMD

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

## 快速啟動

安裝依賴後執行：

```bash
python run.py
```

啟動成功後開啟：

* Dashboard：<http://127.0.0.1:222/>
* Webhook URL：<http://127.0.0.1:222/>
* Health Check：<http://127.0.0.1:222/health>

`run.py` 會在啟動時檢查 Python 版本與 runtime dependencies，並在 Flask application context 內安全執行 `db.create_all()` 建立缺少的 SQLite tables。

## 環境變數

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | gevent WSGI server 綁定的 host。 |
| `PORT` | `222` | Dashboard、Webhook 與 health check 使用的 port。 |
| `DATABASE_URL` | `sqlite:///bettergi.db` | SQLAlchemy database URI；預設資料庫位於專案根目錄。 |
| `LOG_LEVEL` | `INFO` | Flask app logging level。 |
| `WEBHOOK_TOKEN` | 空字串 | 選填；設定後需提供 `Authorization: Bearer <token>` 或 `X-Webhook-Token`。 |
| `WEBHOOK_SIGNATURE_SECRET` | 空字串 | 選填；設定後需提供以 raw request body 計算的 `X-Webhook-Signature` HMAC-SHA256。 |

macOS / Linux 修改 port 範例：

```bash
PORT=8080 python run.py
```

Windows PowerShell 修改 port 範例：

```powershell
$env:PORT = "8080"
python run.py
```

## Webhook API 範例

最小可接受 payload：

```bash
curl -X POST http://127.0.0.1:222/ \
  -H "Content-Type: application/json" \
  -d '{"event":"notification","message":"hello from BetterGI"}'
```

若已設定 `WEBHOOK_TOKEN`，請加入 bearer token：

```bash
curl -X POST http://127.0.0.1:222/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $WEBHOOK_TOKEN" \
  -d '{"event":"notification","message":"hello from BetterGI"}'
```

若已設定 `WEBHOOK_SIGNATURE_SECRET`，需用原始 request body 計算 HMAC-SHA256，並送出 `X-Webhook-Signature: sha256=<hex digest>`。

完整範例：

```json
{
  "event": "notification",
  "result": "success",
  "timestamp": "2026-05-07T00:00:00Z",
  "message": "任務完成\n其他詳細資訊",
  "screenshot": "iVBORw0KGgo..."
}
```

欄位說明：

* `event`：必填，非空字串。
* `result`：選填，任務結果。
* `timestamp`：選填，BetterGI 發出的時間。
* `message`：選填，顯示在 Dashboard 的訊息。
* `screenshot`：選填，Base64 PNG 字串。

如果設定 `WEBHOOK_TOKEN`，請在請求中提供 `Authorization: Bearer <token>` 或 `X-Webhook-Token`。如果設定 `WEBHOOK_SIGNATURE_SECRET`，請在 `X-Webhook-Signature` 提供 raw request body 的 HMAC-SHA256 hex digest；支援純 hex 或 `sha256=<hex>` 格式。


## For Developers

更完整的架構與維護規則請先閱讀 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。該文件說明 request flow、模組責任邊界、新增 route/service 的步驟、model/config 修改注意事項、測試規則與 PR checklist。

### 安裝開發依賴

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest ruff
```

### 執行測試與檢查

```bash
python -m compileall .
ruff check .
pytest
git diff --check
test ! -e bettergi.db
```

測試應使用 temporary SQLite，不應污染專案根目錄的 `bettergi.db`。

### 入口與 factory 的用途差異

* `bettergi_miniweb.app_factory.create_app()`：主要 application factory，負責建立 Flask app、載入 config、初始化 extensions 並註冊 blueprints。
* `app.py`：相容 WSGI / Flask CLI / `python app.py` 的入口，仍匯出 `app`、`create_app`、`db`、`PostData` 與 webhook service helpers。
* `main.py`：舊入口相容層，保留 `from main import app`、`Post_data`、`save_data` 等歷史用法；未確認舊依賴前不要刪除。

### 目前架構拆分原則

本專案是小型 Flask 工具，不採用大型 enterprise architecture。現有 package 邊界已足夠，後續重構目標是降低維護成本，不是繼續增加檔案或抽象層。

* `app_factory.py` 只保留 app 建立、config loading、extension 初始化與 blueprint registration；不要把 business logic 塞回 `app_factory.py`。
* `routes/` 只處理 HTTP request/response 與 status code；不要讓 route 直接承擔複雜資料處理。
* `services/` 放可測試的 business/application logic，例如 webhook payload normalization 與 persistence。
* `models.py` 放 SQLAlchemy models；任何 schema 變更都需要獨立規劃 migration / 相容策略。
* `routes/health.py`、`extensions.py`、`routes/__init__.py`、`services/__init__.py` 雖然偏薄，但目前可接受，不要只為了減少檔案數而合併。
* 只有在兩個檔案永遠一起修改、沒有不同依賴、沒有不同測試需求，且合併後責任仍清楚時，才允許合併。
* 不要新增 `repositories/`、`domain/`、`use_cases/`、`interfaces/`、`adapters/`、`schemas/`、`dto/`、`managers/` 或 generic helpers。
* 不要把 security、migration、file storage refactor 混在同一個 PR。

## 驗證方式

首次設定測試工具：

```bash
python -m pip install -r requirements.txt
python -m pip install pytest ruff
```

每次提交前建議執行：

```bash
ruff check .
pytest
git diff --check
test ! -e bettergi.db
```

測試應使用 temporary SQLite，不應污染專案根目錄的 `bettergi.db`；如果手動啟動後產生 `bettergi.db`，請在提交前移除。

手動啟動驗證：

1. 執行 `python run.py`。
2. 開啟 <http://127.0.0.1:222/health>，應回傳 `{"status":"ok"}`。
3. 用 README 的 `curl` 範例送出 Webhook。
4. 開啟 <http://127.0.0.1:222/>，應看得到新事件。
5. 確認專案根目錄已建立 `bettergi.db`；手動驗證結束且不需保留資料時可刪除。

## 常見問題

### 啟動時顯示 Python 版本太舊

請安裝本分支目前支援的 Python 3.14，重新建立 `.venv`，再執行：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 啟動時顯示 Missing dependency

代表尚未安裝 requirements，請先啟用虛擬環境並執行：

```bash
python -m pip install -r requirements.txt
```

### Dashboard 沒有資料

請確認 BetterGI Webhook URL 指向 `http://127.0.0.1:222/`，且用 `POST` 傳送 JSON。也可以先使用 README 的 `curl` 範例確認服務是否正常。

### `/image/<int:image_id>` 回傳 Invalid image data

該筆資料的 `screenshot` 欄位不是合法 Base64。請檢查 BetterGI 發出的 payload，或使用 `test.py` 捕捉原始請求。

## 已知技術債

* 截圖仍以 Base64 文字保存於 SQLite，資料量大時會造成資料庫膨脹。
* Webhook 已支援選填 token 與 HMAC-SHA256 signature 驗證；若公開到外網，仍建議搭配 HTTPS、反向代理、來源限制與 rate limit。
* 目前 Dashboard 無分頁、搜尋、篩選與即時更新。
* 尚未導入 Alembic migration；資料模型調整仍依賴 `db.create_all()`。
* 前端仍是單一 Jinja2 template，尚未 component 化。

## 後續建議重構方向

後續改動請維持小 PR、單一目的，不要把 security、migration、file storage 或大型 UI 調整混在同一個 PR。

1. 將截圖改存為檔案或物件儲存，SQLite 僅保存路徑與 metadata。
2. 強化外網部署安全，例如 HTTPS、反向代理、來源 IP 限制、rate limit 與更完整的部署範例。
3. 導入 Alembic migration 管理資料庫 schema。
4. 增加 Dashboard 分頁、搜尋、日期篩選與自動刷新。
5. 增加更多 pytest 測試與端到端啟動測試。

以上項目應拆成獨立 PR；不要把 security、migration、file storage 或 Dashboard 功能混在同一次變更。

已知相容性注意事項：

* `POST /` 要求 `Content-Type: application/json`，且 body 必須是 JSON object。
* `event` 欄位為必填非空字串；缺少時會回傳 HTTP 400。
* 啟動器不會自動執行 `pip install`，避免在使用者不知情時修改全域 Python；請在虛擬環境內明確執行安裝指令。
* 首次啟動不建立 `client.txt` sentinel file；資料庫初始化改為每次啟動安全執行 `db.create_all()`。
