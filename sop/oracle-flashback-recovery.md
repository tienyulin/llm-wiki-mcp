# Oracle Flashback Recovery 標準作業程序（SOP）

| | |
|---|---|
| 文件編號 | DBA-SOP-014 |
| 適用版本 | Oracle Database 19c / 21c（Enterprise Edition） |
| 適用對象 | Oracle DBA（需 SYSDBA 權限執行第 5 節） |
| 風險等級 | 第 3、4 節：低；第 5 節：**高（不可逆，需變更審批）** |

---

## 1. 目的與範圍

本 SOP 規範使用 Oracle Flashback 技術進行邏輯錯誤復原的標準程序，涵蓋：

- **Flashback Table**：將資料表回溯到過去某個時間點（誤 UPDATE/DELETE）
- **Flashback Drop**：從 Recycle Bin 還原被 DROP 的資料表
- **Restore Point 管理**：高風險變更前建立保證還原點（Guaranteed Restore Point）
- **Flashback Database**：整庫回溯（重大邏輯損壞，最後手段）

不涵蓋：實體損壞復原（使用 RMAN restore/recover）、Data Guard failover。

## 2. 前置條件（任何 Flashback 操作前必須全部確認）

| # | 條件 | 檢查指令 | 預期結果 |
|---|------|---------|---------|
| P1 | 資料庫為 ARCHIVELOG 模式 | `SELECT log_mode FROM v$database;` | `ARCHIVELOG` |
| P2 | Flashback logging 已啟用（僅 Flashback Database 需要） | `SELECT flashback_on FROM v$database;` | `YES` |
| P3 | FRA（Fast Recovery Area）已設定且空間充足 | `SELECT name, space_limit, space_used FROM v$recovery_file_dest;` | 使用率 < 85% |
| P4 | 目標時間點在 flashback 保留範圍內 | `SELECT oldest_flashback_scn, oldest_flashback_time FROM v$flashback_database_log;` | 目標 SCN/時間 ≥ oldest |
| P5 | Recycle Bin 已啟用（僅 Flashback Drop 需要） | `SHOW PARAMETER recyclebin;` | `on` |
| P6 | （Flashback Table）目標表已啟用 ROW MOVEMENT | `SELECT row_movement FROM dba_tables WHERE owner='&owner' AND table_name='&table';` | `ENABLED` |

保留時間目標由 `DB_FLASHBACK_RETENTION_TARGET` 控制（單位分鐘，預設 1440 = 24 小時）。

## 3. 操作一：Restore Point 管理

### 3.1 建立 Guaranteed Restore Point（高風險變更前）

```sql
CREATE RESTORE POINT before_upgrade_20260612 GUARANTEE FLASHBACK DATABASE;
```

- 名稱規範：`before_<變更說明>_<YYYYMMDD>`
- GUARANTEE 類型不受保留時間限制，但會持續占用 FRA——**變更驗證完成後必須刪除**（見 3.3）

### 3.2 查詢現有 Restore Points

```sql
SELECT name, scn, time, guarantee_flashback_database, storage_size
FROM v$restore_point ORDER BY scn;
```

### 3.3 刪除 Restore Point

```sql
DROP RESTORE POINT before_upgrade_20260612;
```

注意：Guaranteed Restore Point 未刪除會導致 FRA 持續成長，最終觸發 ORA-19809。

## 4. 操作二：Flashback Table / Flashback Drop（schema 層級，低風險）

### 4.1 Flashback Table（回溯誤改資料）

1. 確認 P1、P3、P4、P6。P6 未啟用時先執行：
   ```sql
   ALTER TABLE scott.emp ENABLE ROW MOVEMENT;
   ```
2. 查詢目前 SCN 以便回退（操作本身可再次 flashback 回來）：
   ```sql
   SELECT current_scn FROM v$database;
   ```
3. 執行回溯（擇一）：
   ```sql
   FLASHBACK TABLE scott.emp TO SCN 1234567;
   FLASHBACK TABLE scott.emp TO TIMESTAMP TO_TIMESTAMP('2026-06-12 09:00:00','YYYY-MM-DD HH24:MI:SS');
   ```
