# sop-to-spec 迭代調優紀錄

每輪：乾淨 context 的 agent 盲審（只讀 spec）＋ spec↔code drift 比對 →
誠實分流（含駁回誤判）→ 缺陷歸因（SOP / skill / spec / code）→ 修對應層。
外部參照：GitHub spec-kit（spec 為唯一事實、Spec→Plan→Tasks）、AWS Kiro
（EARS 驗收準則、審批閘門）。

---

## Iteration 1 — 盲審 skill v1 產物（flashback spec v1 + code v1）

發現：18 條 spec 不自足 ＋ 18 條 drift（HIGH×2 真 bug）。

| 關鍵發現 | 嚴重度 | 歸因 | 動作 |
|---------|--------|------|------|
| timestamp 目標整條壞：table 給 timestamp 時實際回溯到 current SCN（沒動）、database 回溯到保留邊界；測試全用 scn 沒蓋到 | HIGH | **skill**（模板沒逼問「替代輸入形式誰解析、怎麼解析」）→ spec 沒定義 → code 亂猜 | skill v2 加逼問清單；spec v2 定 target 解析三步序＋mock 換算公式；code 加 `timestamp_to_scn`；補 timestamp 測試 |
| dry_run response 形狀各端點自行發明 | MED | skill | v2 統一 response 形狀（3b） |
| 閘門順序（auth/422/404/428/409）未定義 | MED | skill | v2 標準閘門順序（3a） |
| 「比照 wiki-processor」依賴 repo 外知識 | MED | skill | v2 自足性鐵律＋fresh-repo 自檢 |
| db_state 狀態機沒畫、邊界 ≥/> 含糊、response 只有散文 | MED | skill | v2：狀態機必畫、EARS 準則、formal JSON |
| audit result 字串模式 spec/code 不一致；未來 SCN 422 是 code 自行發明 | MED | spec | v2 封閉枚舉＋AC-FT-6 |

skill v1→v2：EARS 驗收準則、閘門順序、逼問清單、狀態機、自足性、盲審閘門（Step 5）。

## Iteration 2 — 盲審 spec v2 + drift 比對 code v2

發現 21 條（標 HIGH×5）。誠實分流：

**接受並修復：**

| 發現 | 歸因 | 動作 |
|------|------|------|
| DRIFT-003：`enable_row_movement` 在其他前置條件確認前執行——注定失敗的請求留下已執行的 ALTER | **skill**（沒逼問輔助性 mutation 時機） | skill 加規則；code 改為其餘條件全過才 enable；加回歸測試 |
| IMPL-002/DRIFT-006/007：固定文案/confirm token 散在 service 字串 | skill | spec 指明常數唯一出處 `models/schemas.py`；code 集中常數 |
| IMPL-001/003/008、DRIFT-010 等：dry_run 解析時機、rounding、conftest reset、checks 完整性斷言 | spec/測試 | spec 各補一句；測試補斷言 |

**駁回（誤判，附理由）：**

| 發現 | 駁回理由 |
|------|---------|
| DRIFT-001/004「audit 用未定義字串 table-not-found / not-flashbacked」 | spec §7 允許 `rejected:<error_code 或短原因>`，短原因合法 |
| DRIFT-013「finalize 成功 audit 缺 dry_run 欄位」 | `_audit` 預設 `dry_run=False`，欄位必出現 |
| IMPL-004「table/RP 不檢查 db_state 未說明」 | spec §2.5 已明文＋§9 風險記錄 |
| DRIFT-002「resolve 例外路徑」 | 驗證過：P4 先擋、例外進 `error:` audit，行為已定義 |

## Iteration 3 — 通用性驗證（第二領域：MinIO bucket DR）

寫 `sop/minio-bucket-disaster-recovery.md`（OPS-SOP-021），用 skill v3 產
`specs/minio-bucket-disaster-recovery-api.spec.md`（**僅 spec，不實作**），盲審。

發現 20 條（標 HIGH×6）。分流：

**接受並修復（真缺口）：**

| 發現 | 歸因 | 動作 |
|------|------|------|
| undelete 後浮上來的可能還是 delete marker——`current_version` 爬不爬鏈未定義 | **skill**（鏈式結果狀態沒逼問） | skill 加逼問項；spec 定「不爬鏈，照實回傳」 |
| repository 空 list 與 service 404 的分工未定義 | **skill** | skill 3f 加「repository 永不擲業務錯誤」鐵律；spec 補 |
| dry_run 閘門語句改寫後再度被誤讀 | **skill**（語句每次重寫） | skill 提供 canonical 句子，要求照抄 |
| RV-2 不預測 new_version、mock seq reset、rejected 後綴規則、purged 計數口徑 | spec | 各補一句 |

**駁回（誤判，附理由）：** 404 先於 428（§0.1＋AC-PG-4 已雙重明文）、purge 無前置
條件（AC-PG-2/PG-6 已明文）、latest 平手規則（§0.2.1 已給 FIFO）、401 不留 audit
（§7 已明文）、key rotation 即時生效（per-request 讀 env 即為規格）。

skill v3→v4：canonical dry_run 句、鏈式結果狀態、dry_run 預測範圍、repository
不擲業務錯誤。

## 退出狀態

- flashback spec/code：47 tests passed，每條 AC 有對應測試（名含 AC 編號），
  timestamp 路徑有測試
- 第二領域 spec：盲審真 HIGH（誠實分流後）= 0；殘餘 MED 均已一行修或記錄接受
- 已知殘餘風險（接受）：FLASHBACKED 下不擋 table/RP 操作（§9）、無並發防護
  （單人維運假設）、202 async 模式未做（§9）

## 對「盲審」機制本身的觀察

- 乾淨 context 盲審每輪都能抓到作者盲點（timestamp bug、副作用順序、鏈式語意）
  ——值得固定為 Step 5 閘門
- 盲審也產生 ~30% 誤判（已明文的規則被報為缺漏）——**分流必須逐條對回 spec
  原文**，不可照單全收，駁回要附理由留痕（本檔案的用途）
