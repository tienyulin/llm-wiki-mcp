# MinIO Bucket 災難復原標準作業程序（SOP）

| | |
|---|---|
| 文件編號 | OPS-SOP-021 |
| 適用版本 | MinIO RELEASE.2024+（啟用 versioning 的部署） |
| 適用對象 | 平台維運（需 admin credentials 執行第 4 節） |
| 風險等級 | 第 2、3 節：低；第 4 節：**高（不可逆，需審批）** |

## 1. 目的與範圍

處理 bucket 內物件**誤刪、誤覆寫**的復原，依賴 MinIO object versioning。
涵蓋：版本查詢、還原舊版本、撤銷刪除（移除 delete marker）、版本歷史清除。
不涵蓋：磁碟/erasure set 損毀（屬基礎設施 SOP）、跨站 replication failover。

## 2. 前置條件

| # | 條件 | 檢查指令 | 預期 |
|---|------|---------|------|
| C1 | bucket 存在 | `mc ls myminio/<bucket>` | 不報錯 |
| C2 | versioning 為 Enabled | `mc version info myminio/<bucket>` | `Enabled`（Suspended 期間寫入的物件沒有版本可救） |
| C3 | 目標版本仍存在（未被 lifecycle 清掉） | `mc ls --versions myminio/<bucket>/<key>` | 列出目標 version id |

## 3. 操作一：物件復原（低風險，可重複）

### 3.1 查詢物件版本

```
mc ls --versions myminio/data-bucket/reports/q1.csv
```
輸出含 version id、時間、是否 delete marker。

### 3.2 還原到指定舊版本（誤覆寫）

把舊版本內容複製回成為新的最新版本（原版本鏈不動，操作本身可再還原）：
```
mc cp --version-id <vid> myminio/data-bucket/reports/q1.csv myminio/data-bucket/reports/q1.csv
```

### 3.3 撤銷刪除（誤刪 = 移除 delete marker）

```
mc rm --version-id <delete-marker-vid> myminio/data-bucket/reports/q1.csv
```
移除 delete marker 後物件回到上一個實體版本。注意：delete marker 必須是
**最新版本**才代表「目前被刪」；對歷史 delete marker 操作無意義。

## 4. 操作二：版本歷史清除（**不可逆，需審批**）

> 警告：清除後所有歷史版本永久消失，無法復原。僅用於確認資料已不需保留
> （法遵清理、空間回收）。需變更審批單號。

```
mc rm --versions --force myminio/data-bucket/reports/q1.csv
```
物件含全部版本與 delete markers 一併刪除。

## 5. 驗證與收尾

- 還原後 `mc stat` 確認 etag/size 與預期版本一致，業務確認內容
- 於變更系統記錄：操作、bucket/key、version id、執行人、審批單號（第 4 節必填）、結果

## 6. 常見錯誤與排除

| 錯誤 | 原因 | 處置 |
|------|------|------|
| `NoSuchBucket` | C1 違反 | 確認 bucket 名 / alias |
| `NoSuchVersion` | C3 違反（version id 錯或已被 lifecycle 刪除） | `mc ls --versions` 重新確認；無版本則改走備份還原 |
| versioning `Suspended` | C2 違反 | Suspended 期間的覆寫無版本可救，改走備份還原；先 `mc version enable` 防止再發 |
| delete marker 非最新版本 | §3.3 注意事項 | 物件目前未被刪，確認 key 是否正確 |

## 7. 審計要求

所有操作（查詢以外）留存：時間、執行人、bucket、object key、version id、
dry-run 與否、審批單號（第 4 節必填）、結果。
