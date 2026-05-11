# Better GI MiniWeb Architecture

本文件說明 Better GI MiniWeb 的 request flow、screenshot storage flow、migration policy、Dashboard query / pagination flow、template structure 與維護規則。

## 高層架構

```text
BetterGI
  │ POST /
  ▼
bettergi_miniweb/routes/webhook.py
  │ validate JSON / optional token / optional HMAC signature
  ▼
bettergi_miniweb/services/webhook_service.py
  │ normalize payload
  │ decode and persist screenshot files when present
  ▼
bettergi_miniweb/models.py + SQLite
  │ event metadata + screenshot_path / legacy screenshot
  ▼
GET / dashboard and GET /image/<id>
```

## 檔案結構

```text
better_gi_miniweb/
├── alembic.ini
├── app.py
├── bettergi_miniweb/
│   ├── app_factory.py              # create_app、config loading、extension setup、blueprint registration
│   ├── config.py                   # DATABASE_URL、LOG_LEVEL、PORT、WEBHOOK_*、SCREENSHOT_STORAGE_DIR
│   ├── extensions.py               # db = SQLAlchemy()
│   ├── models.py                   # PostData model
│   ├── routes/
│   │   ├── dashboard.py            # GET / with query, pagination, filters, refresh
│   │   ├── health.py               # GET /health
│   │   ├── image.py                # GET /image/<int:image_id>
│   │   └── webhook.py              # POST /
│   └── services/
│       └── webhook_service.py      # payload normalization, screenshot path safety, persistence
├── migrations/
│   ├── env.py                      # Alembic environment using Flask config without create_all fallback
│   └── versions/                   # schema revisions
├── static/                         # Dashboard static assets
├── templates/
│   ├── base.html                   # shared skeleton
│   ├── dashboard.html              # Dashboard page
│   └── partials/
│       ├── event_card.html
│       ├── filter_form.html
│       └── pagination.html
└── tests/                          # pytest test suite
```

## Request flow

### `POST /` webhook flow

1. `bettergi_miniweb/routes/webhook.py` reads the raw request body.
2. If `WEBHOOK_TOKEN` is configured, the route accepts either `Authorization: Bearer <token>` or `X-Webhook-Token`.
3. If `WEBHOOK_SIGNATURE_SECRET` is configured, the route verifies `X-Webhook-Signature: sha256=<hex digest>` against the raw body.
4. The route rejects non-JSON requests and JSON values that are not objects.
5. The route calls `save_webhook_payload(payload)`.
6. `bettergi_miniweb/services/webhook_service.py` validates that `event` is a non-empty string, normalizes optional fields, persists metadata, and stores valid screenshots as files.
7. On success, the route returns HTTP 201 with the saved row id.

### `GET /` dashboard flow

1. `bettergi_miniweb/routes/dashboard.py` parses query parameters.
2. The route builds a SQLAlchemy `select(PostData)` statement.
3. Optional filters are applied for search, `result`, and create-time date range.
4. A count query computes total rows.
5. The data query orders by `PostData.create_time.desc()`, applies `limit` and `offset`, and renders `templates/dashboard.html`.
6. `templates/dashboard.html` uses partials for the filter form, event cards, and pagination links.

### `GET /image/<int:image_id>` image flow

1. `bettergi_miniweb/routes/image.py` loads `PostData` by id.
2. If `screenshot_path` is present and resolves safely inside `SCREENSHOT_STORAGE_DIR`, the route serves that file.
3. If `screenshot_path` is present but unsafe, the route returns HTTP 404 immediately and does not fallback to legacy Base64.
4. If no file-backed screenshot path exists, the route falls back to the legacy Base64 `screenshot` column.
5. Missing images return HTTP 404.
6. Invalid legacy Base64 returns HTTP 422.

## Screenshot storage flow

New screenshot storage is file-backed:

