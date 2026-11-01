#!/usr/bin/env bash
# ==============================================================================
# Script:      documentation/create_github_issues.sh
# Description: Automated GitHub issue creator for MySQLTuner Ponytail audit remediation
#              Issues 1 through 17 on major/MySQLTuner-perl assigned to jmrenouard.
# Author:      Jean-Marie Renouard / Antigravity
# Usage:       chmod +x documentation/create_github_issues.sh
#              ./documentation/create_github_issues.sh
# ==============================================================================

set -uo pipefail

REPO="major/MySQLTuner-perl"
ASSIGNEE="jmrenouard"

echo "=== MySQLTuner GitHub Issue Creation Orchestrator ==="
echo "Target Repository : ${REPO}"
echo "Assignee          : ${ASSIGNEE}"
echo "Total Issues      : 17"
echo ""

# Check gh CLI availability
if ! command -v gh &>/dev/null; then
    echo "ERROR: 'gh' CLI tool is not installed or not in PATH." >&2
    exit 1
fi

# Optional token sanitization if HTTP 401 is encountered
# unset GITHUB_TOKEN GH_TOKEN

create_issue() {
    local num="$1"
    local title="$2"
    local label="$3"
    local body="$4"

    echo "------------------------------------------------------------------------"
    echo "Creating Issue #${num}: ${title}"

    # First attempt: Create issue with primary label and assignee
    local result
    if result=$(gh issue create \
        --repo "${REPO}" \
        --title "${title}" \
        --assignee "${ASSIGNEE}" \
        --label "${label}" \
        --body "${body}" 2>&1); then
        echo "  [SUCCESS] Created: ${result}"
        return 0
    fi

    # Fallback attempt 1: Try without assignee if assignment fails
    echo "  [RETRY] Attempting creation without explicit assignee..."
    if result=$(gh issue create \
        --repo "${REPO}" \
        --title "${title}" \
        --label "${label}" \
        --body "${body}" 2>&1); then
        echo "  [SUCCESS] Created: ${result}"
        return 0
    fi

    # Fallback attempt 2: Try without label if label is unassigned on upstream
    echo "  [RETRY] Attempting creation without label..."
    if result=$(gh issue create \
        --repo "${REPO}" \
        --title "${title}" \
        --body "${body}" 2>&1); then
        echo "  [SUCCESS] Created: ${result}"
        return 0
    fi

    echo "  [FAILED] Could not create Issue #${num}: ${result}" >&2
    return 1
}

# ==============================================================================
# Issue 1: Remove Silent Mutation in check_metadata_perf
# ==============================================================================
BODY_1=$(cat <<'EOF'
### Problem / Root Cause
In `check_metadata_perf` (line 14358 in `mysqltuner.pl`), MySQLTuner was executing:
```perl
select_one("SET GLOBAL innodb_stats_on_metadata = OFF;");
```
This was a silent mutation of production database state during diagnostic analysis. MySQLTuner must operate strictly as a read-only auditing tool and never alter global variables without operator opt-in.

### Surgical Fix
- Removed the `select_one("SET GLOBAL innodb_stats_on_metadata = OFF;");` execution from `check_metadata_perf`.
- Preserved the tuning recommendation in `@adjvars` (`innodb_stats_on_metadata=OFF`) so that administrators can review and apply the adjustment deliberately.

### Verification
Validated via dedicated unit test `tests/unit_m1_sql_security.t` asserting no SQL mutation statements are executed.
EOF
)
create_issue 1 "fix(sql): remove silent mutation SET GLOBAL innodb_stats_on_metadata in check_metadata_perf" "bug" "${BODY_1}"

