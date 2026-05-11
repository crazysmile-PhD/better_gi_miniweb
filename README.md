# Better GI MiniWeb

Better GI MiniWeb 是一個輕量級 Flask Web 應用，用來接收 BetterGI 的 Webhook 通知、結果、時間戳與截圖，將事件 metadata 寫入 SQLite，將新截圖寫入檔案儲存，再透過瀏覽器 Dashboard 顯示事件。

本分支目前以 Python 3.14 為目標版本；若後續希望支援更多使用者環境，可以再評估放寬到 Python 3.12 或 3.13。

## 專案用途

* 接收 BetterGI 以 `POST /` 發送的 JSON Webhook。
* 將事件資料寫入本機 SQLite 資料庫 `bettergi.db`。
* 將新 webhook 的 Base64 PNG 截圖解碼後保存到 `instance/screenshots/` 或自訂目錄，SQLite 僅保存相對路徑。
* 以 `GET /` 顯示可分頁、搜尋、篩選、可自動刷新的 Dashboard。
* 以 `GET /image/<int:image_id>` 讀取檔案截圖，並相容讀取舊版 SQLite Base64 截圖。
* 以 `GET /health` 提供啟動與監控驗證。

## 目前 Runtime 與套件版本

| 類別 | 版本策略 |
| --- | --- |
| Python | `>=3.14,<3.15`，本分支目前以 Python 3.14 為目標 |
| Flask | `>=3.1.3,<3.2` |
| Flask-SQLAlchemy | `>=3.1.1,<3.2` |
| SQLAlchemy | `>=2.0.49,<2.1` |
| Alembic | `>=1.17.2,<1.18` |
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
├── alembic.ini                      # Alembic CLI 設定
├── app.py                           # WSGI / Flask CLI / python app.py 相容入口
├── bettergi_miniweb/                # Flask package：factory、config、models、routes、services
│   ├── app_factory.py               # create_app、extensions 初始化、blueprint registration
│   ├── config.py                    # BASE_DIR、DB URI、PORT、LOG_LEVEL、截圖目錄與 config mapping
│   ├── extensions.py                # Flask extension instances
│   ├── models.py                    # SQLAlchemy models
│   ├── routes/                      # Blueprint route modules
│   └── services/                    # Webhook 與截圖保存 service logic
├── docs/ARCHITECTURE.md             # 開發者架構與維護規則
├── init_database.py                 # SQLite 初始化與 post_load 匯入工具
├── main.py                          # 舊入口相容層，保留 from main import app 用法
├── migrations/                      # Alembic migration environment 與 versions
├── pyproject.toml                   # 專案 metadata、Python 版本要求、pytest / ruff 設定
├── requirements.txt                 # Runtime 相依套件版本範圍
├── run.py                           # gevent 啟動器與 Runtime / 依賴檢查
├── static/css/style_v2.css          # Dashboard 樣式
├── templates/
│   ├── base.html                    # 共用 HTML skeleton
│   ├── dashboard.html               # Dashboard page template
│   └── partials/                    # event card、filter form、pagination partials
└── tests/test_app.py                # Webhook、Dashboard、圖片端點與相容入口測試
```

## 主要檔案功能

### `app.py`

相容入口，包含：

* `app = create_app()`：保留 WSGI / Flask CLI / `python app.py` 用法。
* 匯出 `create_app`、`db`、`PostData`、`normalize_webhook_payload`、`save_webhook_payload`。
* 不放 route、model 或 service 實作。

### `bettergi_miniweb/`

核心 Flask package，包含：

* `app_factory.py`：建立 Flask app、套用設定、初始化 SQLAlchemy、註冊 blueprints。`db.create_all()` 仍保留為空資料庫的輕量 fallback；正式 schema 變更以 Alembic migration 為準。
* `config.py`：集中管理 `BASE_DIR`、預設 DB URI、預設 port、截圖儲存目錄、`LOG_LEVEL` 與基本 config mapping。
* `models.py`：SQLite 資料模型，包含舊版 `screenshot` Base64 欄位與新版 `screenshot_path` 檔案路徑欄位。
* `routes/`：`POST /`、`GET /`、`GET /health`、`GET /image/<int:image_id>` blueprints。
* `services/`：Webhook payload 驗證、正規化、截圖解碼與保存邏輯。

### `migrations/`

Alembic migration 環境：

* `202605110001_baseline_post_data.py`：目前 `post_data` schema baseline。
* `202605110002_add_screenshot_path.py`：新增 `screenshot_path` 欄位，讓新截圖以檔案儲存。

### `run.py`

正式啟動入口，負責：

* 檢查 Python 是否為 `3.14+`。
* 檢查 Flask / gevent 等依賴是否已安裝。
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

`run.py` 會在啟動時檢查 Python 版本與 runtime dependencies。`create_app()` 仍會安全執行 `db.create_all()` 作為輕量 fallback，方便空 SQLite 在未執行 Alembic 時仍可啟動；正式 schema 變更與既有資料庫升級請使用 Alembic migration。

## 環境變數

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | gevent WSGI server 綁定的 host |
| `PORT` | `222` | Dashboard、Webhook、health check 使用的 port |
| `DATABASE_URL` | `sqlite:///bettergi.db` | SQLAlchemy database URI |
| `LOG_LEVEL` | `INFO` | Flask app logging level |
| `SCREENSHOT_STORAGE_DIR` | `instance/screenshots/` | 新截圖檔案儲存目錄；DB 只存相對檔名 |
| `WEBHOOK_TOKEN` | 未設定 | 選填 bearer token |
| `WEBHOOK_SIGNATURE_SECRET` | 未設定 | 選填 HMAC-SHA256 簽章密鑰 |

