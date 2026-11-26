# Capabilities and Diagnostic Indicators

Technical specification of the indicator catalog, Weighted Health Score model,
and storage engine coverage in `mysqltuner.pl`.

## Indicator Catalog Summary (`--list-indicators`)

Executing `perl mysqltuner.pl --list-indicators` exports the static catalog in
offline JSON without connecting to a database (`version`: `2.9.4`).

| Metric | Count | JSON Field | Description |
| :--- | :--- | :--- | :--- |
| Total Indicators | `1125` | `summary.total` | Sum of all `good`, `bad`, `info`, and `rec` entries |
| Efficiency Checks (`OK`) | `165` | `summary.good` | Passing health checks (`goodprint`) |
| Risk Detections (`WARN`) | `322` | `summary.bad` | Warnings and failures (`badprint`) |
| Information Points (`INFO`) | `582` | `summary.info` | Telemetry and context outputs (`infoprint`) |
| Recommendations (`REC`) | `56` | `summary.rec` | Explicit advice items (`push_recommendation`) |
| Feature Subroutines | `39` | `summary.features` | `34` report sections + `5` standalone audit subroutines |

All indicators map to nine functional categories: `General`, `System`,
`Storage`, `Modeling`, `Performance`, `Security`, `HA`, `Capacity`, and
`Automation`.

## Weighted Health Score (`40 / 30 / 30` Model)

`calculate_health_score()` computes `HealthScore` / `WeightedHealthScore` on a
`0` to `100` scale from three weighted pillars (`HealthScoreDetails`).

| Pillar (Max) | Detail Key | Source Metric | Scoring Rules | Undefined Fallback |
| :--- | :--- | :--- | :--- | :--- |
| Performance (`40`) | `perf_bp` | `pct_read_efficiency` | `> 99%` = `10`; `> 95%` = `5`; `<= 95%` = `0` | `5` |
| Performance (`40`) | `perf_temp` | `pct_temp_disk` | `< 10%` = `10`; `< 25%` = `5`; `>= 25%` = `0` | `5` |
| Performance (`40`) | `perf_thread` | `thread_cache_hit_rate` | `> 90%` = `10`; `> 50%` = `5`; `<= 50%` = `0` | `5` |
| Performance (`40`) | `perf_conn` | `pct_connections_used` | `< 80%` = `10`; `>= 80%` = `0` | `5` |
| Security (`30`) | `sec_total` | `scalar(@secrec)` | Starts at `30`; deducts `5` per `@secrec` entry; floor `0` | `30` |
| Resilience (`30`) | `res_lag` | `%myrepl` thread and lag state | `10` if standalone or `YES` with lag `< 1s`; `5` if `1..59s`; `0` if stopped/non-numeric/`>= 60s` | `10` |
| Resilience (`30`) | `res_logs` | `@adjvars` redo/log entries | Starts at `10`; deducts `5` if `innodb_log_file_size` or `innodb_redo_log_capacity` adjusted | `10` |
| Resilience (`30`) | `res_meta` | `scalar(@modeling)` | Starts at `10`; deducts `5` if `scalar(@modeling) > 5` | `10` |

### Display Bands and Auxiliary KPIs

| KPI Structure | Range / Bands | Components |
| :--- | :--- | :--- |
| `WeightedHealthScore` Display Color | `> 80` Green; `51..80` Yellow; `<= 50` Red | `perf_*` (`40`) + `sec_total` (`30`) + `res_*` (`30`) |
| `WeightedHealthScore` Console Verdict | `< 70` WARN; `70..89` INFO; `>= 90` OK | Emitted by `display_health_score()` |
| `SectionalHealthScore` | `0..100` per domain | `General`, `Storage`, `Security`, `Replication`, `Modeling` |
| `ResourceSaturation` | `0..100` percentage | `CPU`, `Memory`, `Connections`, `IO` |
| `ThroughputEfficiency` | Floating-point telemetry | `QPS`, `LogicalReadsSec`, `Index` (`QPS / LogicalReadsSec`) |

## Storage Engines Support Matrix

| Storage Engine | Subroutine | Support Status | Audited Metrics / Notes |
| :--- | :--- | :--- | :--- |
| `InnoDB` | `mysql_innodb` | Full support | Buffer pool size/instances/chunks, redo log, hit ratio, log waits, AHI, SSD/NVMe tuning, index/data ratio |
| `MyISAM` | `mysql_myisam` | Legacy maintenance | `key_buffer_size`, key cache read/write hit rates, index footprint |
| `Aria` | `mariadb_aria` | MariaDB supported | `aria_pagecache_buffer_size`, pagecache read hit rate, `.MAI` index total |
| `Galera / XtraDB Cluster` | `mariadb_galera` | Full support | `wsrep_ready`, cluster status, flow control (`gcs.fc_*`), SST, certification failures, PK checks |
| `TokuDB` | `mariadb_tokudb` | Status check only | Reports `have_tokudb` enabled/disabled; upstream unmaintained |
| `XtraDB` | `mariadb_xtradb` | Status check only | Reports `have_xtradb`; notes MariaDB 10.2+ uses InnoDB |
| `RocksDB` | `mariadb_rockdb` | Status check only | Reports `have_rocksdb` enabled/disabled; upstream unmaintained |
| `Spider` | `mariadb_spider` | Status check only | Reports `have_spider` enabled/disabled; unsupported for tuning |
| `Archive`, `ColumnStore`, `Connect`, `NDB` | `check_storage_engines` | Inventory only | Listed via `information_schema.ENGINES`; no tuning subroutine |
| `MEMORY`, `Federated`, `BDB`, `ISAM` | `check_storage_engines` | Inventory / legacy | Tracked in table size/count aggregation (`--skipsize` bypasses) |

## Feature Subroutines Catalog

[FEATURES.md](https://github.com/major/MySQLTuner-perl/blob/master/FEATURES.md)

<!-- INCLUDE_SOURCE: FEATURES.md -->

## Related Documentation

- Threshold details and data files:
  [Thresholds and Data Files](../configuration/thresholds-and-files.md)
- Deep dive on Health Score scoring:
  [Health Score and Version Rift](../../04-explanation/deep-dives/health-score-and-version-rift.md)
