# Task14A Monthly ML Readiness Matrix

## 1. monthly readiness matrix

| Month | Canonical rows | Inferable rows | Inferable machines | Direct | Adapted | Defaulted | Blocked | Dominant blocker |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| January 2025 | `64,725` | `3,945` | `24` | `3,814` | `123` | `8` | `60,780` | `missing_positive_good_qty (42,552)` |
| February 2025 | `58,461` | `12,577` | `52` | `12,456` | `114` | `7` | `45,884` | `missing_positive_good_qty (34,854)` |
| March 2025 | `64,725` | `24,727` | `63` | `24,426` | `298` | `3` | `39,998` | `missing_positive_good_qty (31,347)` |
| April 2025 | `62,637` | `27,914` | `71` | `27,549` | `361` | `4` | `34,723` | `missing_positive_good_qty (29,533)` |
| May 2025 | `65,165` | `32,607` | `77` | `32,305` | `288` | `14` | `32,558` | `missing_positive_good_qty (29,333)` |
| June 2025 | `62,639` | `33,798` | `76` | `33,460` | `302` | `36` | `28,841` | `missing_positive_good_qty (26,524)` |
| July 2025 | `64,727` | `35,701` | `80` | `35,376` | `312` | `13` | `29,026` | `missing_positive_good_qty (27,205)` |
| August 2025 | `64,727` | `31,582` | `81` | `31,295` | `271` | `16` | `33,145` | `missing_positive_good_qty (32,269)` |
| September 2025 | `62,640` | `28,123` | `83` | `27,881` | `242` | `0` | `34,517` | `missing_positive_good_qty (33,840)` |
| October 2025 | `64,247` | `25,407` | `81` | `25,128` | `274` | `5` | `38,840` | `missing_positive_good_qty (38,632)` |
| November 2025 | `61,199` | `31,572` | `76` | `31,282` | `270` | `20` | `29,627` | `missing_positive_good_qty (29,535)` |
| December 2025 | `63,240` | `34,261` | `77` | `33,960` | `285` | `16` | `28,979` | `missing_positive_good_qty (28,658)` |
| January 2026 | `63,054` | `32,757` | `77` | `32,536` | `207` | `14` | `30,297` | `missing_positive_good_qty (29,972)` |
| February 2026 | `57,792` | `18,762` | `76` | `18,604` | `145` | `13` | `39,030` | `missing_positive_good_qty (38,624)` |

## 2. post-june support summary

- Post-June canonical rows loaded = `501,626`
- Post-June inferable rows = `238,165`
- Post-June support-path composition:
  - direct = `236,062`
  - adapted = `2,006`
  - defaulted = `97`
  - blocked = `263,461`
- Post-June blocked reasons:
  - `missing_positive_good_qty = 258,735`
  - `missing_hours_since_last_maintenance = 4,725`
  - `unmapped_task_name = 1`

## 3. candidate predictor audit

- Latest-machine candidate rows per month matched the inferable machine count for every audited month.
- All candidate predictions returned `source == model`; none fell back.
- Representative post-June saved-model samples:

| Anchor month | Machine | Hour | Predicted kWh / unit | Confidence | Support path |
| --- | --- | --- | ---: | ---: | --- |
| July 2025 | `024-003` | `2025-07-31T22:00:00` | `0.012590` | `0.6727` | `Direct canonical row` |
| October 2025 | `024-003` | `2025-10-31T23:00:00` | `0.005132` | `0.4973` | `Direct canonical row` |
| February 2026 | `024-003` | `2026-02-28T23:00:00` | `0.005391` | `0.4705` | `Direct canonical row` |
