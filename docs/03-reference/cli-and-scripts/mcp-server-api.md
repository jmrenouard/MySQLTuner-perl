# MCP Server and Agent JSON API

Protocol, tool schemas, resource URIs, safety guardrails, and `--agent-json` output contract for AI integrations.

## MCP Server Specification (`build/mcp_server.py`)

| Attribute | Value | Notes |
| :--- | :--- | :--- |
| Server Name | `mysqltuner-mcp` | Zero external dependencies (Python 3 stdlib only) |
| Server Version | `2.9.4` | Synchronized with `mysqltuner.pl` |
| Protocol Version | `2024-11-05` | JSON-RPC `2.0` (`initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`) |
| Stdio Transport | Default mode | Reads line-delimited JSON-RPC on `stdin`, emits responses on `stdout` |
| SSE HTTP Transport | `--sse` (`--host`, `--port`) | Defaults `127.0.0.1:8000`; endpoints `GET /sse`, `POST /message`, `GET /health` |
| Daemon Mode | `--daemon` | Runs periodic `mysqltuner.pl --prettyjson --reportfile` loop without RPC server |
| SSE Auth Guard | `MCP_AUTH_TOKEN` Bearer token | When unset in `--sse` mode, `READ_ONLY` is forced to `true` automatically |

### MCP Server Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `CACHE_DIR` | `/var/cache/mysqltuner` | Stores `latest.json`, `latest.html`, and `state.json` transaction ledger |
| `AUDIT_INTERVAL_HOURS` | `12` | Interval in hours between background `run_mysqltuner_cmd()` cycles |
| `READ_ONLY` | `false` | Blocks `apply_recommendation` and `rollback_recommendation` when `true`/`1`/`yes` |
| `MYSQLTUNER_PL` | `mysqltuner.pl` | Path to `mysqltuner.pl` binary |
| `DB_HOST` / `DB_PORT` | unset | Optional target database host and port passed to CLI and `mysql` client |
| `DB_USER` / `DB_PASSWORD` | unset | Optional database credentials passed to CLI and `mysql` client |
| `MCP_AUTH_TOKEN` | unset | Optional HTTP `Authorization: Bearer <token>` secret for `--sse` mode |

## Exposed MCP Resources

| Resource URI | Name | MIME Type | Backing File |
| :--- | :--- | :--- | :--- |
| `mysqltuner://reports/latest.json` | Latest JSON report | `application/json` | `$CACHE_DIR/latest.json` |
| `mysqltuner://reports/latest.html` | Latest HTML dashboard | `text/html` | `$CACHE_DIR/latest.html` |

## Exposed MCP Tools

| Tool Name | Parameters (`inputSchema`) | Mutates State | Behavior and Safety Guardrails |
| :--- | :--- | :--- | :--- |
| `get_latest_audit` | None (`additionalProperties: false`) | No | Reads `$CACHE_DIR/latest.json` without querying DB |
| `run_audit` | None (`additionalProperties: false`) | Updates cache | Executes `mysqltuner.pl --prettyjson --reportfile` atomically |
| `analyze_buffer_pool` | `target_ram_percentage` (number, `75`), `include_dirty_pages` (boolean, `true`) | No | Queries live InnoDB status/vars and host/cgroup RAM; fails closed on SQL error |
| `diagnose_replication_lag` | `max_acceptable_lag_seconds` (int, `30`), `channel_name` (string, `""`) | No | Runs `SHOW REPLICA STATUS` / `SHOW SLAVE STATUS`; validates channel regex `^[A-Za-z0-9_-]{1,64}$` |
| `detect_fragmented_tables` | `min_fragmentation_pct` (`20`), `min_table_size_mb` (`10`), `schema_filter` (`""`) | No | Scans `information_schema.TABLES` (top 100); flags tables `>= 5 GB` as `is_high_impact` |
| `apply_recommendation` | `statement` (string, required), `variable_name` (string, optional) | Yes (DB + ledger) | Blocked if `READ_ONLY`; enforces SQL allowlist/blocklist; snapshots `@@global.<var>` |
| `rollback_recommendation` | `statement_id` (string, required) | Yes (DB + ledger) | Blocked if `READ_ONLY`; restores prior `SET GLOBAL <var> = <old_value>` from `state.json` |