```text
Webhook payload screenshot (Base64)
  │
  ▼
base64.b64decode(..., validate=True)
  │
  ▼
SCREENSHOT_STORAGE_DIR/post_<id>.png
  │
  ▼
post_data.screenshot_path = "post_<id>.png"
post_data.screenshot = NULL
```

Rules:

* `SCREENSHOT_STORAGE_DIR` defaults to `instance/screenshots/` and may be overridden by environment variable or test config.
* New valid screenshots are decoded and written to files; SQLite only stores the safe relative path.
* The legacy `screenshot` column remains for backward compatibility with existing SQLite databases.
* `/image/<id>` always prefers `screenshot_path` and only falls back to `screenshot` when no file-backed path exists.
* Screenshot paths are resolved under the configured storage root; unsafe paths that would escape the root are rejected with 404 and do not fallback to legacy Base64.
* If DB commit fails after writing a screenshot file, the service rolls back and deletes the file written for that request to avoid orphan screenshot files.
* Runtime screenshot files are ignored by git and must not be committed.

## Migration policy

Alembic is the source of truth for schema changes.

Current revisions:

* `202605110001_baseline_post_data.py` creates the baseline `post_data` table.
* `202605110002_add_screenshot_path.py` adds `post_data.screenshot_path` for file-backed screenshots.

Operational commands for a new empty database:

```bash
python -m alembic upgrade head
```

Operational commands for an existing pre-Alembic database that already has the baseline `post_data` table:

```bash
python -m alembic stamp 202605110001
python -m alembic upgrade head
```

When targeting a non-default database, use the same `DATABASE_URL` for both commands:

```bash
DATABASE_URL=sqlite:////path/to/bettergi.db python -m alembic stamp 202605110001
DATABASE_URL=sqlite:////path/to/bettergi.db python -m alembic upgrade head
```

Policy for future model changes:

1. Update `bettergi_miniweb/models.py`.
2. Add a new Alembic revision under `migrations/versions/`.
3. Verify the revision on an empty temporary database and, when relevant, on a copy of an existing database.
4. Keep `db.create_all()` only as a lightweight fallback for empty local SQLite startup; do not rely on it for formal schema upgrades.
5. Document migration behavior in README and this architecture document.

`migrations/env.py` creates the Flask app with `SKIP_CREATE_ALL=True` so Alembic can migrate an empty database without `create_app()` pre-creating tables.

## Dashboard query / pagination flow

Supported query parameters:

| Parameter | Behavior |
| --- | --- |
| `page` | 1-based page number; invalid values fall back to page 1 |
| `per_page` | rows per page; invalid values fall back to 10 and values are capped at 100 |
| `q` | case-insensitive search across `event`, `message`, and `result` |
| `result` | exact result filter |
| `date_from` | inclusive lower bound on `create_time`, format `YYYY-MM-DD` |
| `date_to` | inclusive upper bound on `create_time`, format `YYYY-MM-DD` |
| `refresh` | meta-refresh interval in seconds; `0` disables auto refresh |

Flow details:

1. Query parsing is intentionally local to `routes/dashboard.py`; no extra repository or manager layer is introduced.
2. Date parse errors are collected and shown in the template, while the invalid date filter is ignored.
3. The route clamps `page` to available pages so empty out-of-range pages do not break rendering.
4. Pagination links preserve current query parameters.
5. Dashboard HTML responses set `Cache-Control: no-store, max-age=0`; health responses do not receive a one-day public cache header.

## Template structure

The frontend remains lightweight Flask + Jinja2 with no Node, React, Vue, bundler, or frontend build step.

* `templates/base.html` contains the document skeleton, shared stylesheet include, header, and `{% block %}` placeholders.
* `templates/dashboard.html` extends `base.html`, adds optional meta refresh, and composes the dashboard page.
* `templates/partials/filter_form.html` renders search/filter/refresh controls.
* `templates/partials/event_card.html` renders one persisted BetterGI event.
* `templates/partials/pagination.html` renders previous/next pagination links.

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
* 保留 `db.create_all()` 作為輕量 fallback，但不得把正式 migration 邏輯塞進 app factory。
* 不放 business logic、不直接處理 webhook payload、不定義 models。

