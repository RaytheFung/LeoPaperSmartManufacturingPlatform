# Task14F DB Mirror Verification Matrix

## 1. mirror identity matrix

| Path | Size bytes | SHA1 | `fact_machine_hour` rows | Month range |
| --- | ---: | --- | ---: | --- |
| `manufacturing_data.db` | `7226900480` | `40a3300e3915fd7e9928e8ef18c2f0a423e08943` | `879978` | `2025-01` -> `2026-02` |
| `/private/tmp/task14f_working_mirror.db` | `7226900480` | `40a3300e3915fd7e9928e8ef18c2f0a423e08943` | `879978` | `2025-01` -> `2026-02` |
| `/Users/rayfung/.codex/memories/task14f_working_mirror_20260419.db` | `7226900480` | `40a3300e3915fd7e9928e8ef18c2f0a423e08943` | `879978` | `2025-01` -> `2026-02` |

## 2. frozen-gate verification matrix

| Metric | Active Task 4L | Task14C staged candidate |
| --- | ---: | ---: |
| Rows considered | `50675` | `50675` |
| Rows evaluated | `50675` | `50675` |
| Non-model-source rows | `0` | `0` |
| Distinct machines retained | `77` | `77` |
| R² | `0.7605741131053376` | `0.812714004142606` |
| MAE | `0.01499678606743838` | `0.012804444950338991` |
| RMSE | `0.1523568146386601` | `0.13475006522302904` |

## 3. post-activation smoke matrix

| Smoke | Month | Passed | Key result |
| --- | --- | --- | --- |
| Direct predictor | `February 2026` | `true` | `source == model` |
| ML route-adjacent smoke | `February 2026` | `true` | `76` candidate rows, `76` prediction rows |
| Optimization route-adjacent smoke | `February 2026` | `true` | `86` machine summary rows, preview available |
| Experimental scheduling smoke | `February 2026` | `true` | `3` optimized schedule rows |

## 4. artifact fingerprint matrix

| Artifact | SHA-256 |
| --- | --- |
| Final live model | `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e` |
| Final live preprocessor | `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27` |
| Final live model provenance | `d23648bb1fb24b9e830ba6586df5ed4faf02645522b085293e968f3a76774ff5` |
| Final live preprocessor provenance | `66cbdb505ef3c577a0523efabf8881d6f6b104470fc17ff203f44f520d3a7611` |
| Fresh Task14F backup model | `1e72e3d80b54da1e122e729f657e3049b771ca9a21a44dcf620f6c905dee4f25` |
| Fresh Task14F backup preprocessor | `f930ac1e9bc65be797532a99c7a51cdf00097c9e8d8eb016e0ba1f6720d4d3b1` |
| Fresh Task14F backup model provenance | `afbac9e1fe4838911e1cb2e21fdc51bb0345f4c05fea526af60b385eec437049` |
| Fresh Task14F backup preprocessor provenance | `dc740043ee931eca1893e30429df149b13c944a4e238a359468d26549f51842c` |
| Staged candidate model | `9dc8822db7d4cfdfecac93f3b3795e472078ec4198c958fc2796bd3e2d282d1e` |
| Staged candidate preprocessor | `4bfa784a73e47e2307977a1b7adf2961c70b7a4819bc092b6a07548facceca27` |
