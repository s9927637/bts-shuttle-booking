# Deployment Checklist — BTS Shuttle Booking RC1

**Date:** 2026-06-09
**Platform:** Zeabur (GitHub Auto-deploy from `main`)

---

## 上線阻擋清單（必須完成才能上線）

### 🔴 BLOCKER-01：密碼 Hash（Critical）

- [ ] 安裝 `werkzeug`（或確認 Flask 依賴已含）
- [ ] `Admin.password_hash` 改為儲存 `generate_password_hash()` 結果
- [ ] `auth.py` 登入改為 `check_password_hash()`
- [ ] 更新所有現有管理員密碼為 hash 值
- [ ] 測試登入正常

### 🔴 BLOCKER-02：CSRF 保護（Critical）

- [ ] `requirements.txt` 加入 `Flask-WTF==1.2.1`
- [ ] `__init__.py` 初始化 `CSRFProtect`
- [ ] 所有後台表單加入 `{{ csrf_token() }}`
- [ ] 測試表單仍可正常提交

### 🟠 BLOCKER-03：requests 依賴（High）

- [ ] `requirements.txt` 加入 `requests==2.32.3`
- [ ] Zeabur 重新部署後確認 LINE 通知功能正常

---

## 環境變數設定（Zeabur Dashboard）

| 變數名稱 | 必填 | 說明 |
|---------|------|------|
| `DATABASE_URL` | ✅ | PostgreSQL 連接字串 |
| `SECRET_KEY` | ✅ | 隨機 32 字元以上字串，用於 session 簽章 |
| `PASSENGER_LINE_CHANNEL_ACCESS_TOKEN` | ✅ | 乘客 LINE OA Channel Access Token |
| `DRIVER_LINE_CHANNEL_ACCESS_TOKEN` | ✅ | 司機 LINE OA Channel Access Token |
| `PASSENGER_LIFF_ID` | ✅ | 乘客 LIFF ID（e.g. `2xxxxxxx-xxxxxxxx`） |
| `DRIVER_LIFF_ID` | ✅ | 司機 LIFF ID（e.g. `2xxxxxxx-xxxxxxxx`） |

**驗證方法：**
```bash
# Zeabur Console
echo $SECRET_KEY   # 應顯示非空值
echo $DATABASE_URL # 應顯示 postgres:// 開頭
```

---

## .env.example（本機開發用）

```bash
# 資料庫
DATABASE_URL=postgresql://user:password@localhost:5432/bts_shuttle

# Flask
SECRET_KEY=your-random-secret-key-here-at-least-32-chars

# LINE Messaging API — 乘客 OA
PASSENGER_LINE_CHANNEL_ACCESS_TOKEN=

# LINE Messaging API — 司機 OA
DRIVER_LINE_CHANNEL_ACCESS_TOKEN=

# LINE LIFF
PASSENGER_LIFF_ID=
DRIVER_LIFF_ID=
```

---

## 部署前確認清單

### 程式碼

- [ ] `main` 分支為最新版本
- [ ] 所有 migration 檔案已提交
- [ ] `requirements.txt` 包含所有依賴（含 `requests`）
- [ ] `Procfile` 或 `zbpack.json` 設定正確：`gunicorn run:app`
- [ ] `run.py` 中 `debug=True` 在 Production 不會啟動（gunicorn 不受此影響）

### 資料庫

- [ ] Zeabur PostgreSQL 服務已建立
- [ ] `DATABASE_URL` 環境變數已設定
- [ ] 部署後執行 `flask db upgrade`（Zeabur Console）
- [ ] 確認所有 migration 正常執行完畢

```bash
# Zeabur Console 執行
flask db upgrade
flask db current  # 應顯示最新版本
```

### 初始資料

- [ ] 建立至少一個管理員帳號
```python
# Zeabur Console Python shell
from app import create_app, db
from app.models.admin import Admin
from werkzeug.security import generate_password_hash  # 修復 C1 後
app = create_app()
with app.app_context():
    a = Admin(username="admin", password_hash=generate_password_hash("your_password"))
    db.session.add(a)
    db.session.commit()
```

- [ ] 建立車輛資料（/admin/vehicles）
- [ ] 建立司機資料（/admin/drivers）

