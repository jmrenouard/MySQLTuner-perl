# Diagnose Replication Lag

Refer to
[Diagnostic Alerts Matrix](../../03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
for lag thresholds and alert definitions.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. You have database access credentials with `REPLICATION CLIENT` or
   `REPLICA MONITOR` privileges.
2. You have `SUPER` or `REPLICATION_SLAVE_ADMIN` privileges if you must adjust
   worker threads.
3. You know the primary source hostname and current maintenance window status.

## Safety Precautions

**CAUTION:** Never skip replication errors or reset binary log coordinates
without DBA authorization. Incorrect position resets cause permanent data
divergence between primary and replica nodes.

**NOTE:** MySQL 8.0.22+ and MariaDB 10.5+ use `REPLICA` syntax, while older
versions use `SLAVE`.

## Procedure

1. Run `mysqltuner.pl` on the replica node to examine topology, thread state,
   GTID gaps, and lag:

   ```bash
   perl mysqltuner.pl --verbose --defaults-file ~/.my.cnf
   ```

2. Query the replica status directly in SQL to examine exact thread fields and
   errors:

   ```sql
   SHOW REPLICA STATUS\G
   -- On MySQL < 8.0.22 or MariaDB < 10.5:
   SHOW SLAVE STATUS\G
   ```

3. Examine `Replica_IO_Running` and `Replica_SQL_Running` (or `Slave_IO_Running`
   and `Slave_SQL_Running`).

4. If either thread shows `No`, examine `Last_IO_Error`, `Last_SQL_Error`, and
   `Last_SQL_Errno` immediately.

5. Fix network or privilege failures for IO thread errors before you run
   `START REPLICA;`.

6. If the two threads show `Yes` and `Seconds_Behind_Source` climbs, examine the
   worker count:

   ```sql
   -- MySQL 8.0+
   SHOW GLOBAL VARIABLES LIKE 'replica_parallel_workers';
   -- MariaDB 10.5+
   SHOW GLOBAL VARIABLES WHERE Variable_name IN ('slave_parallel_threads', 'slave_parallel_mode');
   ```

7. Record the current worker count and mode before you make a change.

8. If parallel worker threads equal `0` or `1`, stop the SQL thread and
   increase worker concurrency:

   ```sql
   -- MySQL 8.0+ example
   STOP REPLICA SQL_THREAD;
   SET GLOBAL replica_parallel_workers = 4;
   START REPLICA SQL_THREAD;
   ```

9. On MariaDB 10.5 or newer, set `slave_parallel_threads` and
   `slave_parallel_mode = 'optimistic'`:

   ```sql
   STOP SLAVE SQL_THREAD;
   SET GLOBAL slave_parallel_threads = 4;
   SET GLOBAL slave_parallel_mode = 'optimistic';
   START SLAVE SQL_THREAD;
   ```

10. Examine `binlog_format` on the primary source and make sure that `ROW`
    format is active.

## Verification

1. Run `SHOW REPLICA STATUS\G` (or `SHOW SLAVE STATUS\G`) and make sure that the
   two threads show `Yes`.

2. Monitor `Seconds_Behind_Source` (or `Seconds_Behind_Master`) across three
   checks and make sure that lag drops.

3. Run `mysqltuner.pl --verbose` and make sure that no GTID gap or thread alert
   remains.

## Rollback

If worker concurrency triggers lock contention or replication errors, revert to
the previous thread values:

1. Stop the replica SQL thread safely:

   ```sql
   STOP REPLICA SQL_THREAD;
   ```

2. Apply the recorded baseline worker variable values:

   ```sql
   SET GLOBAL replica_parallel_workers = <previous_count>;
   ```

3. Start the replica SQL thread and make sure that the two threads show `Yes`:

   ```sql
   START REPLICA SQL_THREAD;
   SHOW REPLICA STATUS\G
   ```

## Related Topics

- Reference: [Diagnostic Alerts Matrix](../../03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
- Explanation: [Diagnostic Pipeline](../../04-explanation/architecture-overview/diagnostic-pipeline.md)