`WEBHOOK_TOKEN` 設定後，`POST /` 必須帶 `Authorization: Bearer <token>` 或 `X-Webhook-Token: <token>`。

`WEBHOOK_SIGNATURE_SECRET` 設定後，`POST /` 必須帶 `X-Webhook-Signature: sha256=<hex digest>`。

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

若已設定 `WEBHOOK_SIGNATURE_SECRET`，需用原始 request body 計算 HMAC-SHA256，並送出：

```text
X-Webhook-Signature: sha256=<hex digest>
```

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
* `screenshot`：選填，Base64 PNG 字串。新資料會解碼寫入檔案，SQLite 只保存 `screenshot_path`；舊資料庫的 Base64 `screenshot` 欄位仍可由 `/image/<id>` 讀取。

## Screenshot storage

新 webhook payload 若包含合法 Base64 `screenshot`：

1. `save_webhook_payload()` 先寫入事件 metadata 並取得 `post_data.id`。
2. 服務將 Base64 解碼為 bytes。
3. 檔案寫入 `SCREENSHOT_STORAGE_DIR` 下的安全相對檔名，例如 `post_123.png`。
4. SQLite 保存 `screenshot_path`，不再長期保存大型 Base64 字串。
5. `/image/<id>` 優先讀取 `screenshot_path` 指向的檔案；若不存在，才 fallback 到舊版 `screenshot` Base64 欄位。

`SCREENSHOT_STORAGE_DIR` 必須是應用程式可寫入的本機目錄；預設的 `instance/screenshots/` 已在 `.gitignore` 中排除，請不要提交 runtime 截圖檔。

## Alembic migration

從空資料庫建立 schema：

```bash
python -m alembic upgrade head
```

使用非預設 SQLite 檔案或其他 SQLAlchemy URI：

```bash
DATABASE_URL=sqlite:////path/to/bettergi.db python -m alembic upgrade head
```

新增 schema 變更時：

1. 更新 `bettergi_miniweb/models.py`。
2. 新增 `migrations/versions/<revision>_<description>.py`。
3. 在 temporary database 上執行 `python -m alembic upgrade head` 驗證。
4. 執行 `ruff check .`、`pytest`、`git diff --check`、`test ! -e bettergi.db`。

## Dashboard 查詢功能

Dashboard 無 query parameter 時維持顯示最新事件。可使用以下 query parameters：

