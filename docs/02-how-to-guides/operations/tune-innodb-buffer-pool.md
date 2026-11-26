# Tune InnoDB Buffer Pool Safely

Refer to
[Diagnostic Alerts Matrix](../../03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
and [Thresholds and Data Files](../../03-reference/configuration/thresholds-and-files.md)
before you start.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. The database server has a minimum uptime of 24 hours under normal production
   traffic.
2. You have `SUPER` or `SYSTEM_VARIABLES_ADMIN` privileges on the target
   instance.
3. A current backup of `/etc/mysql/my.cnf` (or `/etc/my.cnf`) exists on disk.
4. Free physical host RAM matches the planned buffer pool size without swap
   pressure.

## Safety Precautions

**CAUTION:** Calculate free host RAM before you increase
`innodb_buffer_pool_size`. Excess memory allocation triggers OS swap activity or
an out-of-memory process kill.

**NOTE:** On MariaDB 10.4 and newer, `innodb_buffer_pool_instances` no longer
exists.

## Procedure

1. Run `mysqltuner.pl` with `--buffers` and `--verbose` to measure current
   InnoDB memory and hit ratios:

   ```bash
   perl mysqltuner.pl --buffers --verbose --defaults-file ~/.my.cnf
   ```

2. Record the current `innodb_buffer_pool_size`,
   `innodb_buffer_pool_chunk_size`, and `innodb_buffer_pool_instances` values:

   ```sql
   SHOW GLOBAL VARIABLES WHERE Variable_name IN (
     'innodb_buffer_pool_size',
     'innodb_buffer_pool_chunk_size',
     'innodb_buffer_pool_instances'
   );
   ```

3. Calculate a target size that fits below 75% of dedicated host RAM.

4. On MySQL, make sure that the target size equals a multiple of
   `chunk_size * instances`.

5. Apply the new buffer pool size dynamically with `SET GLOBAL`:

   ```sql
   SET GLOBAL innodb_buffer_pool_size = 4294967296;
   ```

6. Wait until InnoDB completes the background resize operation:

   ```sql
   SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_resize_status';
   ```

7. Write the exact byte or gigabyte value under `[mysqld]` in `my.cnf` so
   restarts keep the value:

   ```ini
   [mysqld]
   innodb_buffer_pool_size = 4G
   ```

8. If you must change `innodb_buffer_pool_instances` on MySQL, schedule a
   maintenance restart.

## Verification

1. Make sure that `Innodb_buffer_pool_resize_status` shows
   `Completed resizing buffer pool` or an empty string.

2. Query `SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size';` and make sure
   that the byte count matches.

3. Run `mysqltuner.pl` again after workload warm-up and make sure that the hit
   ratio exceeds 95%:

   ```bash
   perl mysqltuner.pl --buffers --verbose --defaults-file ~/.my.cnf
   ```

4. Examine OS memory with `free -m` and make sure that zero swap growth
   occurs.

## Rollback

If memory pressure or query latency increases after the adjustment, revert the
pool size immediately:

1. Apply the original recorded `innodb_buffer_pool_size` value dynamically:

   ```sql
   SET GLOBAL innodb_buffer_pool_size = <previous_bytes>;
   ```

2. Wait until `Innodb_buffer_pool_resize_status` shows completion.

3. Replace `my.cnf` with the backup file on disk.

## Related Topics

- Reference: [Diagnostic Alerts Matrix](../../03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
- Explanation: [Health Score and Version Rift](../../04-explanation/deep-dives/health-score-and-version-rift.md)
