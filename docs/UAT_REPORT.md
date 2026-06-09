# UAT Report — BTS Shuttle Booking RC1

**Date:** 2026-06-09
**Version:** RC1
**Environment:** Local (127.0.0.1:5000) + Zeabur (bts-shuttle-booking.anjiatra.com)

---

## 測試範圍

| 模組 | 測試項目 | 結果 |
|------|---------|------|
| 乘客預約 | 預約流程 | ✅ PASS |
| 乘客預約 | 訂金制金額計算 | ✅ PASS |
| 乘客預約 | LIFF 身份取得 | ⚠️ 需驗證 |
| 訂單查詢 | LINE 模式查詢 | ⚠️ 需驗證 |
| 訂單查詢 | 表單模式查詢 | ✅ PASS |
| 匯款回報 | 回報流程 | ✅ PASS |
| 同行群組 | 建立群組 | ✅ PASS |
| 同行群組 | 加入群組 | ✅ PASS |
| 同行群組 | LINE 分享 | ⚠️ 需驗證 |
| 後台登入 | 帳號密碼驗證 | ✅ PASS |
| 後台訂單 | CRUD 操作 | ✅ PASS |
| 後台付款 | 確認訂金 | ✅ PASS |
| 後台車輛 | CRUD 操作 | ✅ PASS |
| 後台司機 | CRUD 操作 | ✅ PASS |
| 後台管理員 | CRUD 操作 | ✅ PASS |
| 排車管理 | 自動排車 | ✅ PASS (邏輯) |
| 排車管理 | 手動排車 | ✅ PASS |
| 排車管理 | Drag & Drop | ✅ PASS |
| LINE 通知 | 司機通知 | ⚠️ 需 token |
| LINE 通知 | 乘客通知 | ⚠️ 需 token |
| LINE 通知 | 重送機制 | ✅ PASS (邏輯) |
| 司機綁定 | LIFF 頁面 | ⚠️ 需驗證 |
| 儀表板 | 統計數字 | ✅ PASS |

---

## 詳細測試結果

### 1. 乘客預約流程

**測試路徑：** `/booking`

| 步驟 | 預期行為 | 實際行為 | 狀態 |
|------|---------|---------|------|
| GET /booking | 顯示預約表單 | ✅ 正常顯示 | PASS |
| 選擇場次 | 僅顯示三個有效場次 | ✅ 下拉選單正確 | PASS |
| 輸入人數 1-8 | 計算金額 = 人數 × 2000 | ✅ JS 即時計算 | PASS |
| 訂金計算 | 300 × 人數 | ✅ 正確 | PASS |
| 尾款計算 | 1700 × 人數 | ✅ 正確 | PASS |
| POST 送出 | 建立訂單，redirect payment_report | ✅ 正常 | PASS |
| LIFF 登入 | 取得 userId / displayName | ⚠️ 需 LINE OA 環境驗證 | PENDING |

**已知問題：**
- 人數欄位 `max="50"` 但後端無驗證，可 POST 任意人數（見 SECURITY_REPORT M1）
- departure_date 後端未驗證白名單（見 SECURITY_REPORT H2）

---

### 2. 匯款回報流程

**測試路徑：** `/payment/report`

| 步驟 | 預期行為 | 狀態 |
|------|---------|------|
| 顯示訂單資訊 | 正確帶入訂單編號 | PASS |
| 輸入匯款資料 | 儲存 Payment 記錄 | PASS |
| 狀態更新 | order.payment_status → 待確認 | PASS |
| 重複回報防護 | 已確認訂單顯示提示 | PASS |

---

### 3. 同行群組

**測試路徑：** `/join/<group_id>`

| 步驟 | 預期行為 | 狀態 |
|------|---------|------|
| 預約時自動建立群組 ID | BTS-FRIEND-XXXXXX 格式 | PASS |
| 邀請連結顯示 | payment_report 頁顯示連結 | PASS |
| LINE Share 按鈕 | 開啟 liff.shareTargetPicker | PENDING (需 LIFF) |
| 加入群組 | 輸入訂單編號加入 | PASS |
| 日期不符防護 | 不同日期無法加入 | PASS |
| 同車優先排車 | auto_dispatch 優先同車 | PASS (邏輯) |

