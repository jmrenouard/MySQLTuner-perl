# Explanation

Architectural overviews, design decisions, and analytical deep dives explaining how MySQLTuner works and why it is
structured this way.

## Explanation Catalog

| Category | Document | Focus |
| :--- | :--- | :--- |
| Architecture Overview | [Diagnostic Pipeline](architecture-overview/diagnostic-pipeline.md) | Execution lifecycle, transport abstraction, and output serialization |
| Architecture Overview | [AI Agent Architecture](architecture-overview/ai-agent-architecture.md) | `.agent/skills/` domain layer, MCP stdio/SSE server, and `--agent-json` |
| Design Decisions | [ADR-001: Single-File Perl Architecture](design-decisions/adr-001-single-file-zero-dependency.md) | Single-file constraint and zero non-core CPAN dependency model |
| Design Decisions | [ADR-002: Versioned Diátaxis Docs](design-decisions/adr-002-versioned-diataxis-docs.md) | MkDocs Material, `mike` redirects, and IONOS SFTP deployment |
| Deep Dives | [Health Score and Version Rift](deep-dives/health-score-and-version-rift.md) | `40/30/30` Health Score analytics and MySQL vs MariaDB divergence |

## Cross-Quadrant Navigation

- Guided labs: [Tutorials](../01-tutorials/index.md)
- Operational runbooks and procedures: [How-To Guides](../02-how-to-guides/index.md)
- Exact specs, flags, and matrices: [Reference](../03-reference/index.md)
