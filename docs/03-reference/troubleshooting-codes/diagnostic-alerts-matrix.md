# Diagnostic Alerts Matrix

Mapping of MySQLTuner findings, status indicators, and audit alerts to
thresholds and operational runbooks.

## Performance and InnoDB Alerts

| Diagnostic Message / Signal | Trigger Threshold | Severity | Remediation Runbook |
| :--- | :--- | :--- | :--- |
| `InnoDB buffer pool / data size: X / Y` | `innodb_buffer_pool_size <=` InnoDB data + index bytes | `WARN` / `REC` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |
| `InnoDB Read buffer efficiency: < 90%` | `pct_read_efficiency < 90%` | `WARN` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |
| `Innodb_buffer_pool_size not aligned with ...` | `bp_size % (chunk_size * instances) != 0` | `WARN` / `REC` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |
| `InnoDB buffer pool instances` mismatch | `instances != floor(bp_size / 1G)` (capped at CPU cores and `64`) | `WARN` / `REC` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |
| `InnoDB Adaptive Hash Index (AHI) has low search hit ratio` | Hit ratio `< 15.0%` (`> 50,000` searches) or `ahi_parts == 1` | `WARN` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |
| `table_definition_cache is >= 90% full` | Fill `>= 90%`, open rate `> 5.0/s`, opened `> 2x` capacity | `WARN` | [Tune InnoDB Buffer Pool](../../02-how-to-guides/operations/tune-innodb-buffer-pool.md) |

## Replication and High-Availability Alerts

| Diagnostic Message / Signal | Trigger Threshold | Severity | Remediation Runbook |
| :--- | :--- | :--- | :--- |
| `This replication replica is not running but seems to be configured.` | `Replica_IO_Running` or `Replica_SQL_Running` `!= YES` | `WARN` | [Diagnose Replication Lag](../../02-how-to-guides/incident-response/diagnose-replication-lag.md) |
| `This replication replica is lagging and has N second(s) behind source host.` | `Seconds_Behind_Replica > 0` (`>= 60s` scores `0/10` resilience) | `WARN` | [Diagnose Replication Lag](../../02-how-to-guides/incident-response/diagnose-replication-lag.md) |
| `This replication replica has unknown lag` | `Seconds_Behind_Replica` is `NULL` or non-numeric | `WARN` | [Diagnose Replication Lag](../../02-how-to-guides/incident-response/diagnose-replication-lag.md) |
| `Parallel replication is disabled.` | MariaDB `slave_parallel_threads` / `replica_parallel_threads <= 1` | `WARN` / `REC` | [Diagnose Replication Lag](../../02-how-to-guides/incident-response/diagnose-replication-lag.md) |
| `This replication replica is running with the read_only option disabled.` | `read_only = OFF` on active replica | `WARN` | [Diagnose Replication Lag](../../02-how-to-guides/incident-response/diagnose-replication-lag.md) |

## Security, TLS, and Authentication Alerts

| Diagnostic Message / Signal | Trigger Threshold | Severity | Remediation Runbook |
| :--- | :--- | :--- | :--- |
| `Current connection is NOT encrypted!` | Session `Ssl_cipher` empty, `NULL`, or `0` | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |
| `SSL is DISABLED on the server.` | `get_server_tls_status() == 0` | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |
| `require_secure_transport is OFF` | `require_secure_transport = OFF` on non-localhost server | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |
| `Insecure TLS versions enabled` / `Weak or vulnerable SSL cipher(s)` | `TLSv1`/`TLSv1.0`/`TLSv1.1` or `RC4`/`DES`/`3DES`/`MD5`/`NULL`/`ADH` | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |
| `User ... uses DEPRECATED/INSECURE plugin` | `mysql_old_password`, `mysql_native_password`, or `sha256_password` | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |
| `User ... is using a weak password` / anonymous / `@'%'` | Match in `basic_passwords.txt`, empty `USER`, or wildcard host | `WARN` / `REC` | [Audit TLS and Authentication Plugins](../../02-how-to-guides/security/audit-tls-and-auth-plugins.md) |

## Container, Remote Host, and Documentation Alerts

| Diagnostic Message / Signal | Trigger Threshold | Severity | Remediation Runbook |
| :--- | :--- | :--- | :--- |
| `Physical Memory (RAM) : Unknown (Use --forcemem to specify)` | Remote TCP/IP audit without `--ssh-host` or `--forcemem` | `INFO` / `WARN` | [Run Remote and Container Audits](../../02-how-to-guides/deployment/run-remote-and-container-audit.md) |
| `Skipping host network, process, filesystem, and kernel probes in container mode.` | `is_docker()` or `--container` active; caps RAM via cgroup v1/v2 | `INFO` | [Run Remote and Container Audits](../../02-how-to-guides/deployment/run-remote-and-container-audit.md) |
| `sshpass is not installed. Password authentication for SSH will not work.` | `--ssh-password` specified without `sshpass` in `$PATH` | `WARN` | [Run Remote and Container Audits](../../02-how-to-guides/deployment/run-remote-and-container-audit.md) |
| `There is less than 1,5 Gb of RAM` | Host or cgroup memory `< 1.5 GB` | `WARN` / `REC` | [Run Remote and Container Audits](../../02-how-to-guides/deployment/run-remote-and-container-audit.md) |
| MkDocs / `mike` / Docs validation failure | Broken relative links, procedural errors, or missing `versions.json` | `WARN` / `ERROR` | [Publish Versioned Documentation](../../02-how-to-guides/deployment/publish-versioned-docs.md) |

## Related Documentation

- Threshold details and data files:
  [Thresholds and Data Files](../configuration/thresholds-and-files.md)
- CLI transport options:
  [CLI Options and Environment](../cli-and-scripts/cli-options.md)
