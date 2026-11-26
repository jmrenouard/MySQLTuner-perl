# Audit TLS and Authentication Plugins

Refer to
[Diagnostic Alerts Matrix](../../03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
and [Thresholds and Data Files](../../03-reference/configuration/thresholds-and-files.md)
before you start.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. You have administrative read access to `mysql.user` (or `mysql.global_priv`
   on MariaDB 10.4+).
2. The `openssl` binary exists locally if you audit certificate expiration
   dates.
3. You know which client drivers connect to the database server before you
   alter authentication plugins.

## Safety Precautions

**CAUTION:** Verify client driver compatibility before you switch user accounts
to `caching_sha2_password` or `ed25519`. Older client libraries fail to connect
after an incompatible plugin change.

**NOTE:** MySQLTuner skips SSL/TLS checks when the server accepts connections
only on `localhost`.

## Procedure

1. Run `mysqltuner.pl` on TCP with `--dumpdir` to examine TLS parameters and
   export CSV findings:

   ```bash
   perl mysqltuner.pl \
     --host 127.0.0.1 \
     --verbose \
     --dumpdir /tmp/tls-audit \
     --defaults-file ~/.my.cnf
   ```

2. Examine `SSL/TLS Security Recommendations` and
   `Authentication Plugin Security` in the output.

3. Examine exported `/tmp/tls-audit/ssl_issues.csv` and
   `/tmp/tls-audit/insecure_authentication_plugins.csv` (mode `0600`).

4. If `tls_version` includes `TLSv1` or `TLSv1.1`, restrict `[mysqld]` in
   `my.cnf` to modern protocols:

   ```ini
   [mysqld]
   tls_version = TLSv1.2,TLSv1.3
   require_secure_transport = ON
   ```

5. If `ssl_cert` or `ssl_ca` expires in less than 30 days, renew and reload the
   TLS certificates.

6. For remote accounts that do not enforce SSL, enforce TLS per account:

   ```sql
   ALTER USER 'app_user'@'10.0.%' REQUIRE SSL;
   ```

7. For accounts that use `mysql_native_password` or `sha256_password`, migrate
   to modern plugins:

   ```sql
   -- MySQL 8.0+ / 8.4+ / 9.x
   ALTER USER 'app_user'@'10.0.%' IDENTIFIED WITH caching_sha2_password BY 'strong_secret';

   -- MariaDB 10.4+ (ed25519) or local unix_socket
   ALTER USER 'app_user'@'10.0.%' IDENTIFIED VIA ed25519 USING PASSWORD('strong_secret');
   ```

## Verification

1. Run `mysqltuner.pl --host 127.0.0.1 --verbose --defaults-file ~/.my.cnf`
   again.

2. Make sure that `Only secure TLS versions enabled: TLSv1.2,TLSv1.3` and
   `require_secure_transport is ON` appear.

3. Make sure that
   `No users found using insecure or deprecated authentication plugins` appears.

4. Make sure that `All remote users have SSL enforcement active` appears in the
   security summary.

5. Remove the temporary audit directory `/tmp/tls-audit` after your
   examination.

## Rollback

If legacy applications fail TLS handshakes or plugin authentication, restore
access immediately:

1. If `require_secure_transport = ON` blocks unencrypted legacy clients
   temporarily, run:

   ```sql
   SET GLOBAL require_secure_transport = OFF;
   ```

2. Revert an affected account to its previous authentication plugin or TLS
   requirement on MySQL 8.0/8.4 or MariaDB.

3. Restore the previous `tls_version` value in `my.cnf` and reload TLS if
   legacy clients need an interim window.

## Related Topics

- Reference: [Thresholds and Data Files](../../03-reference/configuration/thresholds-and-files.md)
- Explanation: [Health Score and Version Rift](../../04-explanation/deep-dives/health-score-and-version-rift.md)
