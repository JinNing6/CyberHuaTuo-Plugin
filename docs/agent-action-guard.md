# CyberHuaTuo Agent Action Guard

Updated: 2026-07-14

## Decision

CyberHuaTuo uses an independently implemented, layered action guard:

1. `cyberhuatuo.agent_guard` deterministically classifies the exact command and resolved path scope.
2. `hooks/pre_tool_guard.py` adapts that decision to Codex and Claude Code `PreToolUse` protocol output.
3. MCP `agent_action_guard` and CLI `cyberhuatuo guard` expose the same policy for Agents and operators.
4. The `cyberhuatuo-agent-guard` skill requires preflight use even where a host hook is unavailable.

No layer executes or rewrites the proposed command.

New users should begin with `cyberhuatuo guard --self-test --workspace-root .`. The self-test reviews fixed `ALLOW`, `ASK`, and `BLOCK` examples without executing them. Installation, plugin activation, Hook trust, and verification are documented in [Agent Guard quickstart](agent-guard-quickstart.md).

## Decision Contract

- `ALLOW`: no covered destructive operation is detected.
- `ASK`: a destructive action is bounded to the declared workspace, but permanent loss remains possible.
- `BLOCK`: the action has machine, identity, system, outside-workspace, dynamic, wildcard, unresolved, disk, or database scope that cannot be bounded safely.

Each result includes stable `CHT-*` rule IDs, reasons, targets, reversibility, and safer next steps. Codex `PreToolUse` does not currently support `ask`; the hook converts `ASK` to `deny`. Claude Code receives `ask` and can show an interactive approval.

## Local Case Reports

CyberHuaTuo `0.2.3+` can turn a real command review into a local redacted Markdown case without executing or uploading the command:

```bash
cyberhuatuo guard "<exact proposed command>" --workspace-root . --expected BLOCK --report reports/guard-report.md
```

- `--expected` accepts `ALLOW`, `ASK`, or `BLOCK`. A match exits `0`; a mismatch exits `1`.
- The CLI emits the complete redacted preview before writing and requires confirmation.
- Non-interactive writing requires explicit `--confirm-report`; implicit overwrite is refused unless `--overwrite-report` is also supplied.
- `--redact <literal>` can be repeated for private project or business identifiers that deterministic patterns cannot identify.
- Known credentials, URL authorities, host/user identity, workspace/home context, resolved absolute paths, reasons, and targets are redacted before serialization.
- Private-key material and known secrets that remain after redaction fail closed with exit `4`. Operational report errors are never masked by `--exit-zero`.
- The case fingerprint is derived from the canonical redacted command, expected/actual decisions, and rule IDs, never directly from the raw command.

Public forms separate [false positives](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-positive.yml), [ordinary false negatives](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-negative.yml), and [integration gaps](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-integration-gap.yml). Reliable Hook/parser/wrapper/protocol bypasses use [private vulnerability reporting](https://github.com/JinNing6/CyberHuaTuo-Plugin/security/advisories/new).

## Current Coverage

- Permanent and recursive filesystem deletion on POSIX and Windows.
- Absolute executable path normalization for POSIX and Windows shell commands.
- Common shell wrappers: PowerShell `-Command`, `cmd /c`, and `bash` / `sh` / `zsh -c`.
- Destructive Git cleanup/reset/restore operations.
- Disk formatting, wiping, raw-device overwrite, and destructive PowerShell disk operations.
- Database `DROP` / `TRUNCATE` and mirror-delete synchronization.
- Workspace boundary, system path, home/profile, dynamic target, and wildcard checks.
- Fail-closed hook behavior for malformed shell payloads and guard runtime failures.

## Enforcement Boundary

This is a high-value guardrail, not a sandbox, identity authority, or complete reference monitor.

- A host can only block paths that emit `PreToolUse`. Current Codex documentation says interception is incomplete for `unified_exec` shell paths.
- Plugin hooks are skipped until the user reviews and trusts them.
- A script written to disk and executed through an uncovered path can bypass command-text review.
- The current engine does not claim full AST coverage for every inline language, cloud provider, container platform, or database dialect.
- Permanent deletion has no reliable rollback unless an independent snapshot, backup, version-control reference, transaction, or quarantine copy was verified first.

## Measured Hook Latency

On 2026-07-13, the Windows plugin hook was measured end to end as a fresh Python process after one warm-up per path. Each sample includes process startup, JSON parsing, assessment, and protocol output:

| Path | Samples | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|
| Allow: `git status --short` | 100 | 65.95 ms | 77.56 ms | 86.55 ms | 96.71 ms |
| Deny: `rm -rf /` | 100 | 65.53 ms | 78.12 ms | 91.77 ms | 108.88 ms |

These are local measurements, not universal product claims. Python process startup dominates this implementation; internal matcher timing must not be presented as total hook latency.

## Third-Party Boundary

Do not bundle, copy, derive from, execute, or benchmark Destructive Command Guard (DCG) as part of CyberHuaTuo. Its current license contains an additional rider that denies rights to OpenAI, Anthropic, their affiliates, and parties acting for them. CyberHuaTuo may independently implement general command-guard concepts, but its code, rules, tests, and documentation must remain independently authored.

## Next Engineering Gates

1. Add independently authored AST checks for selected inline Python, JavaScript, shell, and PowerShell execution forms.
2. Add script-to-disk provenance checks that bind a script hash and resolved effects to the task that created it.
3. Add task-scoped, expiring, revocable approval receipts instead of broad permanent allowlists.
4. Add provider rule modules only with real fixtures and false-positive regression cases.
5. Add cross-platform release benchmarks and reduce process-startup overhead without weakening fail-closed behavior.

## Official Host References

- [Codex hooks](https://developers.openai.com/codex/hooks)
- [Codex plugin lifecycle hooks](https://developers.openai.com/codex/plugins)
- [Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)
