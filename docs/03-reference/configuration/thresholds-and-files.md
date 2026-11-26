# Thresholds and External Data Files

Reference catalog of external data/credential files, diagnostic alert
thresholds, and the upstream security policy.

## External Data and Credential Files

| File / Path | Format | Default Lookup Order | Override / Flag | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `basic_passwords.txt` | Plain text (`620` tokens) | `<script_dir>/basic_passwords.txt`, then `/usr/share/mysqltuner/basic_passwords.txt` | `--passwordfile` / `--skippassword` | Dictionary for offline SHA-1 and fallback password strength checks |
| `vulnerabilities.csv` | Semicolon CSV (`1966` rows) | `./vulnerabilities.csv`, then `/usr/share/mysqltuner/vulnerabilities.csv` | `--cvefile` | Matches `version` (`major;minor;micro`) against known CVEs |
| `~/.my.cnf` | INI (`[client]`, mode `0600`) | `$HOME/.my.cnf` (`USERPROFILE` / `*_HOME` on Windows) | `--defaults-file` / `--defaults-extra-file` | Unattended client authentication credentials |
| `~/.mylogin.cnf` | Encrypted (`mysql_config_editor`) | `$HOME/.mylogin.cnf` | `--login-path` | Encrypted local client authentication profiles |
| `/etc/mysql/debian.cnf` | INI (`debian-sys-maint`) | Local Linux hosts only (`$doremote == 0`) | Explicit `--defaults-file` or `--login-path` | Debian/Ubuntu local maintenance login fallback |
| `/etc/psa/.psa.shadow` | Plain text | Local Plesk hosts (`$doremote == 0`) | Explicit CLI credentials | Plesk admin account login fallback |
| `/usr/local/directadmin/conf/mysql.conf` | Key-value (`user=`, `passwd=`) | Local DirectAdmin hosts (`$doremote == 0`) | Explicit CLI credentials | DirectAdmin credential fallback (see Issue #289 caveat) |
| `$TMP/.mysqltuner_<host>_<port>` | `uptime:failed_attempts` (`0600`) | `$TEMP`, `$TMP`, or `/tmp` | None (symlink-protected, atomic rename) | Subtracts MySQLTuner password-probe failures from `Aborted_connects` |

## Key Diagnostic Thresholds

### Connections, Memory, and Query Execution

| Indicator | Warning Condition | Optimal Target | Source Subroutine |
| :--- | :--- | :--- | :--- |
| Server Uptime | `< 86400` s (`< 24` hours) | `>= 86400` s | `mysql_stats` |
| Max Used Memory | `> 85%` of physical RAM (or `> 2 GB` on 32-bit OS) | `<= 85%` of physical RAM | `mysql_stats` |
| Max Peak Memory | `> 85%` of physical RAM | `<= 85%` of physical RAM | `mysql_stats` |
| Non-MySQL Process Memory | `> 15%` of physical RAM (ignored with `--nondedicated`) | `<= 15%` of physical RAM | `system_recommendations` |
| Slow Queries Ratio | `> 5%` of total `Questions`; `long_query_time > 10` | `<= 5%`; `long_query_time <= 10` | `mysql_stats` |
| Connection Usage | `> 85%` (`Max_used_connections / max_connections`) | `<= 85%` (`< 80%` for full Health Score) | `mysql_stats` |
| Aborted Connections | `> 3%` (`Aborted_connects / Connections`) | `<= 3%` | `mysql_stats` |
| Sorts Requiring Temp Tables | `> 10%` (`Sort_merge_passes / total_sorts`) | `<= 10%` | `mysql_stats` |
| Joins Without Indexes | `> 250` per day | `<= 250` per day | `mysql_stats` |
| Temp Tables Created on Disk | `> 25%` (`Created_tmp_disk_tables / Created_tmp_tables`) | `<= 25%` (`< 10%` for full Health Score) | `mysql_stats` |
| Thread Cache Hit Rate | `<= 50%` or `thread_cache_size == 0` | `> 50%` (`> 90%` for full Health Score) | `mysql_stats` |
| Table Cache Hit Rate | `< 20%` (`Table_open_cache_hits` or open ratio) | `>= 20%` | `mysql_stats` |
| Table Definition Cache | Fill `>= 90%`, open rate `> 5.0/s`, opened `> 2x` capacity | Suggests `>= 1.5x` (min `2000`) | `audit_table_definition_cache` |

### InnoDB, Performance Schema, and Storage

| Indicator | Warning Condition | Optimal Target | Source Subroutine |
| :--- | :--- | :--- | :--- |
| InnoDB Buffer Pool Size | `<` InnoDB data + index size (or `> 4 GB` on 32-bit OS) | `>=` InnoDB data + index size (~75-80% RAM) | `mysql_innodb` |
| InnoDB Buffer Pool Instances | `!= floor(size / 1 GB)` (capped by CPU cores and `64`) | `1` per GB (`<= 64`, `1` when `<= 1 GB`) | `mysql_innodb` |
| InnoDB Read / Write Efficiency | `< 90%` (`pct_read_efficiency` or `pct_write_efficiency` + waits) | `> 99%` read (`> 90%` write) | `mysql_innodb` |
| InnoDB Redo Log Ratio (`< 8.0.30`) | `< 20%` or `> 30%` of `innodb_buffer_pool_size` | `25%` of `innodb_buffer_pool_size` | `mysql_innodb` |
| InnoDB AHI Hit Ratio | `< 15.0%` (when total searches `> 50,000`), or `parts == 1` with multi-instance BP | `>= 15.0%` or disable AHI; match `bp_instances` | `audit_innodb_ahi` |
| PFS Stage Profiling | Tmp table `> 1000` & `> 5000 ms`; Sort `> 5000` & `> 10000 ms` | Below thresholds | `audit_pfs_stage_profiling` |
| PFS Wait Contention | InnoDB mutex `> 10000 ms`; Data file I/O `> 50000 ms` | Below thresholds | `audit_pfs_stage_profiling` |
| Fragmented Tables | `DATA_LENGTH > 100 MB` and `DATA_FREE > 10%` of total | `< 10%` fragmentation | `check_storage_engines` |

### Security, TLS, Replication, and Kernel

| Indicator | Warning Condition | Optimal Target | Source Subroutine |
| :--- | :--- | :--- | :--- |
| Error Log Size | `> 32 MB` | `<= 32 MB` (rotated) | `log_file_recommendations` |
| Weak Password Dictionary Limit | Stops after `--max-password-checks` (`100` default) | Zero dictionary matches | `security_recommendations` |
| TLS Protocols and Ciphers | `TLSv1`, `TLSv1.0`, `TLSv1.1`, or `RC4/DES/3DES/MD5/EXPORT/NULL/ADH` | `TLSv1.2,TLSv1.3` with AEAD/GCM | `ssl_tls_recommendations`, `audit_tls_ciphers_protocols` |
| Authentication Plugins | `mysql_old_password`, `mysql_native_password`, or `sha256_password` | `caching_sha2_password`, `ed25519`, `parsec`, `unix_socket` | `check_auth_plugins` |
| Replication Threads and Lag | `IO`/`SQL` thread `!= YES` or `Seconds_Behind_* > 0` (`>= 60s` scores `0`) | Both `YES`, lag `0s` (`read_only=ON` on replica) | `get_replication_status` |
| Galera Flow Control | `wsrep_flow_control_paused >= 0.02`, even node count, or non-PK tables | `< 0.02`, `3` or `5` nodes, `innodb_flush_log_at_trx_commit` tuned | `mariadb_galera` |
| Linux Kernel Sysctls | `vm.swappiness > 10`, `fs.aio-max-nr < 1000000`, `fs.nr_open < 1000000`, `sunrpc.tcp_slot_table_entries < 100` | `swappiness <= 10`, `aio-max-nr >= 1048576`, `nr_open >= 1048576` | `get_kernel_info` |

## Upstream Security Policy

[SECURITY.md](https://github.com/major/MySQLTuner-perl/blob/master/SECURITY.md)

<!-- INCLUDE_SOURCE: SECURITY.md -->

## Related Documentation

- Finding-to-runbook mapping:
  [Diagnostic Alerts Matrix](../troubleshooting-codes/diagnostic-alerts-matrix.md)
- TLS and auth audit procedure:
  [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md)
