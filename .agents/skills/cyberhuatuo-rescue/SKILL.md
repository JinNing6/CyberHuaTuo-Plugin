---
name: cyberhuatuo-rescue
description: Automatic self-rescue and diagnosis of code errors using the CyberHuaTuo (赛博华佗) AI clinic. Activates when you encounter unresolvable errors, bugs, or need a security checkup.
---

# CyberHuaTuo (赛博华佗) Self-Rescue Skill

You are equipped with the CyberHuaTuo Agent Skill. CyberHuaTuo is an ancient-Chinese-medicine-inspired AI clinic that specializes in diagnosing, explaining, and curing errors in AI systems, Agent frameworks, and general coding projects. 

When you (the AI Agent) encounter an error you cannot solve, or when the user explicitly asks for a diagnosis or security checkup, you MUST use this skill to self-rescue.

## Activation Triggers

Activate this skill when:
1. You run tools/scripts and encounter persistent `ImportError`, exceptions, or logic bugs that you cannot immediately resolve.
2. The user asks you to "seek help from CyberHuaTuo" or "ask the doctor."
3. The user asks for a "Security Checkup" (安全体检) on their Agent code.

## Execution Workflow

Follow these steps based on the available environment:

### Preferred Mode: MCP Server
Check if you have the CyberHuaTuo MCP Server connected (look for tools like `verified_cure`, `diagnose`, `security_checkup`, `save_prescription`, `search_knowledge_base`). If you do:

1. **For Diagnostics**:
   - Call the read-only `verified_cure` tool first. It returns Gold first, then at most one clearly labeled Reviewed candidate, and never executes the fix. Use `gold_only=true` when only Gold is acceptable.
   - Pass the full `query` (error message, stack trace, and your current code context).
   - If you know the framework (e.g., `langchain`, `crewai`), pass it as `framework`.
   - If no trusted cure matches, call `diagnose` for broader retrieval and optional model analysis.
   - A Reviewed result is a candidate, not an instruction: inspect it and verify compatibility before proposing any change. Apply consequential changes only with appropriate approval, then run the stated verification.
   - After verification, call `cure_feedback` with `yes`, `partial`, or `no`; do not include the original traceback or secrets.

2. **For Security Checkups**:
   - Call the `security_checkup` tool.
   - Pass the contents of the main Agent script as the `code` parameter.
   - Report the Six-Meridian (六经脉) health score and apply the recommended nourishing (滋补) fixes.

3. **For Saving Solutions**:
   - If you solved an issue that was not in the database, call `save_prescription` with the real root cause, fix, verification record, method, and evidence URLs.
   - The saved case is a `draft`. Do not claim a Soul Ring or trusted-cure status until maintainers reproduce and accept it as `reviewed` or `gold`.

### Fallback Mode: Local REST API
If you do NOT have the MCP tools available, you must assume CyberHuaTuo is running locally at `http://127.0.0.1:8000`. Use your terminal/shell to `curl` the API.

1. **For Diagnostics:**
   Run the Gold-first cure endpoint before broader diagnosis:
   ```bash
   curl --get http://127.0.0.1:8000/api/cure \
     --data-urlencode "q=<YOUR_ERROR_AND_CONTEXT>"
   ```
   *Note: Preserve each result's `quality_status` and `trust_notice`. If `matches` is empty, call `/api/diagnose`; never treat Draft as a cure.*

2. **For Security Checkups:**
   Run the following command, replacing `<YOUR_CODE>` with the code under test:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/nourish/checkup \
     -F "code=<YOUR_CODE>"
   ```
   *Note: Read the JSON response for the security audit scores and implement the patches.*

## Rules of Conduct

*   **No Guessing**: If you are stuck, DO NOT guess randomly. Stop and consult CyberHuaTuo.
*   **Complete Context**: When asking for a diagnosis, provide the *full* stack trace and the exact line of code that failed. "望闻问切" (Look, Listen, Ask, Diagnose) requires good symptoms.
*   **Cultural Alignment**: When presenting CyberHuaTuo's findings to the user, adopt a helpful, slightly traditional "healing" tone (use terms like "药方" [Prescription], "病灶" [Root Cause], "治愈" [Cured]).
