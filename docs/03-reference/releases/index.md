# Release Notes Archive

Versioned release index dynamically populated from `releases/v*.md` during the
MkDocs build.

## Documentation Version Channels

| Selector Alias | Target Scope | Redirect Behavior | Trigger Source |
| :--- | :--- | :--- | :--- |
| `latest` | Most recent tagged production release | Default canonical target (`alias_type: redirect`) | Published GitHub Release |
| `<X.Y.Z>` | Immutable snapshot for a specific release tag | Direct versioned path `/<X.Y.Z>/` | Published GitHub Release or `workflow_dispatch` |
| `dev` | Unreleased `master` branch tip | Updated continuously on `master` docs changes | Push to `master` |

## Published Releases

Source: [GitHub Releases](https://github.com/major/MySQLTuner-perl/releases).

<!-- AUTO_RELEASES_TABLE -->

## Related Documentation

- Versioning and hosting architecture:
  [ADR-002: Versioned Docs](../../04-explanation/design-decisions/adr-002-versioned-documentation-architecture.md)
- Publishing procedure:
  [Publish Versioned Documentation](../../02-how-to-guides/deployment/publish-versioned-docs.md)
