---
name: cyberhuatuo-agent-guard
description: Use before an Agent permanently deletes files, runs destructive Git cleanup, formats or wipes disks, drops database data, or mirrors deletions. Reviews the exact command and requires ALLOW, ASK, or BLOCK handling.
---

# CyberHuaTuo Agent Action Guard

## Trigger

Run this skill before any proposed action that can destroy or broadly remove user data, including:

- Permanent or recursive deletion such as `rm -rf`, `Remove-Item -Recurse`, `del /s`, `find -delete`, or shredding.
- Destructive Git operations such as `git clean`, `git reset --hard`, checkout/restore that discards work.
- Disk formatting, partitioning, wiping, raw-device writes, or free-space erasure.
- Database `DROP` or `TRUNCATE` statements.
- Mirror synchronization that deletes destination files, such as `robocopy /MIR` or `rsync --delete`.

## Preflight

For first-run verification, review the built-in examples without executing anything:

```bash
cyberhuatuo guard --self-test --workspace-root "<workspace>"
```

Continue only when it prints `SELF-TEST PASSED` with one `ALLOW`, one `ASK`, and one `BLOCK`.

Prefer the MCP tool when available:

```text
agent_action_guard(
  command="<exact proposed shell command>",
  cwd="<current working directory>",
  workspace_root="<declared workspace root>"
)
```

Otherwise use the CLI:

```bash
cyberhuatuo guard "<exact proposed shell command>" --cwd "<cwd>" --workspace-root "<workspace>" --json
```

The review is read-only and does not execute, rewrite, approve, or intercept the command.

## Decision Contract

- `ALLOW`: no destructive signature was detected. Continue only within the declared task and workspace.
- `ASK`: stop and obtain explicit human approval for the exact resolved targets. Show what will be lost and verify a snapshot, backup, or quarantine copy first.
- `BLOCK`: do not execute. The target is machine-wide, identity-wide, outside the workspace, dynamic, wildcarded, unresolved, or otherwise impossible to bound safely.

Never reinterpret `ASK` as approval. Never bypass `BLOCK` by changing syntax while preserving the same destructive scope.

## Rollback Rule

Do not promise a "regret pill" for permanent deletion. A rollback exists only after a real snapshot, backup, version-control reference, database transaction, or quarantine copy has been verified independently of the target tree.

## Enforcement Boundary

This skill makes the Agent call the guard before the action. The MCP tool and CLI are advisory unless the host permission or hook layer enforces their result. Do not claim that CyberHuaTuo globally intercepts every command until such a host integration is installed and verified.
