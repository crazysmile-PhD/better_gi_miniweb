# Better GI MiniWeb Architecture

## 專案目的

Better GI MiniWeb 是一個輕量級 Flask 應用，用來接收 BetterGI Webhook 事件，將事件資料寫入本機 SQLite，並透過簡單 Dashboard 顯示最近事件與 Base64 PNG 截圖。

目前的重構目標是逐步把原本集中在 `main.py`、`init_database.py`、`run.py` 的程式碼拆成可維護的 package 結構，同時保持既有 API 與舊入口相容。

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
4. Route 只做 HTTP 層驗證，例如選填的 Webhook token / HMAC signature，以及確認 request 是 JSON object。
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