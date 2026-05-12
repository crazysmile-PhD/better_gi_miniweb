# Manual Verification Record

Date: 2026-05-11 (UTC)
Scope: PR #15 remains Draft. This record only captures manual merge-readiness checks requested after the automated test coverage was added.

## Results

| Area | Command / method | Result |
| --- | --- | --- |
| Empty DB migration | Temporary `DATABASE_URL` + `python -m alembic upgrade head` | Passed. `post_data` contains `id,event,result,timestamp,screenshot,create_time,message,screenshot_path`; `alembic_version` is `202605110002`. |
| Existing pre-Alembic DB migration | Created a temporary legacy `post_data` table, then ran `python -m alembic stamp 202605110001` and `python -m alembic upgrade head` | Passed. `screenshot_path` was added and `alembic_version` became `202605110002`. |
| New file-backed screenshot | Flask test client `POST /` with valid Base64 screenshot, then `GET /image/<id>` | Passed. Image returned HTTP 200 with `image/png`, and the decoded screenshot file existed under the configured screenshot directory. |
| Legacy Base64 screenshot fallback | Inserted a row with only legacy `screenshot` Base64, then `GET /image/<id>` | Passed. Image returned HTTP 200 with `image/png`. |
| Unsafe screenshot path | Inserted a row with `screenshot_path="../secret.png"`, then `GET /image/<id>` | Passed. Endpoint returned HTTP 404 and did not fallback to legacy Base64. |
| Invalid Base64 screenshot | Inserted a row with `screenshot="not base64"`, then `GET /image/<id>` | Passed. Endpoint returned HTTP 422. |
| Dashboard query / pagination / refresh | Flask test client `GET /?q=manual-message&result=success&page=2&per_page=3&refresh=15` | Passed. Dashboard returned HTTP 200, `Cache-Control: no-store, max-age=0`, rendered page `第 2 / 2 頁`, and included `<meta http-equiv="refresh" content="15">`. |

## Commands Used

### Empty DB migration

```bash
tmpdir=$(mktemp -d)
DATABASE_URL="sqlite:///$tmpdir/empty.db" SCREENSHOT_STORAGE_DIR="$tmpdir/screenshots" python -m alembic upgrade head
python - <<'PY' "$tmpdir/empty.db"
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as con:
    cols = [row[1] for row in con.execute('pragma table_info(post_data)')]
    version = con.execute('select version_num from alembic_version').fetchone()[0]
print('empty_db_columns=' + ','.join(cols))
print('empty_db_version=' + version)
PY
rm -rf "$tmpdir"
```

Observed output:

```text
empty_db_columns=id,event,result,timestamp,screenshot,create_time,message,screenshot_path
empty_db_version=202605110002
```

### Existing pre-Alembic DB migration

```bash
tmpdir=$(mktemp -d)
python - <<'PY' "$tmpdir/existing.db"
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as con:
    con.execute(
        'create table post_data ('
        'id integer primary key autoincrement, '
        'event text not null, '
        'result text, '
        'timestamp text, '
        'screenshot text, '
        'create_time datetime not null, '
        'message text)'
    )
print('created_pre_alembic_db')
PY
DATABASE_URL="sqlite:///$tmpdir/existing.db" SCREENSHOT_STORAGE_DIR="$tmpdir/screenshots" python -m alembic stamp 202605110001
DATABASE_URL="sqlite:///$tmpdir/existing.db" SCREENSHOT_STORAGE_DIR="$tmpdir/screenshots" python -m alembic upgrade head
python - <<'PY' "$tmpdir/existing.db"
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as con:
    cols = [row[1] for row in con.execute('pragma table_info(post_data)')]
    version = con.execute('select version_num from alembic_version').fetchone()[0]
print('existing_db_columns=' + ','.join(cols))
print('existing_db_version=' + version)
PY
rm -rf "$tmpdir"
```

Observed output:

```text
existing_db_columns=id,event,result,timestamp,screenshot,create_time,message,screenshot_path
existing_db_version=202605110002
```

### Endpoint and Dashboard checks

A temporary Flask app was created with a temporary SQLite database and temporary `SCREENSHOT_STORAGE_DIR`. The script exercised:

* `POST /` with a valid screenshot followed by `GET /image/<id>`.
* Legacy Base64-only row followed by `GET /image/<id>`.
* Unsafe `screenshot_path` row followed by `GET /image/<id>`.
* Invalid Base64 row followed by `GET /image/<id>`.
* Dashboard request `GET /?q=manual-message&result=success&page=2&per_page=3&refresh=15`.

Observed output:

```text
new_file_backed_status=200
new_file_backed_mimetype=image/png
new_file_exists=True
legacy_base64_status=200
legacy_base64_mimetype=image/png
unsafe_screenshot_path_status=404
invalid_base64_status=422
dashboard_status=200
dashboard_cache_control=no-store, max-age=0
dashboard_has_page_2=True
dashboard_has_refresh_meta=True
```
