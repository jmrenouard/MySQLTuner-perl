# Run Offline Verification Tests

Refer to
[CLI Options and Environment](../../03-reference/cli-and-scripts/cli-options.md)
before you start this procedure.

## Preconditions

Before you start this procedure, make sure that these conditions apply:

1. Perl 5.8 or a newer version exists on your workstation.
2. Python 3.8 or a newer version and `make` exist on your workstation.
3. A local checkout of `MySQLTuner-perl` is clean on a dedicated branch.

## Safety Precautions

**CAUTION:** Run tests inside an isolated checkout or clean branch. Never write
test output files over production databases or host directories.

**NOTE:** The offline verification commands require zero network access and zero
database containers.

## Procedure

1. Verify Perl syntax on `mysqltuner.pl`:

   ```bash
   perl -c mysqltuner.pl
   ```

2. Run `mysqltuner.pl` with `--help` and make sure that help text displays
   without errors:

   ```bash
   perl mysqltuner.pl --help
   ```

3. Export the offline JSON indicator catalog with `--list-indicators`:

   ```bash
   perl mysqltuner.pl --list-indicators | head -n 20
   ```

4. Run `build/mcp_server.py` with `--help` to verify the MCP server
   entrypoint:

   ```bash
   CACHE_DIR=/tmp/mt-mcp-cache python3 build/mcp_server.py --help
   ```

5. Run the Perl unit and compliance test suite:

   ```bash
   make unit-tests
   ```

6. Run the Python and Perl issue triage test suite:

   ```bash
   make test-triage
   ```

7. Run the documentation structure and style checks:

   ```bash
   make docs-check
   ```

## Verification

1. Make sure that `perl -c mysqltuner.pl` prints `mysqltuner.pl syntax OK` and
   exits with code `0`.

2. Make sure that `make unit-tests`, `make test-triage`, and `make docs-check`
   exit with code `0`.

3. Examine `git status --short` and make sure that zero temporary test
   artifacts remain on disk:

   ```bash
   git status --short
   ```

## Rollback

If a check fails after local edits, revert the modified file and run the suite
again:

1. Discard broken test or documentation changes on the current branch:

   ```bash
   git checkout -- <modified_file>
   ```

2. Run `make unit-tests` and `make docs-check` again to confirm green status.

## Related Topics

- Reference: [CLI Options and Environment](../../03-reference/cli-and-scripts/cli-options.md)
- Explanation:
  [ADR-001 Single-File Perl Architecture](../../04-explanation/design-decisions/adr-001-single-file-zero-dependency.md)
