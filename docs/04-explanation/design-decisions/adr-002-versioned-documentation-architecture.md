# ADR-002: Versioned Documentation Architecture

| Attribute | Value |
| :--- | :--- |
| **Status** | Accepted |
| **Date** | `2026-11-23` |
| **Deciders** | Project Maintainers |
| **Supersedes** | Legacy PHP documentation site and ad-hoc root Markdown cross-links |

## Context

MySQLTuner documentation historically spanned root-level generated Markdown
(`USAGE.md`, `FEATURES.md`, `mysql_support.md`, `mariadb_support.md`,
`SECURITY.md`), release notes (`releases/v*.md`), multilingual READMEs, and
contributor specs under `documentation/`, alongside a legacy PHP site.

Keeping operator runbooks, conceptual architecture, and CLI reference tables
synchronized across releases required a static, version-aware publishing
pipeline deployable to `https://mysqltuner.lightpath.fr/` on IONOS SFTP hosting.

## Options Considered and Trade-Offs

| Option | Genre Clarity | Release Versioning | Shared Hosting Compatibility (IONOS SFTP) | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| Option A: 4-section `docs/` + MkDocs Material + `mike` (`alias_type: redirect`) | High (enforced by CI gates) | Native (`latest`, `vX.Y.Z`, `dev`) | High (pure static HTML/JS/CSS + `.htaccess`) | **Selected** |
| Option B: Legacy static PHP site with manual HTML updates | Low (mixed prose and snippets) | Manual directory copies | Requires PHP runtime and manual routing | Rejected |
| Option C: MkDocs Material + `mike` with `alias_type: symlink` | High | Native | Low (SFTP deploys and Apache `FollowSymLinks` often fail on shared hosts) | Rejected |

## Decision

Adopt **Option A**:

1. **4-Section Documentation Tree**: Organize user and contributor docs under
   `docs/` into `01-tutorials/`, `02-how-to-guides/`, `03-reference/`, and
   `04-explanation/`, keeping `02-how-to-guides/` focused on procedural clarity.
2. **Build-Time Single-Source Reuse (`build/mkdocs_hooks.py`)**: Keep generated
   root files (`USAGE.md`, `FEATURES.md`, `mysql_support.md`,
   `mariadb_support.md`, `SECURITY.md`, `CURRENT_VERSION.txt`, `releases/v*.md`)
   in the repository root.
3. **Hook Token Expansion**: Inject root artifacts dynamically at build time via
   `<!-- INCLUDE_SOURCE: ... -->`, `<!-- CURRENT_VERSION -->`, and
   `<!-- AUTO_RELEASES_TABLE -->`.
4. **Versioned Hosting via `mike` Redirects**: Publish `vX.Y.Z` snapshots,
   `latest`, and `dev` channels to `docs-site` using `alias_type: redirect` and
   `canonical_version: latest`, then deploy with `build/docs_htaccess` over
   SFTP.
5. **Docs-as-Code CI Gates**: Enforce strict structure validation,
   `markdownlint-cli2`, `mkdocs build --strict`, Vale style checks, and
   automated documentation unit tests on pull requests.

## Consequences

### Positive

- **Single Source of Truth**: Generated root files (`USAGE.md`, `FEATURES.md`,
  `*_support.md`, `releases/v*.md`) remain the authoritative data inputs without
  manual copy-paste drift inside `docs/`.
- **Clean Static Security Posture**: Replacing dynamic PHP scripts with static
  HTML, `.htaccess` security headers, and `no-cache` headers on `versions.json`
  removes server-side execution surface.
- **Strict Section Separation**: Operators find 1-action runbooks in
  `02-how-to-guides/` while engineers consult specifications in `03-reference/`
  and ADRs in `04-explanation/`.

### Negative and Operational Mitigations

- **Dual Documentation Trees**: Legacy contributor specifications in
  `documentation/` remain outside `docs/` so existing audit scripts
  (`build/check_doc_links.pl`, `build/audit_specifications.pl`) continue
  passing.
- **SFTP Credential Dependency**: Publishing requires `IONOS_FTP_SERVER`,
  `IONOS_FTP_USERNAME`, `IONOS_FTP_PASSWORD`, and `IONOS_REMOTE_PATH` secrets;
  workflows fall back to `docs-site` branch builds when secrets are absent.

## Related Documentation

- Dynamic release index:
  [Release Notes Archive](../../03-reference/releases/index.md)
- Publishing procedure:
  [Publish Versioned Documentation](../../02-how-to-guides/deployment/publish-versioned-docs.md)