4. 驗證資料正確性（業務確認），錯誤則用步驟 2 記錄的 SCN 再 flashback 回去。

### 4.2 Flashback Drop（還原誤刪資料表）

1. 確認 P5，查詢 Recycle Bin：
   ```sql
   SELECT object_name, original_name, droptime FROM dba_recyclebin
   WHERE owner='SCOTT' AND original_name='EMP' ORDER BY droptime DESC;
   ```
2. 還原（同名表已存在時必須 RENAME）：
   ```sql
   FLASHBACK TABLE scott.emp TO BEFORE DROP;
   FLASHBACK TABLE scott.emp TO BEFORE DROP RENAME TO emp_restored;
   ```
3. 注意：索引還原後為系統名（`BIN$...`），需手動 rename；同名多版本時還原最近一次 DROP 的版本。

## 5. 操作三：Flashback Database（整庫回溯，**不可逆，需審批**）

> **警告**：執行後目標時間點之後的所有交易永久遺失，且 OPEN RESETLOGS 後無法
> flashback 回到 RESETLOGS 之後的時間點。必須取得變更審批單號後才可執行。

1. 確認 P1–P4。預估所需 flashback log 量：
   ```sql
   SELECT estimated_flashback_size FROM v$flashback_database_log;
   ```
2. 通知應用停機，關閉並 MOUNT：
   ```sql
   SHUTDOWN IMMEDIATE;
   STARTUP MOUNT;
   ```
3. 執行回溯（擇一）：
   ```sql
   FLASHBACK DATABASE TO RESTORE POINT before_upgrade_20260612;
   FLASHBACK DATABASE TO SCN 1234567;
   FLASHBACK DATABASE TO TIMESTAMP TO_TIMESTAMP('2026-06-12 09:00:00','YYYY-MM-DD HH24:MI:SS');
   ```
4. 先以 READ ONLY 開啟驗證資料；確認無誤後才 RESETLOGS：
   ```sql
   ALTER DATABASE OPEN READ ONLY;
   -- 驗證通過後：
   SHUTDOWN IMMEDIATE; STARTUP MOUNT;
   ALTER DATABASE OPEN RESETLOGS;
   ```
5. RESETLOGS 後立即執行全備（舊備份基線失效）。

## 6. 驗證與收尾

- 業務單位確認資料正確
- Flashback Database 完成後：檢查 `v$database.resetlogs_time`、執行 RMAN 全備
- 刪除已完成用途的 Guaranteed Restore Point
- 於變更系統記錄：操作類型、目標物件、目標 SCN/時間、執行人、審批單號、結果

## 7. 常見錯誤與排除

| 錯誤 | 原因 | 處置 |
|------|------|------|
| ORA-38729 | 目標時間點超出 flashback log 保留範圍（違反 P4） | 改用 RMAN point-in-time recovery |
| ORA-08189 | 表未啟用 ROW MOVEMENT（違反 P6） | `ALTER TABLE ... ENABLE ROW MOVEMENT` 後重試 |
| ORA-38305 | 物件不在 Recycle Bin（已 PURGE 或 P5 關閉） | 改用 RMAN 或輔助庫匯出 |
| ORA-19809 | FRA 空間不足（違反 P3） | 加大 `DB_RECOVERY_FILE_DEST_SIZE`、刪除過期備份/已用 GRP |
| ORA-38780 | Restore point 不存在 | `v$restore_point` 確認名稱 |
| ORA-38796 | 同名 restore point 已存在 | 改名或先 DROP 舊的 |
| ORA-38312 | Flashback Drop 還原目標名稱與現有表衝突 | 使用 `RENAME TO` 還原為新名稱（見 4.2） |

## 8. 審計要求

所有 flashback 操作（含查詢以外的全部動作）必須留存：時間、執行人、操作類型、
目標物件、目標 SCN/時間點、dry-run 與否、審批單號（第 5 節必填）、執行結果。
