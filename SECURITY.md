# Security Policy

## Supported Versions

Security fixes are developed against the latest released `0.2.x` version and the current default branch. Reproduce against the latest available release before reporting when it is safe to do so.

## Report Privately

Use [GitHub private vulnerability reporting](https://github.com/JinNing6/CyberHuaTuo-Plugin/security/advisories/new) for:

- Reliable Hook, parser, shell-wrapper, protocol, or enforcement bypasses.
- Cases that could permit an Agent to perform an unapproved destructive action.
- Secret exposure, unsafe report redaction, path disclosure, or authentication failures.
- Any report whose reproduction details would increase risk if published before a fix exists.

Do not open a public Issue first for these cases. Do not execute a destructive command solely to demonstrate impact.

Include the minimum redacted information needed to reproduce:

- CyberHuaTuo version and installation method.
- Agent host, host version, OS, shell, and whether the Hook was reviewed and trusted.
- The expected and observed `ALLOW / ASK / BLOCK` behavior.
- Rule IDs and a redacted command or minimal non-destructive reproducer.
- Whether the host emitted `PreToolUse` and enforced the returned decision.

Remove credentials, tokens, usernames, hostnames, absolute paths, private URLs, proprietary data, and private repository identifiers.

## Report Publicly

Use the public Guard forms only when the details are safe to disclose:

- [Guard false positive](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-positive.yml)
- [Ordinary Guard false negative](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-negative.yml)
- [Guard integration gap](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-integration-gap.yml)

Generate a local redacted report without executing the reviewed command:

```bash
cyberhuatuo guard "<exact proposed command>" --workspace-root . --expected BLOCK --report reports/guard-report.md
```

The CLI prints a redacted preview and asks before writing. It performs no network request or automatic public upload. Automated redaction cannot identify every private business term, so review the preview and add `--redact <literal>` as needed.

## Enforcement Boundary

CyberHuaTuo Agent Action Guard is a deterministic guardrail, not a sandbox or complete reference monitor. It can enforce only on host paths that emit and honor the supported Hook protocol. Permanent deletion has no automatic rollback unless an independent snapshot, backup, version-control reference, transaction, or quarantine copy was verified first.
