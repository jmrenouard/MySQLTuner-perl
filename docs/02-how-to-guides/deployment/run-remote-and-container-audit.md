# Run Remote and Container Audits

Refer to [CLI Options and Environment](../../03-reference/cli-and-scripts/cli-options.md) before you start this
procedure.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. You have database access credentials with read privileges on the target server.
2. Perl 5.6 or a newer version exists on the control host.
3. For SSH mode, SSH key access or `sshpass` exists on the control host.
4. For container mode, the `docker`, `podman`, or `kubectl` CLI exists on the control host.

## Safety Precautions

**CAUTION:** Never put passwords in plain CLI arguments on shared hosts. Other users can read command arguments
from process lists.

**NOTE:** Container mode probes `cgroup` memory limits and skips host kernel checks.

## Procedure

### Method A: Audit via SSH Transport

1. Set database and SSH parameters, then start `mysqltuner.pl` with `--ssh-host`:

   ```bash
   perl mysqltuner.pl \
     --ssh-host db01.internal \
     --ssh-user dba_ops \
     --ssh-identity-file ~/.ssh/id_ed25519 \
     --defaults-file ~/.my.cnf \
     --verbose
   ```

2. If the target uses an SSH password instead of a key, install `sshpass` first.

3. Pass `--ssh-password` only in an isolated automation runner, not on shared terminals.

### Method B: Audit via Direct Remote TCP

1. Get the physical RAM and swap totals from the server administrator.

2. Set `--forcemem` and `--forceswap` so buffer calculations match the remote server hardware:

   ```bash
   export MYSQL_PWD_USER="mysqltuner"
   export MYSQL_PWD_VAL="secret"
   perl mysqltuner.pl \
     --host 192.0.2.50 \
     --port 3306 \
     --userenv MYSQL_PWD_USER \
     --passenv MYSQL_PWD_VAL \
     --forcemem 32G \
     --forceswap 4G \
     --verbose
   ```

3. If you audit a managed cloud database without SSH, add `--cloud` (and `--azure` on Azure).

**NOTE:** Direct `--cloud` mode without `--ssh-host` assumes 1024 MB RAM unless you pass `--forcemem`.

### Method C: Audit Docker, Podman, or Kubernetes Containers

1. Run `mysqltuner.pl` with `--container` and the runtime prefix (`docker:`, `podman:`, or `kubectl:`):

   ```bash
   # Docker container
   perl mysqltuner.pl --container docker:prod_mysql --defaults-file ~/.my.cnf --verbose

   # Podman container
   perl mysqltuner.pl --container podman:prod_mariadb --defaults-file ~/.my.cnf --verbose

   # Kubernetes pod
   perl mysqltuner.pl --container kubectl:mysql-primary-0 --host 127.0.0.1 --defaults-file ~/.my.cnf --verbose
   ```

2. Examine the `cgroup` memory limit and container error log summary in the terminal output.

## Verification

1. Examine the header output and make sure that the target hostname or container name appears.

2. Make sure that the `System Linux Recommendations` or `cgroup` memory lines show accurate RAM values.

3. Make sure that no SSH or container transport errors appear in the output.

## Rollback

This audit executes read-only commands and makes no server changes.

1. If a temporary SSH agent or terminal session stays open, close the session.

2. Remove temporary report files or credentials files from `/tmp` after review:

   ```bash
   rm -f /tmp/mysqltuner_report.html /tmp/result_mysqltuner.txt
   ```

## Related Topics

- Reference: [CLI Options and Environment](../../03-reference/cli-and-scripts/cli-options.md)
- Explanation: [Diagnostic Pipeline](../../04-explanation/architecture-overview/diagnostic-pipeline.md)