| Parameter | 說明 |
| --- | --- |
| `page` | 頁碼，預設 `1` |
| `per_page` | 每頁筆數，預設 `10`，上限 `100` |
| `q` | 搜尋 `event` / `message` / `result` |
| `result` | 依 `result` 精準篩選，例如 `success` |
| `date_from` | 依 `create_time` 起日篩選，格式 `YYYY-MM-DD` |
| `date_to` | 依 `create_time` 迄日篩選，格式 `YYYY-MM-DD` |
| `refresh` | 自動刷新秒數；`0` 或省略代表不自動刷新 |

範例：

```text
http://127.0.0.1:222/?q=notification&result=success&page=2&per_page=20&refresh=30
```

若日期格式錯誤，Dashboard 會顯示提示並忽略該日期條件。

## For Developers

更完整的架構與維護規則請先閱讀 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

該文件說明 request flow、screenshot storage flow、migration policy、dashboard query / pagination flow、template structure、模組責任邊界、新增 route/service 的步驟、測試規則與 PR checklist。

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

### 目前架構拆分原則

本專案是小型 Flask 工具，不採用大型 enterprise architecture。現有 package 邊界已足夠，後續重構目標是降低維護成本，不是繼續增加檔案或抽象層。

* `app_factory.py` 只保留 app 建立、config loading、extension 初始化與 blueprint registration；不要把 business logic 塞回 `app_factory.py`。
* `routes/` 只處理 HTTP request/response 與 status code；不要讓 route 直接承擔複雜資料處理。
* `services/` 放可測試的 business/application logic，例如 webhook payload normalization、persistence 與 screenshot file storage。
* `models.py` 放 SQLAlchemy models；任何 schema 變更都需要 Alembic migration。
* `templates/base.html` 提供共用 skeleton，Dashboard 內容在 `templates/dashboard.html` 與 `templates/partials/`。
* `routes/health.py`、`extensions.py`、`routes/__init__.py`、`services/__init__.py` 雖然偏薄，但目前可接受，不要只為了減少檔案數而合併。
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

1. 執行 `python -m alembic upgrade head` 初始化或升級資料庫。
2. 執行 `python run.py`。
3. 開啟 <http://127.0.0.1:222/health>，應回傳 `{"status":"ok"}`。
4. 用 README 的 `curl` 範例送出 Webhook。
5. 開啟 <http://127.0.0.1:222/>，應看得到新事件。
6. 若使用預設 `DATABASE_URL`，手動啟動可能會在專案根目錄建立 `bettergi.db`；手動驗證結束後請刪除，並在提交前確認 `test ! -e bettergi.db` 通過。

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

請確認 BetterGI Webhook URL 指向 `http://127.0.0.1:222/`，且用 `POST` 傳送 JSON。

也可以先使用 README 的 `curl` 範例確認服務是否正常。

### `/image/<int:image_id>` 回傳 Invalid image data

該筆舊版資料的 `screenshot` 欄位不是合法 Base64。請檢查 BetterGI 發出的 payload，或使用 `test.py` 捕捉原始請求。

## 已知技術債

* Webhook 已支援選填 token 與 HMAC-SHA256 signature 驗證；若公開到外網，仍建議搭配 HTTPS、反向代理、來源限制與 rate limit。
* 舊版資料庫中可能仍存在 Base64 screenshot 欄位；如需完全清理，可另做 migration / cleanup 工具。

## 後續建議重構方向

後續改動請維持小 PR、單一目的，不要把 security、migration、file storage 或大型 UI 調整混在同一個 PR。

1. 強化外網部署安全，例如 HTTPS、反向代理、來源 IP 限制、rate limit 與更完整的部署範例。
2. 若需要完全移除舊版 Base64 截圖欄位，另做 migration / cleanup 工具。
3. 增加更多 pytest 測試與端到端啟動測試。

## 已知相容性注意事項

* `POST /` 要求 `Content-Type: application/json`，且 body 必須是 JSON object。
* `event` 欄位為必填非空字串；缺少時會回傳 HTTP 400。
* 啟動器不會自動執行 `pip install`，避免在使用者不知情時修改全域 Python；請在虛擬環境內明確執行安裝指令。
* `create_app()` 仍保留 `db.create_all()` 作為輕量 fallback，但正式 schema 變更與升級應使用 Alembic migration。
