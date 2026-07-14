# CyberHuaTuo Privacy Policy

Last updated: 2026-07-14.

CyberHuaTuo is an open-source MCP server, Codex plugin, Claude plugin, and Claude Desktop extension for diagnosing AI-agent and framework failures.

## Data Processed

CyberHuaTuo may process the text a user provides to a tool, including error messages, stack traces, code snippets, framework names, GitHub usernames, GitHub issue identifiers, prescription content, verification notes, and contribution metadata.

## Local Storage

Some tools write local runtime state in the user's CyberHuaTuo environment:

- `diagnose` can save a diagnosis record under `.user_data/`.
- `my_medical_record`, `subscribe_framework`, `prescription_eval`, and `mentorship` can update local profile, subscription, evaluation, or review state.
- `save_prescription` and `upload_prescription` can create prescription case files.
- ChromaDB indexes and epidemic reports can be stored locally for search and monitoring.

Local runtime files such as `.user_data/`, `.chroma_db/`, `.env`, and generated reports are excluded from the public repository by `.gitignore`.

### Agent Action Guard Reports

`cyberhuatuo guard --report` builds a local Markdown preview from the command text supplied by the user. Report generation:

- Does not execute the reviewed command.
- Performs no network request, telemetry, or automatic public upload.
- Requires an expected `ALLOW`, `ASK`, or `BLOCK` decision.
- Shows the redacted report before writing and requires interactive confirmation, or explicit `--confirm-report` in non-interactive use.
- Refuses implicit overwrite and refuses to generate a public report when private-key material or a known unredacted token remains.
- Redacts known credentials, URL authorities, host/user identity, workspace/home context, and absolute paths before serialization.

Automated redaction cannot identify every private business term, repository name, or proprietary identifier. Users must review the preview and can repeat `--redact <literal>` before sharing. Only the redacted report is written; the raw Guard assessment is not persisted by this command.

## External Services

Depending on the tool and local configuration, CyberHuaTuo may contact external services:

- GitHub, for issue mining, public repository synchronization, and contribution workflows.
- Official documentation providers or framework documentation sources, for documentation lookup.
- LLM providers configured by the user, for diagnosis, issue refinement, or security checkup analysis.

CyberHuaTuo does not include built-in credentials. Users control external access through local environment variables such as `GITHUB_TOKEN` and any configured LLM API keys.

## Public Contributions

If a user submits a prescription through GitHub sync, issue forms, pull requests, or public repository workflows, the submitted content and associated GitHub username can become public repository content. Do not submit secrets, private code, proprietary logs, credentials, or personal data that should not be public.

## No Conversation Harvesting

CyberHuaTuo tools only process inputs passed to the tool call and local/public data sources needed for that tool. The project does not query Claude, Codex, or ChatGPT conversation history or memory.

## Contact

Report exploitable Guard, Hook, parser, protocol, enforcement, secret-exposure, or redaction vulnerabilities privately:

https://github.com/JinNing6/CyberHuaTuo-Plugin/security/advisories/new

Use the public issue tracker only for redacted, non-sensitive product bugs and ordinary misclassifications:

https://github.com/JinNing6/CyberHuaTuo-Plugin/issues
