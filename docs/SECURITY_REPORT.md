# Security Audit Report — BTS Shuttle Booking RC1

**Date:** 2026-06-09
**Auditor:** RC1 Pre-launch Audit
**Scope:** Full codebase static analysis

---

## 摘要

| 等級 | 數量 |
|------|------|
| 🔴 Critical | 2 |
| 🟠 High | 3 |
| 🟡 Medium | 4 |
| 🟢 Low | 2 |

---

## 🔴 Critical

### C1 — 管理員密碼明文儲存

**位置：** `app/models/admin.py:7`, `app/routes/auth.py:19`

**問題：**
`Admin.password_hash` 欄位命名暗示 hash，但實際儲存**明文密碼**。登入時直接比對：
```python
admin = Admin.query.filter_by(username=username, password_hash=password).first()
```
資料庫一旦外洩，所有管理員帳號立即淪陷。

**影響：** 資料庫外洩 → 帳號全部失守

**修復建議（上線前必須）：**
```python
# requirements.txt 加入
werkzeug  # Flask 已含此依賴，直接使用

# auth.py 改為
from werkzeug.security import generate_password_hash, check_password_hash
# 存入時 hash：generate_password_hash(password)
# 驗證時：check_password_hash(admin.password_hash, password)
```

---

### C2 — 所有 POST 表單缺少 CSRF 保護

**位置：** 全站所有 `<form method="post">` 表單

**問題：**
無 Flask-WTF CSRF token，任何已登入管理員點擊惡意連結可觸發狀態變更（刪除訂單、刪除管理員、觸發通知等）。

**影響：** CSRF 攻擊可任意操控後台資料

**修復建議（上線前必須）：**
```python
# requirements.txt 加入
Flask-WTF==1.2.1

# __init__.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()
csrf.init_app(app)

# 所有表單加入
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

---

## 🟠 High

### H1 — SECRET_KEY 未設定時 Flask Session 失效

**位置：** `app/__init__.py:23`

```python
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")  # 可能回傳 None
```

**問題：** SECRET_KEY 為 None 時，Flask session cookie 無法正確簽章，管理員無法登入，且可能暴露 session 偽造風險。

**修復建議：**
```python
secret = os.getenv("SECRET_KEY")
if not secret:
    raise RuntimeError("SECRET_KEY environment variable is not set")
app.config["SECRET_KEY"] = secret
```

---

### H2 — 預約日期後端未驗證

**位置：** `app/routes/passenger.py:81` — `booking_submit()`

**問題：**
`departure_date` 僅在前端 `<select>` 限制，後端未驗證是否在 `DEPARTURE_OPTIONS` 白名單內。攻擊者可 POST 任意字串作為日期。

```python
# 目前無驗證，以下為修復
VALID_DATES = {"11/19(四)", "11/21(六)", "11/22(日)"}
if form_data["departure_date"] not in VALID_DATES:
    flash("請選擇有效的出發日期。", "error")
    return redirect(...)
```

---

### H3 — `requests` 套件未列入 requirements.txt

**位置：** `app/services/line_service.py:4`, `requirements.txt`

**問題：**
`line_service.py` 使用 `import requests`，但 `requirements.txt` 未列入此依賴。Zeabur 部署可能因 `requests` 未安裝而在 LINE 通知時崩潰（`requests` 通常跟隨其他套件附帶安裝，但不可靠）。

**修復建議：**
```
# requirements.txt 加入
requests==2.32.3
```

---

## 🟡 Medium

### M1 — 乘客人數後端無上限驗證

**位置：** `app/routes/passenger.py:89`

**問題：**
前端 `<input type="number" min="1" max="50">`，但後端只做 `int()` 轉換，未驗證 `1 <= passenger_count <= 8`（排車上限）。使用者可直接 POST `passenger_count=999` 製造無效訂單。

---

### M2 — Driver is_line_bound 與 bind_status 不同步

**位置：** `app/routes/admin.py:448-464` — `driver_edit()`

**問題：**
管理員手動修改司機 `bind_status` 為「已綁定」或「未綁定」時，`is_line_bound` 欄位不更新，導致系統內部狀態不一致。

---

### M3 — LINE 通知 Token 在 module 載入時讀取

**位置：** `app/services/line_service.py:14-15`

```python
PASSENGER_TOKEN = os.environ.get("PASSENGER_LINE_CHANNEL_ACCESS_TOKEN", "")
DRIVER_TOKEN    = os.environ.get("DRIVER_LINE_CHANNEL_ACCESS_TOKEN", "")
```

**問題：**
Token 在 Python module 首次 import 時讀取，若環境變數後來才設定（Zeabur 重新部署但未重啟），token 仍為空字串。應在函式內部讀取或使用 `app.config`。

---

### M4 — Session 無過期設定

**位置：** `app/__init__.py`, `app/routes/auth.py`

**問題：**
管理員登入 session 永不過期（browser close 才失效）。長時間未操作的 session 若遭竊用，攻擊者可無限期存取後台。

**建議：**
```python
from datetime import timedelta
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
# auth.py login 成功後
session.permanent = True
```

---

## 🟢 Low

### L1 — 缺少 .env.example

**問題：** 新部署者無法知道需要哪些環境變數。應建立 `.env.example` 供參考（見 DEPLOY_CHECKLIST.md）。

### L2 — 後台無速率限制

**問題：** `/admin/login` POST 無暴力破解防護。在密碼為明文的情況下（C1），影響尤為嚴重。建議 C1 修復後，加入 Flask-Limiter。

---

## XSS 確認安全 ✓

Jinja2 預設開啟 autoescape，全站模板無 `| safe` 使用，XSS 風險低。

## SQL Injection 確認安全 ✓

所有資料庫查詢均透過 SQLAlchemy ORM parameterized query，無 raw SQL 拼接。

## 環境變數洩漏確認安全 ✓

`.gitignore` 正確排除 `.env` 及 `.env.*`，GitHub 倉庫無敏感資訊。

---

## 修復優先順序

| 優先 | 項目 | 上線前必須 |
|------|------|-----------|
| 1 | C1 密碼 hash | ✅ 必須 |
| 2 | C2 CSRF 保護 | ✅ 必須 |
| 3 | H1 SECRET_KEY 檢查 | ✅ 必須 |
| 4 | H2 日期驗證 | ✅ 必須 |
| 5 | H3 requests 依賴 | ✅ 必須 |
| 6 | M1 人數驗證 | 建議 |
| 7 | M2 Driver 狀態同步 | 建議 |
| 8 | M3 Token 讀取時機 | 建議 |
| 9 | M4 Session 過期 | 建議 |
| 10 | L1 .env.example | 低 |
| 11 | L2 速率限制 | 低 |