### SQL Sanitizer Rules (`sanitize_sql_statement`)

- Strips `--`, `#`, and `/* ... */` comments; rejects unclosed `/*` comments and multiple statements (`;`).
- Rejects destructive SQL keywords: `DROP`, `DELETE`, `TRUNCATE`, `INSERT`, `UPDATE`, `GRANT`, `REVOKE`, `CREATE`,
  `REPLACE`, `EXECUTE`, `CALL`, `LOAD_FILE`, `LOAD DATA`, `INTO OUTFILE`, `INTO DUMPFILE`, `SHUTDOWN`, `KILL`, and
  `FLUSH PRIVILEGES`.
- Requires statement to start with one of: `SET GLOBAL`, `SET @@GLOBAL.`, `SET PERSIST`, `ALTER TABLE`,
  `OPTIMIZE TABLE`, or `ANALYZE TABLE` (followed by whitespace for non-dot prefixes).

## `--agent-json` Output Contract (`mysqltuner.pl`)

Executing `perl mysqltuner.pl --agent-json` emits a single JSON object `{ "findings": [...] }` generated from `@adjvars`
while excluding dot-delimited sysctl or Galera keys.

### Finding Object Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | string | Deterministic identifier (`<var>_adjust`, `<var>_enable`, or `query_cache_size_disable`) |
| `topic` | string | Domain category (`Performance`, `Security`, or `Reliability`) |
| `description` | string | Human-readable summary of the detected configuration gap |
| `impact_score` | integer | Priority weight on a `1` to `10` scale |
| `risk_level` | string | Operational risk classification (`Low`, `Medium`, or `High`) |
| `risk_description` | string | Operational caveat before applying the change |
| `requires_restart` | boolean | `true` when variable is static (`Config`), `false` when dynamically mutable (`SQL`) |
| `expected_outcome` | string | Expected workload or reliability improvement |
| `action.type` | string | `SQL` (dynamic `SET GLOBAL`) or `Config` (`my.cnf` key-value directive) |
| `action.statement` | string | Executable `SET GLOBAL <var> = <val>;` or config line `<var> = <val>` |
| `action.rollback_statement` | string | Exact revert `SET GLOBAL` or config line using pre-audit `$myvar{<var>}` |

### Variable Risk, Impact, and Rollback Matrix

| Variable | Finding ID | Topic | Impact | Risk Level | `requires_restart` | Action Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `innodb_buffer_pool_size` | `innodb_buffer_pool_size_adjust` | `Performance` | `9` | `Medium` | `false` | `SQL` |
| `performance_schema` | `performance_schema_enable` | `Performance` | `8` | `Medium` | `true` | `Config` |
| `innodb_file_per_table` | `innodb_file_per_table_enable` | `Performance` | `8` | `Low` | `true` | `Config` |
| `innodb_log_file_size` | `innodb_log_file_size_adjust` | `Performance` | `8` | `High` | `true` | `Config` |
| `query_cache_size` | `query_cache_size_disable` | `Performance` | `8` | `Low` | `false` | `SQL` |
| `skip-name-resolve` / `skip_name_resolve` | `skip_name_resolve_enable` | `Security` | `7` | `Medium` | `true` | `Config` |
| `innodb_buffer_pool_instances` | `innodb_buffer_pool_instances_adjust` | `Performance` | `7` | `Medium` | `true` | `Config` |
| `lower_case_table_names` | `lower_case_table_names_adjust` | `Reliability` | `7` | `High` | `true` | `Config` |
| `max_connections` | `max_connections_adjust` | `Reliability` | `7` | `Medium` | `false` | `SQL` |
| `long_query_time` | `long_query_time_adjust` | `Performance` | `6` | `Low` | `false` | `SQL` |
| Static vars (`innodb_page_size`, `ft_min_word_len`) | `<var>_adjust` | `Performance` | `5` | `Low` | `true` | `Config` |
| All other dynamic `@adjvars` | `<var>_adjust` | `Performance` | `5` | `Low` | `false` | `SQL` |

## Related Documentation

- AI agent subsystem design:
  [AI Agent Architecture](../../04-explanation/architecture-overview/ai-agent-architecture.md)
- Guided MCP sandbox lab: [AI and MCP Sandbox Lab](../../01-tutorials/02-ai-mcp-sandbox-lab.md)
