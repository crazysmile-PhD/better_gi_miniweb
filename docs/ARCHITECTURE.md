# Better GI MiniWeb Architecture

## 專案目的

Better GI MiniWeb 是一個輕量級 Flask 應用，用來接收 BetterGI Webhook 事件，將事件資料寫入本機 SQLite，並透過簡單 Dashboard 顯示最近事件與 Base64 PNG 截圖。

目前的重構目標是逐步把原本集中在單一 `app.py` 的程式碼拆成可維護的 package 結構，同時保持既有 API 與舊入口相容。

本專案是小型 Flask 工具，不採用大型 enterprise architecture。重構目標是降低維護成本與修改風險，而不是把檔案拆得越細越好；目前 package 邊界已足夠，除非有明確需求，否則不要再新增抽象層。

## Over-splitting audit 結論

目前架構先維持現狀，不再繼續拆分：

* `app_factory.py` 只負責組裝 Flask app。
* `config.py` 只負責設定與環境變數。
* `extensions.py` 保留 `db` extension instance。
* `models.py` 保留 `PostData` schema。
* `routes/` 保留 HTTP request / response。
* `services/` 保留資料驗證、正規化與 DB 寫入。
* `app.py` / `main.py` 保留相容入口。

`routes/health.py`、`extensions.py`、`routes/__init__.py`、`services/__init__.py` 雖然偏薄，但目前可接受：它們有清楚 package / endpoint / extension 邊界，不要只為了減少檔案數而合併。

只有在兩個檔案同時符合以下條件時，才允許合併：

1. 永遠一起修改。
2. 沒有不同依賴。
3. 沒有不同測試需求。
4. 合併後責任仍清楚。
5. 合併不會破壞 public API 或測試。

除非有明確需求，否則不要新增：

* `repositories/`
* `domain/`
* `use_cases/`
* `interfaces/`
* `adapters/`
* `schemas/`
* `dto/`
* `managers/`
* generic helpers
* plugin system
* API versioning

## Request flow

### Webhook 寫入流程：`POST /`

1. Flask app 由 `bettergi_miniweb.app_factory.create_app()` 建立。
2. `create_app()` 初始化 config、logging、SQLAlchemy，並註冊 blueprints。
3. `bettergi_miniweb.routes.webhook.webhook()` 接收 `POST /`。
4. Route 只做 HTTP 層驗證，例如確認 request 是 JSON object。
5. Route 呼叫 `bettergi_miniweb.services.webhook_service.save_webhook_payload()`。
6. Service 執行 payload normalization 與必要欄位驗證。
7. Service 建立 `PostData` model 並透過 shared `db.session` 寫入 SQLite。
8. Route 回傳 `201` 與 `{ "msg": "OK", "id": ... }`。

### Dashboard 讀取流程：`GET /`

1. `bettergi_miniweb.routes.dashboard.page()` 查詢最近 10 筆 `PostData`。
2. Route 將資料傳給 `templates/base.html`。
3. Template 負責渲染 Dashboard；目前沒有 frontend build pipeline。

### 圖片讀取流程：`GET /image/<int:image_id>`

1. `bettergi_miniweb.routes.image.serve_image()` 用 `image_id` 查詢 `PostData`。
2. 若該筆資料不存在或沒有 screenshot，回傳 `404`。
3. 若 screenshot 不是合法 Base64，回傳 `422`。
4. 若合法，將 Base64 decode 成 binary 並以 `image/png` 回傳。

## Public API routes

目前必須保持相容的 public routes：

| Method | Route | 說明 |
| --- | --- | --- |
| `POST` | `/` | 接收 BetterGI Webhook JSON payload。 |
| `GET` | `/` | 顯示 Dashboard。 |
| `GET` | `/health` | 健康檢查，回傳 `{ "status": "ok" }`。 |
| `GET` | `/image/<int:image_id>` | 讀取指定事件的 Base64 PNG 截圖。 |

## 目錄結構說明

```text
better_gi_miniweb/
├── app.py                         # WSGI / Flask CLI / python app.py 相容入口
├── main.py                        # 舊版 from main import app 相容層
├── run.py                         # gevent 啟動器
├── init_database.py               # SQLite 初始化與 post_load 匯入工具
├── bettergi_miniweb/
│   ├── __init__.py                # package public exports
│   ├── app_factory.py             # create_app、logging、blueprint registration
│   ├── config.py                  # 環境變數與基本 Flask config mapping
│   ├── extensions.py              # Flask extension instances
│   ├── models.py                  # SQLAlchemy models
│   ├── routes/                    # HTTP route blueprints
│   │   ├── dashboard.py           # GET /
│   │   ├── health.py              # GET /health
│   │   ├── image.py               # GET /image/<int:image_id>
│   │   └── webhook.py             # POST /
│   └── services/                  # 可測試的 business/application logic
│       └── webhook_service.py     # Webhook payload validation and persistence
├── docs/
│   └── ARCHITECTURE.md            # 開發者架構說明
├── static/                        # Dashboard static assets
├── templates/                     # Jinja2 templates
└── tests/                         # pytest test suite
```

## 模組責任邊界

### `app.py`

* 保留 top-level `app = create_app()`，供 gunicorn、gevent、`flask run` 或舊部署方式使用。
* 保留 `python app.py` 啟動方式。
* 只做相容匯出，不放 route、model 或 service logic。

### `main.py`

* 舊入口相容層。
* 保留 `from main import app`、`Post_data`、`save_data` 等歷史名稱。
* 除非確認沒有舊入口依賴，否則不要刪除。

