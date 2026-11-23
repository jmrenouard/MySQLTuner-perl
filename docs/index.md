# MySQLTuner Documentation

**Current Version:** <!-- CURRENT_VERSION -->

MySQLTuner is a single-file Perl diagnostic and performance tuning advisor for MySQL, MariaDB, and Percona Server.
It runs with zero non-core CPAN dependencies, evaluates over 900 indicators, and computes a Weighted Health Score
(0-100) across Performance, Security, and Resilience. It also integrates with AI workflows through `--agent-json`,
a Model Context Protocol (MCP) server, and curated domain skills.

## Documentation Quadrants (Diataxis)

Choose the section that matches your immediate goal:

| Quadrant | Purpose | Start Here |
| :--- | :--- | :--- |
| **Tutorials** | Learning-oriented hands-on labs in isolated Docker sandboxes | [Explore Tutorials](01-tutorials/index.md) |
| **How-To Guides** | Goal-oriented operational procedures and on-call runbooks | [Explore How-To Guides](02-how-to-guides/index.md) |
| **Reference** | Neutral specifications, CLI flags, thresholds, and alert tables | [Explore Reference](03-reference/index.md) |
| **Explanation** | Architectural design decisions, internals, and analytical deep dives | [Explore Explanation](04-explanation/index.md) |

## Quick Links

- **First Sandbox Audit:** [Run Your First MySQLTuner Audit in a Sandbox](01-tutorials/01-first-audit-sandbox.md)
- **AI & MCP Lab:** [Run an AI Agent & MCP Sandbox Lab](01-tutorials/02-ai-mcp-sandbox-lab.md)
- **CLI Options & Environment:** [CLI Options & Environment](03-reference/cli-and-scripts/cli-options.md)
- **Troubleshooting Alerts:** [Diagnostic Alerts Matrix](03-reference/troubleshooting-codes/diagnostic-alerts-matrix.md)
- **Release Notes Archive:** [Release Notes Archive](03-reference/releases/index.md)
