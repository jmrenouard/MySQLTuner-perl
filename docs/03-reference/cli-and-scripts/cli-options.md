# CLI Options and Environment Variables

Command-line contract, process exit codes, environment variables, and complete manual for `mysqltuner.pl`.

## Process Exit Codes

| Exit Code | Trigger Condition | Source Location |
| :--- | :--- | :--- |
| `0` | Normal diagnostic completion, `--help`, `--list-indicators`, or `--agent-json` export | `setup_environment`, `dump_result`, `MAIN` |
| `1` | Invalid CLI flag/value, positional argument, unknown `--feature`, mutually exclusive `--json --yaml`, or fatal DB login/privilege failure | `parse_cli_args`, `mysql_setup`, `get_all_vars`, `dump_result` |
| `2` | Target server answered zero queries (`Questions < 1`) | `calculations()` |
| `> 0` (Perl `die`) | Unwritable `--outputfile`/`--reportfile`, unreadable `--cvefile`, or directory creation error (`--dumpdir`/`--schemadir`) | `setup_environment`, `cve_recommendations`, `dump_csv_files` |

## Environment Variables

### Runtime Variables (`mysqltuner.pl`)

| Variable | Default | Scope | Purpose |
| :--- | :--- | :--- | :--- |
| `MYSQLTUNER_PROC_MEMINFO` | `/proc/meminfo` | Linux `os_setup()` | Overrides memory/swap procfs source for hermetic or simulated runs |
| `MYSQLTUNER_CGROUP_DIR` | `/sys/fs/cgroup` | Container memory detection | Overrides cgroup v1/v2 directory for container RAM/swap limits |
| `MYSQLTUNER_SYS_BLOCK_DIR` | `/sys/block` | Infrastructure detection | Overrides block device rotational probe path (`SSD`/`NVMe` vs `HDD`) |
| `container` | unset | Container detection | Recognized values `docker`, `podman`, or `lxc` trigger container mode |
| `MYSQL_PWD` | unset | MySQL/MariaDB client | Client password fallback respected by `mysql`/`mariadb` subprocesses |
| `MARIADB_ROOT_PASSWORD` / `MYSQL_ROOT_PASSWORD` | unset | Container env fallback | Fallback root credentials when `--pass` is omitted in container environments |
| `HOME` / `MARIADB_HOME` / `MYSQL_HOME` / `USERPROFILE` | OS user home | Credential discovery | Locates `.my.cnf` and `.mylogin.cnf` (`USERPROFILE` / `*_HOME` on Windows) |
| `TEMP` / `TMP` | `/tmp` | State file storage | Base directory for atomic `.mysqltuner_<host>_<port>` aborted-connects state |
| `<custom>` (`--userenv` / `--passenv`) | unset | CLI authentication | Reads DB username or password from user-named environment variable |

### Toolchain and Test Variables (`build/` and `tests/`)

| Variable | Default | Consumer Script | Purpose |
| :--- | :--- | :--- | :--- |
| `MYSQLTUNER_DOCS_DIR` | `documentation/` | `build/check_doc_links.pl` | Overrides legacy documentation directory during link audits |
| `MYSQLTUNER_SPEC_DIR` | `documentation/specifications` | `build/audit_specifications.pl` | Overrides specification directory during compliance audits |
| `MYSQLTUNER_QA_FILE` | `documentation/QUALITY_AND_TESTING.md` | `build/audit_specifications.pl` | Overrides QA traceability matrix file path |
| `MYSQLTUNER_README_DIR` | repository root | `tests/readme_translations_sync.t` | Overrides multilingual README directory for isolated translation tests |
| `MYSQLTUNER_SCRIPT_PATH` | `mysqltuner.pl` | `tests/pod_cli_sync.t` | Overrides script path for POD/CLI parity tests |
| `MYSQLTUNER_STRICT_ALL` | unset (`0`) | `build/audit_specifications.pl` | Escalates specification audit warnings to fatal failures |
| `MYSQLTUNER_PL` | `mysqltuner.pl` | `build/mcp_server.py` | Path to `mysqltuner.pl` executed by MCP `run_audit` and daemon loop |
| `GEN_HISTORICAL` | unset (`0`) | `build/release_gen.pl` | Allows regenerating historical release notes without live script metrics |

## Upstream POD Manual (`USAGE.md`)

<!-- INCLUDE_SOURCE: USAGE.md -->

## Related Documentation

- Execution lifecycle and transport design:
  [Diagnostic Pipeline](../../04-explanation/architecture-overview/diagnostic-pipeline.md)
- Container and SSH invocation procedures:
  [Run Remote and Container Audits](../../02-how-to-guides/deployment/run-remote-and-container-audit.md)