---

## LINE 設定確認

### 乘客 LINE OA
- [ ] LINE Developers Console → LIFF App 建立完成
- [ ] LIFF URL 設定為：`https://bts-shuttle-booking.anjiatra.com/booking`（預約）
- [ ] LIFF URL 設定為：`https://bts-shuttle-booking.anjiatra.com/orders/search`（查詢）
- [ ] LIFF URL 設定為：`https://bts-shuttle-booking.anjiatra.com/payment/report`（匯款）
- [ ] `PASSENGER_LIFF_ID` 填入 Zeabur 環境變數
- [ ] `PASSENGER_LINE_CHANNEL_ACCESS_TOKEN` 填入 Zeabur 環境變數
- [ ] 測試：透過 LINE App 開啟 LIFF，確認 userId 正確取得

### 司機 LINE OA
- [ ] LINE Developers Console → LIFF App 建立完成
- [ ] LIFF URL 設定為：`https://bts-shuttle-booking.anjiatra.com/driver/bind`
- [ ] `DRIVER_LIFF_ID` 填入 Zeabur 環境變數
- [ ] `DRIVER_LINE_CHANNEL_ACCESS_TOKEN` 填入 Zeabur 環境變數
- [ ] 測試：司機透過 LINE App 開啟，完成綁定

---

## 部署後煙霧測試（Smoke Test）

### 必測項目

| 測試 | URL | 預期 |
|------|-----|------|
| 首頁 | `/` | 200 正常顯示 |
| 預約頁 | `/booking` | 200 顯示表單 |
| 訂單查詢 | `/orders/search` | 200 顯示查詢頁 |
| 後台登入 | `/admin/login` | 200 顯示登入頁 |
| 後台登入（POST）| `/admin/login` | 成功跳轉 Dashboard |
| Dashboard | `/admin/` | 200 顯示統計數字 |
| 訂單管理 | `/admin/orders` | 200 |
| 排車管理 | `/admin/dispatch` | 200 |
| 司機綁定頁 | `/driver/bind` | 200 |

### 功能測試

- [ ] 完成一筆預約（從預約到 payment_report）
- [ ] 後台確認訂金（payment_status → 訂金已確認）
- [ ] 建立 Dispatch 並指派訂單
- [ ] 點擊「通知乘客」確認收到 LINE 訊息
- [ ] Dashboard 通知成功數更新

---

## Gunicorn 設定

```
# Procfile
web: gunicorn run:app

# zbpack.json
{"build_command": "", "start_command": "gunicorn run:app"}
```

**建議 Production gunicorn 參數：**
```
gunicorn run:app --workers=2 --timeout=60 --bind=0.0.0.0:$PORT
```

---

## 已知風險摘要

| 等級 | 項目 | 上線後修復 |
|------|------|-----------|
| 🔴 Critical | 密碼明文 | 立即（BLOCKER） |
| 🔴 Critical | 缺少 CSRF 保護 | 立即（BLOCKER） |
| 🟠 High | requests 依賴缺失 | 立即（BLOCKER） |
| 🟠 High | departure_date 未後端驗證 | V1.1 |
| 🟡 Medium | 人數無後端上限驗證 | V1.1 |
| 🟡 Medium | Driver is_line_bound 同步問題 | V1.1 |
| 🟡 Medium | Session 無過期設定 | V1.1 |
| 🟢 Low | 缺少速率限制 | V1.2 |
| ⚠️ 資料 | DB 1 筆舊資料金額不符 | 可忽略（舊資料） |

---

## Migration 歷史（目前共 8 個）

```
514283b25e63  add_line_user_id_display_name_to_orders
188e2b645ef6  add_group_id_to_orders
4189720aa353  add_deposit_balance_to_orders
534a267a7a66  add_display_name_to_admins
0cea5721016a  add_dispatches_dispatch_orders
0143e6ac9aa7  upgrade_notifications_table
4639baa82115  rebuild_notifications_and_add_driver_line_bind  ← 最新
```

全部 migration 已提交至 `main` 分支。

---

**文件版本：** RC1
**下次更新：** 待 BLOCKER 修復後升版至 RC2
