# ADR-001: Single-File Perl and Zero-Dependency Core Architecture

| Attribute | Value |
| :--- | :--- |
| **Status** | Accepted |
| **Date** | `2026-11-23` |
| **Deciders** | Project Maintainers (Constitution Tier 00) |
| **Supersedes** | None |

## Context

Database administrators frequently execute diagnostic tooling on hardened, air-gapped, or ephemeral Linux, BSD,
Solaris, AIX, macOS, and Windows hosts where installing compilers, CPAN toolchains, or third-party runtime packages is
prohibited or impractical.

MySQLTuner's core mission requires a tool that can be copied as a single artifact onto any target host and audited
directly by security teams before execution.

## Options Considered and Trade-Offs

| Option | Deployment Friction | Security Auditability | Maintenance Ergonomics | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| Option A: Single-file `mysqltuner.pl` + Perl Core modules only | Minimal (`wget` or `scp` one file; runs on base Perl) | High (entire engine in one inspectable file) | Medium (requires strict sectioning and `perltidy`) | **Selected** |
| Option B: Multi-file Perl package (`lib/*.pm` + CPAN `DBI`/`DBD::mysql`) | High (requires CPAN, C headers, or OS package manager) | Medium (dependency tree expands attack surface) | High (modular files) | Rejected |
| Option C: Compiled binary (Go/Rust) or Python package | Medium-High (cross-arch builds or Python venv needed) | Medium | High | Rejected for core engine |

## Decision

Adopt **Option A** as an immutable constitutional constraint for `mysqltuner.pl`:

1. Keep the entire diagnostic engine inside a single executable file (`mysqltuner.pl`). Splitting `mysqltuner.pl` into
   external `.pm` modules is prohibited.
2. Restrict imports strictly to Perl Core modules (`POSIX`, `File::Spec`, `File::Temp`, `Getopt::Long`, `Pod::Usage`,
   `Sys::Hostname`, `File::Basename`, `Cwd`) and graceful `eval { require ... }` checks for optional Core modules
   (`JSON::PP`, `Time::HiRes`, `Digest::SHA`, `Time::Local`).
3. Delegate SQL execution through existing `mysql` / `mariadb` and `mysqladmin` / `mariadb-admin` CLI binaries rather
   than requiring `DBD::mysql` or `DBD::MariaDB`.
4. Isolate optional ecosystem microservices (such as `build/mcp_server.py`) as external wrappers using Python 3 standard
   library only, leaving the core Perl diagnostic tool self-contained.

## Consequences

### Positive

- **Zero-Install Portability**: Administrators can download or copy `mysqltuner.pl` directly into air-gapped
  environments and run diagnostics immediately using base Perl.
- **Minimal Attack Surface**: Excluding third-party CPAN modules eliminates external supply-chain dependencies and
  simplifies security sign-off.
- **Transport Uniformity**: Invoking `mysql` and OS utilities through `execute_system_command()` enables identical
  execution locally, over SSH (`--ssh-host`), or inside containers (`--container`).

### Negative and Structural Mitigations

- **Large Single-File Footprint**: `mysqltuner.pl` exceeds 19,000 lines, raising merge-conflict and readability risks.
  The project mitigates this by enforcing `perltidy` formatting, pure calculation helper functions, automated
  compliance auditing (`build/check_compliance.pl`), and subtest-decomposed unit tests in `tests/`.
- **CLI Subprocess Parsing**: Querying via the `mysql` CLI rather than a binary wire driver requires defensive shell
  escaping (`_shell_quote()`, `[REQ-INFRA-01]`, `[REQ-INFRA-02]`) and explicit client error extraction
  (`extract_client_error()`).

## Related Documentation

- Full technical reference index: [Reference Overview](../../03-reference/index.md)
- Capabilities and Core JSON indicator export:
  [Capabilities and Indicators](../../03-reference/architecture-specs/capabilities-and-indicators.md)
- CLI contract and exit codes:
  [CLI Options and Environment](../../03-reference/cli-and-scripts/cli-options.md)
