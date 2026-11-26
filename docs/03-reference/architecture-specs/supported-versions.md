# Supported Database Versions

Authoritative compatibility matrix, lifecycle cycles, and database privilege
requirements for MySQLTuner.

## Engine and Platform Compatibility

| Engine / Platform | Support Tier | Detection Signal | Notes |
| :--- | :--- | :--- | :--- |
| MySQL | Full support | `@@version` / `@@version_comment` | Supports 5.5 through 9.x and 26.x cycles |
| MariaDB | Full support | `is_mariadb()` via version/comment or major `10..25` | Supports 10.x through 13.0 cycles |
| Percona Server | Full support | `@@version_comment` (`Percona`) | Tested against Percona Server 8.0 |
| Galera / Percona XtraDB Cluster | Full support | `wsrep_on = ON` | Audits quorum, flow control, SST, and PKs |
| MySQL Group Replication | Full support | `group_replication_group_name` | Audits `replication_group_members` and roles |
| Asynchronous / Semi-Sync Replication | Supported | `SHOW REPLICA STATUS` / `SHOW SLAVE STATUS` | Supports multi-source channels and GTID |
| Cloud Managed (AWS, GCP, Azure, DO) | Autodiscovered | `@@version_comment`, `@@aurora_version`, `@@cloudsql_instance_id` | Adjusts OS and storage checks automatically |
| Windows Host | Partial | `$^O eq 'MSWin32'` | Uses PowerShell `Get-CimInstance` with WMIC fallback |

## Synchronized Release Cycles

Release cycles below reflect `build/ci_matrix.json` and `mysqltuner.pl`
(`@SUPPORTED_LTS_VERSIONS` and `@SUPPORTED_SHORT_TERM_VERSIONS`). Run
`make sync_versions` to propagate matrix updates.

| Engine | LTS Cycles | Legacy Supported | Short-Term Support | CI Default Targets |
| :--- | :--- | :--- | :--- | :--- |
| MySQL | `8.4`, `9.7` | `8.0` | `26.10` | `8.0`, `8.4` |
| MariaDB | `10.11`, `11.4`, `11.8`, `12.3` | None | `13.0` | `10.11`, `11.4` |
| Percona Server | `8.0` (CI target) | None | None | `8.0` |

## Required Database Privileges

| Engine / Version | Required Privileges |
| :--- | :--- |
| MySQL 8.0+ | `SELECT, PROCESS, SHOW DATABASES, EXECUTE, REPLICATION REPLICA, REPLICATION CLIENT, SHOW VIEW` |
| MariaDB 10.5+ | `SELECT, PROCESS, SHOW DATABASES, EXECUTE, BINLOG MONITOR, SHOW VIEW, REPLICATION SOURCE ADMIN, REPLICA MONITOR` |
| Legacy MySQL / MariaDB | `SELECT, PROCESS, EXECUTE, REPLICATION CLIENT, SHOW DATABASES, SHOW VIEW` |

## Runtime Requirements

| Requirement | Minimum | Notes |
| :--- | :--- | :--- |
| Perl Interpreter | `5.005`+ (`5.8`+ recommended) | Uses Perl Core modules only; zero CPAN dependencies |
| Database Uptime | `>= 24` hours (`86400` seconds) | Below 24 hours triggers inaccurate-recommendation notice |
| Architecture | 64-bit recommended | 32-bit OS with `> 2 GB` RAM raises instability warning |

## MySQL Lifecycle Matrix

[mysql_support.md](https://github.com/major/MySQLTuner-perl/blob/master/mysql_support.md)

<!-- INCLUDE_SOURCE: mysql_support.md -->

## MariaDB Lifecycle Matrix

[mariadb_support.md](https://github.com/major/MySQLTuner-perl/blob/master/mariadb_support.md)

<!-- INCLUDE_SOURCE: mariadb_support.md -->

## Related Documentation

- CLI flags and execution modes:
  [CLI Options and Environment](../cli-and-scripts/cli-options.md)
- Version divergence analysis:
  [Health Score and Version Rift](../../04-explanation/deep-dives/health-score-and-version-rift.md)
