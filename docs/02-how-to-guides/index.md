# How-To Guides

These operational guides and on-call runbooks provide step-by-step production procedures written in strict
ASD-STE100 Issue 9. Use them when you need to execute a specific administrative task or triage an active incident.

## Guides by Domain

### Deployment

- **[Run Remote and Container Audits](deployment/run-remote-and-container-audit.md)**: Audit remote MySQL/MariaDB
  instances over SSH, direct TCP, Docker, Podman, or Kubernetes.
- **[Publish Versioned Docs](deployment/publish-versioned-docs.md)**: Validate, build, preview, and publish versioned
  MkDocs Material and `mike` documentation.

### Operations

- **[Tune InnoDB Buffer Pool](operations/tune-innodb-buffer-pool.md)**: Measure hit ratios, adjust
  `innodb_buffer_pool_size` safely, verify stability, and revert on regression.
- **[Run Offline Verification](operations/run-offline-verification.md)**: Compile `mysqltuner.pl`, inspect offline
  indicators, run unit tests, and validate Diátaxis documentation.

### Incident Response

- **[Diagnose Replication Lag](incident-response/diagnose-replication-lag.md)**: On-call triage runbook for stopped
  IO/SQL threads, GTID gaps, and parallel worker saturation.

### Security

- **[Audit TLS and Auth Plugins](security/audit-tls-and-auth-plugins.md)**: Verify transport encryption, cipher
  suites, certificate expiration, and authentication plugin safety.

## Related Quadrants

- **First-Time Sandbox Labs:** [Tutorials](../01-tutorials/index.md)
- **CLI Flags & Alert Matrices:** [Reference](../03-reference/index.md)
- **Internals & Design Decisions:** [Explanation](../04-explanation/index.md)