### `bettergi_miniweb/config.py`

* 集中管理環境變數讀取與預設值。
* 提供 `BASE_DIR`、`DEFAULT_DATABASE_URI`、`DEFAULT_PORT`、`DEFAULT_SCREENSHOT_STORAGE_DIR`、`get_log_level()`、`get_port()`、`get_app_config()`。
* `create_app(test_config=...)` 必須持續支援測試覆蓋設定。

### `bettergi_miniweb/extensions.py`

* 放 Flask extension instances，例如 `db = SQLAlchemy()`。
* 不 import app factory，避免 circular import。

### `bettergi_miniweb/models.py`

* 放 SQLAlchemy models。
* `PostData` schema 由 Alembic migrations 管理。
* `screenshot` 保留作為舊版 Base64 相容欄位；`screenshot_path` 是新版檔案儲存路徑欄位。

### `bettergi_miniweb/routes/*.py`

* 每個檔案負責一組 HTTP endpoints，並透過 Blueprint 匯出。
* Route 只處理 HTTP request/response、status code 與呼叫 service。
* 複雜資料處理應移到 service layer，不要讓 route 直接承擔複雜資料處理。

### `bettergi_miniweb/services/*.py`

* 放可測試的 business/application logic。
* `webhook_service.py` 負責 Webhook payload normalization、persistence、screenshot file storage 與安全路徑解析。
* Service 可以使用 models、extensions 與 Flask app config，但不應依賴 Flask request object。

### `tests/test_app.py`

* 覆蓋 public API routes、錯誤路徑、圖片端點、Dashboard query behavior、Alembic migration 與相容入口。
* 使用 temporary SQLite database 與 temporary screenshot storage。
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
* 所有 schema 變更都要新增 Alembic migration。
* `db.create_all()` 只作為輕量 fallback，不是 schema migration 工具。
* 不要把圖片儲存方式變更與不相關 route/service refactor 混在一起。

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
* 使用 temporary screenshot storage。
* 不污染專案根目錄 `bettergi.db`。
* 覆蓋 public API route method list：`POST /`、`GET /`、`GET /health`、`GET /image/<int:image_id>`。

## PR checklist

送出 PR 前確認：

- [ ] 變更範圍單一，不混合不相關重構。
- [ ] Public API routes 沒有意外改變。
- [ ] `app.py` 相容入口仍可 import `app`、`create_app`、`db`、`PostData`、`normalize_webhook_payload`、`save_webhook_payload`。
- [ ] `main.py` 相容層未被刪除。
- [ ] 若修改 config，測試仍使用 temporary SQLite 與 temporary screenshot storage。
- [ ] 若修改 model，PR 說明包含 Alembic migration / 相容策略。
- [ ] 已執行 `ruff check .`、`pytest`、`git diff --check`。
- [ ] 已確認 `test ! -e bettergi.db` 通過。

## 禁止事項

* 不要只因為檔案偏薄就合併 `routes/health.py`、`extensions.py`、`routes/__init__.py` 或 `services/__init__.py`。
* 不要新增 `repositories/`、`domain/`、`use_cases/`、`interfaces/`、`adapters/`、`schemas/`、`dto/`、`managers/` 或 generic helpers。
* 不要把 business logic 塞回 `app_factory.py`。
* 不要在 route 裡直接做複雜資料處理。
* 不要繞過 service layer。
* 不要直接修改 SQLite schema 而不新增 Alembic migration。
* 不要讓測試污染專案根目錄 `bettergi.db`。
* 不要提交 runtime/cache/db/screenshot artifacts。
* 不要跳過 `ruff check .`、`pytest`、`git diff --check`。
* 不要把 security / migration / file storage refactor 混在同一個 PR。
* 不要在未確認舊入口依賴前刪除 `main.py`。