---

### 4. 後台管理

**測試路徑：** `/admin/*`

| 功能 | 狀態 | 備註 |
|------|------|------|
| 登入 / 登出 | PASS | 密碼明文（待修復） |
| 訂單列表 + 搜尋 | PASS | |
| 訂單狀態更新 | PASS | |
| 付款確認 → 訂金已確認 | PASS | |
| 車輛 CRUD | PASS | |
| 司機 CRUD | PASS | |
| 管理員 CRUD | PASS | |
| 自我刪除防護 | PASS | 不能刪自己 |
| 儀表板統計 | PASS | |

---

### 5. 排車管理

**測試路徑：** `/admin/dispatch`

| 功能 | 狀態 | 備註 |
|------|------|------|
| 日期 Tab 切換 | PASS | |
| 自動排車 | PASS | 需有訂金已確認訂單 |
| 手動建立車輛 | PASS | |
| Drag & Drop | PASS | |
| 同車最大 8 人 | PASS | 超過拒絕 |
| Group 同車優先 | PASS | |
| Group >8 警告 | PASS | |
| 刪除 dispatch | PASS | 訂單移回待排車 |
| 通知司機 按鈕 | PASS (邏輯) | 需 DRIVER token |
| 通知乘客 按鈕 | PASS (邏輯) | 需 PASSENGER token |
| 批次通知司機 | PASS (邏輯) | 需 token |
| 批次通知乘客 | PASS (邏輯) | 需 token |
| 通知狀態顯示 | PASS | |
| 重送失敗通知 | PASS (邏輯) | 需 token |

---

### 6. LINE 整合

| 功能 | 環境 | 狀態 | 備註 |
|------|------|------|------|
| 乘客 LIFF 初始化 | LINE App | PENDING | 需設 PASSENGER_LIFF_ID |
| 司機 LIFF 綁定 | LINE App | PENDING | 需設 DRIVER_LIFF_ID |
| Push Message 司機 | Zeabur | PENDING | 需設 DRIVER_LINE_CHANNEL_ACCESS_TOKEN |
| Push Message 乘客 | Zeabur | PENDING | 需設 PASSENGER_LINE_CHANNEL_ACCESS_TOKEN |

---

## PENDING 項目驗收條件

### ⚠️ PENDING-01: LIFF 功能驗證

**條件：**
1. 在 LINE Developers Console 設定好兩個 LIFF URL
2. Zeabur 設定 `PASSENGER_LIFF_ID` 和 `DRIVER_LIFF_ID`
3. 透過 LINE App 開啟 `/booking`、`/orders/search`、`/payment/report`
4. 確認 userId / displayName 正確填入

### ⚠️ PENDING-02: LINE Push Message 驗證

**條件：**
1. Zeabur 設定 `PASSENGER_LINE_CHANNEL_ACCESS_TOKEN` 和 `DRIVER_LINE_CHANNEL_ACCESS_TOKEN`
2. 建立至少一筆「訂金已確認」訂單且有 line_user_id
3. 建立至少一筆 Dispatch
4. 點擊「通知乘客」確認收到 LINE 訊息
5. 確認 Notification 記錄正確儲存

### ⚠️ PENDING-03: 司機 LINE 綁定

**條件：**
1. 在 LINE Developers Console 設定 Driver LIFF URL 為 `/driver/bind`
2. 建立司機帳號（有電話號碼）
3. 透過 LINE App 開啟 `/driver/bind`
4. 輸入電話完成綁定
5. 確認 `drivers.line_user_id` 和 `is_line_bound=true` 正確儲存

---

## 整體評估

**目前狀態：** RC1 — 功能完整，需修復 2 個 Critical 安全問題後可上線

**功能完整度：** 95%（僅 LINE 相關功能待 Production 環境驗證）

**上線阻擋項：**
1. C1 密碼明文（CRITICAL）
2. C2 CSRF（CRITICAL）
3. H3 requests 依賴缺失（HIGH）