# ==============================================================================
# Issue 2: Shell & SQL Metacharacter Escaping
# ==============================================================================
BODY_2=$(cat <<'EOF'
### Problem / Root Cause
1. In `select_one` (lines 4689-4712), queries passed through the shell without escaping double quotes (`"`), backticks (``` ` ```), and dollar signs (`$`), in contrast to `select_array` which escaped them.
2. In `mysql_setup` and `log_file_recommendations`, user inputs (`$opt{user}`, `$logfile`, and `$myvar{'log_error'}`) were interpolated into shell execution strings without single-quote escaping (`s/'/'\\''/g`), allowing shell argument injection if quotes were contained in usernames or log paths.

### Surgical Fix
- Added metacharacter escaping in `select_one`:
  ```perl
  $query =~ s/"/\\"/g;
  $query =~ s/`/\\`/g;
  $query =~ s/\$/\\\$/g;
  ```
- Applied single-quote escaping `s/'/'\\''/g` on `$opt{user}`, `$logfile`, and `$myvar{'log_error'}` before constructing shell commands.

### Verification
Validated with unit tests in `tests/unit_m1_sql_security.t`.
EOF
)
create_issue 2 "fix(security): escape shell and SQL metacharacters in select_one and credential options" "bug" "${BODY_2}"

# ==============================================================================
# Issue 3: Process Telemetry & --noprocess
# ==============================================================================
BODY_3=$(cat <<'EOF'
### Problem / Root Cause
1. In `setup_environment` (lines 800-801), `$opt{noprocess}` was unconditionally reset to 0, ignoring the user CLI flag.
2. In `get_other_process_memory` (lines 5758-5794), the subroutine did not check if `$opt{noprocess}` was enabled before spawning `ps`.
3. The process filtering regex `next if $command =~ /mysqld/i;` failed to exclude `mariadbd` (MariaDB 10.5+) and `garbd` (Galera Arbitrator Daemon), incorrectly attributing MariaDB server memory to third-party non-database processes.

### Surgical Fix
- Preserved `$opt{noprocess}` in `setup_environment`.
- Added `return 0 if $opt{noprocess};` in `get_other_process_memory`.
- Updated the regex to `next if $command =~ /(?:mysqld|mariadbd|garbd)/i;`.

### Verification
Validated with unit test `tests/unit_m2_process_swap.t`.
EOF
)
create_issue 3 "fix(telemetry): respect --noprocess flag and exclude mariadbd and garbd in process memory" "bug" "${BODY_3}"

# ==============================================================================
# Issue 4: Windows Swap Telemetry & Zero Swap Handling
# ==============================================================================
BODY_4=$(cat <<'EOF'
### Problem / Root Cause
1. In `os_setup` (lines 3530-3553), Windows CIM/WMI metric `FreeVirtualMemory` is returned in kilobytes, but was treated as raw bytes, distorting swap memory calculations by a factor of 1024.
2. Systems where swap is explicitly disabled (`swap == 0`) triggered a false fatal exit (`memerror`) because the check evaluated truthiness `if ($swap_memory)` instead of checking if it is a defined numeric value.

### Surgical Fix
- Scaled `FreeVirtualMemory` by multiplying by 1024:
  ```perl
  $swap_memory = $swap_memory * 1024;
  ```
- Updated swap validity guard to:
  ```perl
  if ( defined($swap_memory) && $swap_memory =~ /^\d+$/ ) { ... }
  ```

### Verification
Validated with unit test `tests/unit_m2_process_swap.t` and regression test `tests/unit_windows_metrics.t`.
EOF
)
create_issue 4 "fix(system): scale Windows FreeVirtualMemory to bytes and handle zero swap safely" "bug" "${BODY_4}"

# ==============================================================================
# Issue 5: InnoDB Buffer Pool Sizing & Custom Page Size
# ==============================================================================
BODY_5=$(cat <<'EOF'
### Problem / Root Cause
In `mysql_innodb` (lines 12759-12766), raw page counts (`Innodb_buffer_pool_pages_total`, `Innodb_buffer_pool_pages_free`, `Innodb_buffer_pool_pages_data`) were formatted using `hr_bytes()`, assuming raw numbers were bytes or hardcoding 16KB. When custom `innodb_page_size` (4KB, 8KB, 32KB, 64KB) was configured, the reported buffer pool sizes were severely corrupted. In addition, used buffer pool bytes was miscalculated.

### Surgical Fix
- Scaled page counts by `($myvar{'innodb_page_size'} // 16384)` before calling `hr_bytes()`.
- Computed used buffer pool bytes as `(Innodb_buffer_pool_pages_total - Innodb_buffer_pool_pages_free) * page_size`, clamped to 0 on underflow.

### Verification
Validated with unit test `tests/unit_m3_innodb_buffer_pool.t`.
EOF
)
create_issue 5 "fix(engine): compute InnoDB buffer pool page memory using innodb_page_size" "bug" "${BODY_5}"

# ==============================================================================
# Issue 6: Auto-Fix Snippets & Agent JSON Read-Only Filtering
# ==============================================================================
BODY_6=$(cat <<'EOF'
### Problem / Root Cause
In `generate_auto_fix_snippets` (lines 2265-2298) and `dump_result` (`--agent-json`, lines 15311-15455), read-only variables, sysctl dot keys (`/\./`), and static variables requiring server restart (`innodb_log_file_size`, `innodb_buffer_pool_instances`, `lower_case_table_names`, `skip-name-resolve`, `performance_schema`, `innodb_file_per_table`) were generated as `SET GLOBAL` statements, causing SQL errors when applied. Furthermore, target values containing comments (e.g. `10 # comment`) produced invalid SQL syntax.

### Surgical Fix
- Excluded read-only, dot keys, and static variables from dynamic `SET GLOBAL` generation, outputting them as `# my.cnf:` configuration comments instead.
- Implemented `clean_tuning_value` to strip trailing comments and whitespace from target adjustment values.
- Classified variables requiring restart properly in `--agent-json` output (`restart_required: true`).

### Verification
Validated with unit test `tests/unit_m4_autofix_agent_json.t`.
EOF
)
create_issue 6 "fix(autofix): exclude read-only, dot keys, and static variables from dynamic SET GLOBAL" "bug" "${BODY_6}"

# ==============================================================================
# Issue 7: Windows getpwuid Crash Guard
# ==============================================================================
BODY_7=$(cat <<'EOF'
### Problem / Root Cause
In `setup_environment` (line 845), invoking `getpwuid($<)` on Windows systems causes fatal runtime errors or Perl crashes because Windows environments do not implement POSIX user databases.

### Surgical Fix
- Protected user ID resolution:
  ```perl
  $me = ( !$is_win ? eval { ( getpwuid($<) )[0] } : undef ) // $ENV{USER} // $ENV{USERNAME} // 'unknown';
  ```

### Verification
Validated with unit test `tests/unit_m2_env_windows_update.t`.
EOF
)
create_issue 7 "fix(system): guard getpwuid call on Windows platforms in setup_environment" "bug" "${BODY_7}"

# ==============================================================================
# Issue 8: Query Preloading & Engine Deduplication
# ==============================================================================
BODY_8=$(cat <<'EOF'
### Problem / Root Cause
1. In `mysql_80_modeling_checks` (lines 11748-11769), MySQLTuner queried generated columns on a per-table basis, resulting in N database roundtrips.
2. In `mysql_databases` (lines 14481-14637), `SELECT DISTINCT(ENGINE)` was executed twice consecutively.

### Surgical Fix
- Preloaded virtual/generated column tables in a single query against `information_schema.columns`.
- Cached `@engines` and reused the array to eliminate redundant query execution.

### Verification
Validated with unit test `tests/unit_m3_query_dedup_caching.t`.
EOF
)
create_issue 8 "perf(query): preload virtual column tables and deduplicate engine queries" "enhancement" "${BODY_8}"

# ==============================================================================
# Issue 9: PFS & GCache Memory Result Caching
# ==============================================================================
BODY_9=$(cat <<'EOF'
### Problem / Root Cause
In `mysql_stats` (lines 8757-8765) and `mysql_pfs` (lines 9733-9744), helper functions `get_pf_memory()` and `get_gcache_memory()` were called repeatedly, each triggering redundant queries against Performance Schema memory summary tables.

### Surgical Fix
- Scoped and cached results of `get_pf_memory()` and `get_gcache_memory()` in local variables upon first execution and reused them throughout the diagnostic routine.

### Verification
Validated with unit test `tests/unit_m3_query_dedup_caching.t`.
EOF
)
create_issue 9 "perf(query): cache Performance Schema and GCache memory query results" "enhancement" "${BODY_9}"

# ==============================================================================
# Issue 10: External Command & SHOW Deduplication
# ==============================================================================
BODY_10=$(cat <<'EOF'
### Problem / Root Cause
1. In `get_system_info` (lines 6137-6248), external OS commands were executed twice (once to verify and once to capture).
2. In `get_all_vars`, duplicate `SHOW VARIABLES` and `SHOW STATUS` queries were executed.

### Surgical Fix
- Modified `infocmd_tab` to return captured output directly, avoiding duplicate command execution.
- Removed redundant SHOW queries in `get_all_vars` while retaining fallback logic.

### Verification
Validated with unit test `tests/unit_m2_system_kernel_fs.t`.
EOF
)
create_issue 10 "perf(system): return command output from infocmd_tab and deduplicate SHOW queries" "enhancement" "${BODY_10}"

# ==============================================================================
# Issue 11: Sysctl & FS Output Rectification
# ==============================================================================
BODY_11=$(cat <<'EOF'
### Problem / Root Cause
1. In `get_kernel_info` (lines 6057-6095), the recommendation mistakenly suggested `fs.aio-nr > 1M` when `fs.nr_open < 1000000`.
2. `sunrpc.tcp_slot_table_entries` check displayed `> 100` instead of `< 100`.
3. In `get_fs_info` (lines 5855-5862), the mount point warning interpolated `$4` (percentage) instead of `$5` (mount point path).

### Surgical Fix
- Corrected sysctl recommendation to `fs.nr_open > 1M`.
- Corrected sunrpc threshold display to `< 100`.
- Corrected mount point interpolation from `$4` to `$5`.

### Verification
Validated with unit tests in `tests/unit_m2_system_kernel_fs.t` and `tests/unit_fs_info.t`.
EOF
)
create_issue 11 "fix(system): correct fs.nr_open sysctl recommendation, sunrpc threshold, and mountpoint" "bug" "${BODY_11}"

# ==============================================================================
# Issue 12: Galera Telemetry & Index Type Alignment
# ==============================================================================
BODY_12=$(cat <<'EOF'
### Problem / Root Cause
1. In `mariadb_galera` (lines 12240-12250), Galera status metrics were read from `%myvar` instead of `%mystat`, and `get_wsrep_options()` was called in scalar context.
2. In `mysql_databases` (lines 14431-14508), character set count was not deduplicated.
3. In `mysql_indexes` (lines 14958-14976), index type referenced an incorrect column index.

### Surgical Fix
- Read Galera status metrics from `%mystat` and assigned `get_wsrep_options()` in list/array context.
- Computed distinct charsets for `CHARS`.
- Referenced `$info[3]` for index `TYPE`.

### Verification
Validated with unit test `tests/unit_m3_galera_indexes_fk.t`.
EOF
)
create_issue 12 "fix(telemetry): read Galera status from mystat, fix wsrep context, and resolve index type" "bug" "${BODY_12}"

# ==============================================================================
# Issue 13: PFS Table Name & Bitwise Operator Fix
# ==============================================================================
BODY_13=$(cat <<'EOF'
### Problem / Root Cause
1. In `mysql_indexes` (lines 14887-14998) with `--ignore-tables`, the query against `performance_schema.table_io_waits_summary_by_index_usage` threw SQL error `Unknown column 'TABLE_NAME'` because the correct column is `OBJECT_NAME`.
2. In `mysql_stats` (lines 8779-8780), query cache evaluation used bitwise OR `|` instead of logical OR `||`.

### Surgical Fix
- Changed query clause to `AND object_name NOT IN (...)`.
- Replaced bitwise `|` with logical `||`.

### Verification
Validated with unit test `tests/unit_m1_index_stats_csv.t`.
EOF
)
create_issue 13 "fix(sql): use object_name in PFS index wait query and fix bitwise operator in stats" "bug" "${BODY_13}"

# ==============================================================================
# Issue 14: Color Preservation & Download Verification
# ==============================================================================
BODY_14=$(cat <<'EOF'
### Problem / Root Cause
1. In `setup_environment` (lines 839-843), `$opt{nocolor} = 1` was overwritten when `$outputfile` was defined.
2. In `update_tuner_version` (lines 3670-3705), the download verification checked `-s $script` instead of the downloaded target path `-s $fullpath`.

### Surgical Fix
- Preserved `$opt{nocolor} = 1` when `$outputfile` is defined.
- Updated download verification to check `-s $fullpath`.

### Verification
Validated with unit test `tests/unit_m2_env_windows_update.t`.
EOF
)
create_issue 14 "fix(cli): preserve nocolor on outputfile and verify downloaded file size in update" "bug" "${BODY_14}"

# ==============================================================================
# Issue 15: CSV Limit Clause Deduplication
# ==============================================================================
BODY_15=$(cat <<'EOF'
### Problem / Root Cause
In `select_csv_file` (lines 4501-4565), `LIMIT $limit` was unconditionally appended, producing syntax errors when the input query already contained an explicit `LIMIT`.

### Surgical Fix
- Added `unless ( $req =~ /\bLIMIT\b/i )` before appending `LIMIT $limit`.

### Verification
Validated with unit test `tests/unit_m1_index_stats_csv.t`.
EOF
)
create_issue 15 "fix(sql): prevent duplicate LIMIT clause in select_csv_file" "bug" "${BODY_15}"

# ==============================================================================
# Issue 16: Redundant Foreign Key Check Removal
# ==============================================================================
BODY_16=$(cat <<'EOF'
### Problem / Root Cause
In `mysql_table_structures` (lines 11618-11634), an expensive query checking for foreign key data type mismatches was executed, duplicating the check already performed by `mysql_foreign_key_checks` (lines 12142-12171).

### Surgical Fix
- Removed the redundant execution in `mysql_table_structures`.

### Verification
Validated with unit test `tests/unit_m3_galera_indexes_fk.t`.
EOF
)
create_issue 16 "perf(schema): eliminate duplicate foreign key mismatch query in table structures" "enhancement" "${BODY_16}"

# ==============================================================================
# Issue 17: Connect Unused Diagnostic Auditors
# ==============================================================================
BODY_17=$(cat <<'EOF'
### Problem / Root Cause
Diagnostic subroutines `audit_pfs_stage_profiling`, `audit_innodb_ahi`, `audit_tls_ciphers_protocols`, and `audit_table_definition_cache` existed in `mysqltuner.pl` but were never invoked during operational execution.

### Surgical Fix
- Safely connected all four diagnostic auditors into the main audit sequence with defensive guards against missing Performance Schema instrumentation or status keys.

### Verification
Validated with unit test `tests/unit_m4_connected_auditors.t`.
EOF
)
create_issue 17 "feat(audit): wire diagnostic auditors for PFS stages, AHI, TLS ciphers, and table cache" "enhancement" "${BODY_17}"

echo ""
echo "=== Issue Creation Process Complete ==="
exit 0