### `bettergi_miniweb/app_factory.py`

* 建立 Flask app。
* 載入 config mapping。
* 初始化 logging 與 extensions。
* 註冊 blueprints。
* 不放 business logic、不直接處理 webhook payload、不定義 models。不要把 service 或 route 的邏輯塞回 `app_factory.py`。

### `bettergi_miniweb/config.py`

* 集中管理環境變數讀取與預設值。
* 提供 `BASE_DIR`、`DEFAULT_DATABASE_URI`、`DEFAULT_PORT`、`get_log_level()`、`get_port()`、`get_app_config()`。
* `create_app()` 需要的基本 config mapping 應由這裡提供。

### `bettergi_miniweb/extensions.py`

* 放 Flask extension instances，例如 `db = SQLAlchemy()`。
* 不 import app factory，避免 circular import。

### `bettergi_miniweb/models.py`

* 放 SQLAlchemy models。
* 目前 `PostData` schema 與既有 SQLite table 相容。
* 修改欄位前必須先說明 migration 策略。

### `bettergi_miniweb/routes/*.py`

* 每個檔案負責一組 HTTP endpoints，並透過 Blueprint 匯出。
* Route 只處理 HTTP request/response、status code 與呼叫 service。
* 複雜資料處理應移到 service layer，不要讓 route 直接承擔複雜資料處理。

### `bettergi_miniweb/services/*.py`

* 放可測試的 business/application logic。
* 目前 `webhook_service.py` 負責 Webhook payload normalization 與 persistence。
* Service 可以使用 models 與 extensions，但不應依賴 Flask request object。

### `tests/test_app.py`

* 覆蓋 public API routes、錯誤路徑、圖片端點與相容入口。
* 使用 temporary SQLite database。
* 測試前後不可留下專案根目錄 `bettergi.db`。

## 新增 route 的步驟

1. 在 `bettergi_miniweb/routes/` 新增或更新對應 route module。
2. 使用 `Blueprint` 定義 endpoint，保持 route function 聚焦於 HTTP 層。
3. 若需要 business logic，新增或呼叫 `bettergi_miniweb/services/` 中的 service。
4. 在 `bettergi_miniweb/routes/__init__.py` 匯出新的 blueprint。
5. 在 `bettergi_miniweb/app_factory.py` 的 `create_app()` 註冊 blueprint。
6. 在 `tests/test_app.py` 補上 route method 與行為測試。
7. 確認 public route URL 與 method 是否影響相容性。

## 新增 service 的步驟

1. 在 `bettergi_miniweb/services/` 建立清楚命名的 module。
2. 將可測試的資料處理、驗證或 persistence logic 放進 service。
3. 避免在 service 裡讀取 Flask `request`，改由 route 傳入普通 Python 資料。
4. Route 只呼叫 service 並轉換 service 結果為 HTTP response。
5. 補上 service 相關的 route 或單元測試。

## 修改 model 的注意事項

* `PostData` 對應既有 SQLite table，修改欄位可能造成資料不相容。
* 不要直接修改 SQLite schema 而不寫清楚遷移策略。
* 在導入 migration 前，任何 schema 變更都應獨立成小 PR，並明確標記破壞性影響。
* 不要把圖片儲存方式變更與 schema 變更混在一般 route/service refactor 裡。

## 修改 config 的注意事項

* 環境變數讀取應集中在 `bettergi_miniweb/config.py`。
* `create_app(test_config=...)` 必須持續支援測試覆蓋設定。
* `PORT` 預設仍是 `222`，`app.py` 的 host 暫時仍是 `0.0.0.0`。
* 修改 config 時應補測試，避免測試建立專案根目錄 `bettergi.db`。

## 測試規則

每個 PR 至少執行：

```bash
ruff check .
pytest
git diff --check
test ! -e bettergi.db
```

測試應遵守：

* 使用 pytest fixtures。
* 使用 temporary SQLite database。
* 不污染專案根目錄 `bettergi.db`。
* 覆蓋 public API route method list：`POST /`、`GET /`、`GET /health`、`GET /image/<int:image_id>`。

## PR checklist

送出 PR 前確認：

- [ ] 變更範圍單一，不混合不相關重構。
- [ ] Public API routes 沒有意外改變。
- [ ] `app.py` 相容入口仍可 import `app`、`create_app`、`db`、`PostData`、`normalize_webhook_payload`、`save_webhook_payload`。
- [ ] `main.py` 相容層未被刪除。
- [ ] 若修改 config，測試仍使用 temporary SQLite。
- [ ] 若修改 model，PR 說明包含 migration / 相容策略。
- [ ] 已執行 `ruff check .`、`pytest`、`git diff --check`。
- [ ] 已確認 `test ! -e bettergi.db` 通過。

## 禁止事項

* 不要只因為檔案偏薄就合併 `routes/health.py`、`extensions.py`、`routes/__init__.py` 或 `services/__init__.py`。
* 不要新增 `repositories/`、`domain/`、`use_cases/`、`interfaces/`、`adapters/`、`schemas/`、`dto/`、`managers/` 或 generic helpers。
* 不要把 business logic 塞回 `app_factory.py`。
* 不要在 route 裡直接做複雜資料處理。
* 不要繞過 service layer。
* 不要直接修改 SQLite schema 而不寫清楚遷移策略。
* 不要讓測試污染專案根目錄 `bettergi.db`。
* 不要跳過 `ruff check .`、`pytest`、`git diff --check`。
* 不要把 security / migration / file storage refactor 混在同一個 PR。
* 不要在未確認舊入口依賴前刪除 `main.py`。
