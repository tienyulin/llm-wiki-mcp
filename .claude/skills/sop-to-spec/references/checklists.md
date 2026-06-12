# 清單集（sop-to-spec v5）

## 逼問清單（Step 3，寫每端點 AC 時逐題回答，答案寫進 AC——不准留白）

- 每個 **optional 欄位**：None 時行為？
- 每個**比較**：邊界含不含等號？
- 每個**替代輸入形式**（如 scn vs timestamp vs name）：誰負責解析成 canonical
  形式？用什麼方法？解析失敗回什麼？每個形式都要有自己的 AC
- **dry_run** response 有哪些欄位？回退資訊（prior state）在 dry_run 給不給？
- dry_run 的預測範圍：執行後才知道的值（新 etag、新 id）**不預測**，明寫哪些不給
- 操作**耗時**？sync 或 202？timeout 責任在誰？
- **並發**：兩請求同打一資源會怎樣？（狀態機擋 or 未防護＋風險說明）
- **冪等**：同請求打兩次，第二次回什麼？
- **輔助性 mutation**（自動修復前置條件的 ALTER 之類）：必須在**其餘全部前置
  條件確定通過後**才執行——注定失敗的請求不得留下副作用
- **鏈式結果狀態**：操作後「浮上來」的東西可能還是同類（如 delete marker 下面
  還是 delete marker）——爬不爬鏈要明寫
- 固定文案/token：spec 給字面值＋常數檔名

## 自檢清單（Step 4）

- [ ] **Part A 白話測試**：不懂 HTTP 的主管讀完 A1–A6 能說出「這 API 做什麼、
      最危險的操作是什麼、什麼情況下會被擋」
- [ ] Part A 與 Part B 一致（A2 端點 = §2 總表；A5 = §9）
- [ ] SOP 每個操作都在 spec（或 Out of Scope＋原因）
- [ ] 每條 AC 可單獨驗證（確切輸入、HTTP code、欄位值）
- [ ] 每端點 happy/edge/failure 三類 AC 都有
- [ ] 逼問清單每題每端點都有對應 AC
- [ ] **fresh-repo 測試**：任何「比照/見/沿用」指向 spec 外（SOP 編號除外）→ inline
- [ ] mock 初始狀態足以跑完測試計畫全部案例

## 盲審閘門（Step 5）

派**乾淨 context 的 agent**（不給 SOP、不給 repo 背景），prompt 重點：

> 只讀 <spec 路徑>。列出實作者必須猜測或發明的每一處（兩個合理實作者會做出
> 不同行為 = HIGH；要自行決定並記錄 = MED；外觀 = LOW）。嚴格，不要稱讚。

另派（或同 agent 第二部）讀 Part A 問：「不懂技術的審批者能否回答：這 API
做什麼、最危險操作、防護是什麼？」答不出 = Part A 不合格。

**分流規則**（盲審約 30% 是誤判——經驗值）：
- 每條發現**逐字對回 spec 原文**再判定；spec 已明文的 → 駁回並記理由
- 真 HIGH > 0 → 修 spec 重審，**不准開工**
- 全部發現與處置（含駁回理由）記入 `specs/REVIEWS.md`

## 實作回饋歸因表（Step 6）

| 歸因 | 動作 |
|------|------|
| SOP 缺資訊（錯誤碼缺漏等） | 補 SOP ＋ spec |
| skill 模板/逼問清單沒問到 | 改 skill ＋ 重產 spec 該節 |
| spec 產出沒照模板 | 重產 spec 該節 |
| 純 code bug | 修 code ＋ 補 AC 對應測試 |

修完重跑 Step 4；重大修改重跑 Step 5。全程記 `specs/REVIEWS.md`。
