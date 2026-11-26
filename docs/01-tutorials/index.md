# Tutorials

Welcome to the MySQLTuner learning lab! These step-by-step tutorials teach you
how to run database diagnostics and AI-assisted audits safely inside isolated
local Docker sandboxes before touching any shared environment.

> **Environment Warning:** Execute tutorial commands only against disposable
> local Docker containers. Never point sandbox commands at staging or
> production databases.

## Available Labs

1. **[First Audit Sandbox](01-first-audit-sandbox.md)**: Start a local MariaDB
   container, run a verbose CLI audit, inspect the Weighted Health Score, and
   generate a standalone HTML diagnostic dashboard.
2. **[AI & MCP Sandbox Lab](02-ai-mcp-sandbox-lab.md)**: Export actionable
   `--agent-json` telemetry, inspect the offline `--list-indicators` catalog,
   and interact with the Model Context Protocol (MCP) server over JSON-RPC
   stdio.

## Continue Your Journey

Once you finish the sandbox labs, explore the remaining documentation sections:

- **Apply in Operations:** [How-To Guides](../02-how-to-guides/index.md)
- **Look Up Exact Flags & Thresholds:** [Reference](../03-reference/index.md)
- **Understand the Architecture:** [Explanation](../04-explanation/index.md)
