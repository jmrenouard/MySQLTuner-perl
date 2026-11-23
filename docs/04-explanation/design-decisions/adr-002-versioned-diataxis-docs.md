# ADR-002: Versioned Diátaxis Documentation Architecture

| Attribute | Value |
| :--- | :--- |
| **Status** | Accepted |
| **Date** | `2026-11-23` |
| **Deciders** | Project Maintainers |
| **Supersedes** | Legacy PHP documentation site and ad-hoc root Markdown cross-links |

## Context

MySQLTuner documentation historically spanned root-level generated Markdown (`USAGE.md`, `FEATURES.md`,
`mysql_support.md`, `mariadb_support.md`, `SECURITY.md`), historical release notes (`releases/v*.md`), multilingual
READMEs, and architectural specifications under `documentation/`, alongside a legacy PHP website.

Keeping operator runbooks, conceptual architecture, and CLI reference tables synchronized across releases required a
static, version-aware publishing pipeline deployable to `https://mysqltuner.lightpath.fr/` on IONOS SFTP hosting.

## Options Considered and Trade-Offs

| Option | Genre Clarity | Release Versioning | Shared Hosting Compatibility (IONOS SFTP) | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| Option A: Diátaxis 4-quadrant `docs/` + MkDocs Material + `mike` (`alias_type: redirect`) | High (enforced by CI gates) | Native (`latest`, `vX.Y.Z`, `dev`) | High (pure static HTML/JS/CSS + `.htaccess`) | **Selected** |
| Option B: Legacy static PHP site with manual HTML updates | Low (mixed prose and snippets) | Manual directory copies | Requires PHP runtime and manual routing | Rejected |
| Option C: MkDocs Material + `mike` with `alias_type: symlink` | High | Native | Low (SFTP deploys and Apache `FollowSymLinks` often fail on shared hosts) | Rejected |

## Decision

Adopt **Option A**:

1. **Diátaxis 4-Quadrant Tree**: Organize user and contributor documentation under `docs/` into `01-tutorials/`,
   `02-how-to-guides/`, `03-reference/`, and `04-explanation/`, keeping `02-how-to-guides/` compliant with ASD-STE100
   Issue 9 procedural clarity.
2. **Build-Time Single-Source Reuse (`build/mkdocs_hooks.py`)**: Keep canonical generated files (`USAGE.md`,
   `FEATURES.md`, `mysql_support.md`, `mariadb_support.md`, `SECURITY.md`, `CURRENT_VERSION.txt`, and `releases/v*.md`)
   in the repository root and inject them dynamically at build time via `<!-- INCLUDE_SOURCE: ... -->`,
   `<!-- CURRENT_VERSION -->`, and `<!-- AUTO_RELEASES_TABLE -->`.
3. **Versioned Hosting via `mike` Redirects**: Publish immutable `vX.Y.Z` snapshots, `latest`, and `dev` channels to the
   `docs-site` branch using `alias_type: redirect` and `canonical_version: latest` (never `symlink`), then synchronize
   the archived tree plus `build/docs_htaccess` to IONOS over SFTP.
4. **Docs-as-Code CI Gates**: Enforce `build/check_diataxis_docs.py docs --strict`, `markdownlint-cli2`, `mkdocs build
   --strict`, and `tests/unit_mkdocs_diataxis.t` on pull requests.

## Consequences

### Positive

- **Single Source of Truth**: Generated root files (`USAGE.md`, `FEATURES.md`, `*_support.md`, `releases/v*.md`) remain
  the authoritative data inputs without manual copy-paste drift inside `docs/`.
- **Clean Static Security Posture**: Replacing dynamic PHP scripts with static HTML, `.htaccess` security headers, and
  `no-cache` headers on `versions.json` removes server-side execution surface.
- **Strict Genre Separation**: Operators find 1-action runbooks in `02-how-to-guides/` while engineers consult
  specifications in `03-reference/` and ADRs in `04-explanation/`.

### Negative and Operational Mitigations

- **Dual Documentation Trees**: Legacy contributor specifications in `documentation/` remain outside `docs/` so existing
  audit scripts (`build/check_doc_links.pl`, `build/audit_specifications.pl`) continue passing uninterrupted.
- **SFTP Credential Dependency**: Automated publishing requires `IONOS_FTP_SERVER`, `IONOS_FTP_USERNAME`,
  `IONOS_FTP_PASSWORD`, and `IONOS_REMOTE_PATH` secrets; workflows degrade gracefully to `docs-site` branch builds when
  secrets are absent or `dry_run` is selected.

## Related Documentation

- Dynamic release index: [Release Notes Archive](../../03-reference/releases/index.md)
- Publishing procedure: [Publish Versioned Documentation](../../02-how-to-guides/deployment/publish-versioned-docs.md)
