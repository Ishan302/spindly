---
description: Runs parallel security and quality code review for a specific Spendly feature. Pass the spec name as argument e.g. /code-review-feature 03-login-logout
argument-hint: "Spec name e.g. 03-login-logout"
allowed-tools: Bash(git diff:*), Bash(git status:*)
---

Run the full code review pipeline for the feature specified in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /code-review-feature <spec-name> e.g. /code-review-feature 03-login-logout"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md. Please check the spec name and try again."

## Pre-flight Check

Before invoking any subagents, collect what changed, limited to feature code: `app.py`, `database/`, `templates/` and `static/`.

1. Run `git diff -- app.py database templates static` (unstaged) and `git diff --staged -- app.py database templates static` (staged), and combine them.
2. Run `git status --short -- app.py database templates static` and note any untracked (`??`) files. `git diff` does not show them, so the reviewers must read these files in full.
3. If the diff and the untracked list are both empty, the feature may already be committed: run `git diff main...HEAD -- app.py database templates static` and use that instead.

If everything is still empty, stop immediately and say:
"No changes detected. Implement the feature before running code review."

---

## Step 1: Parallel Review

Send both Agent calls in a single response so the subagents run in parallel. Give both the same context:

**security-reviewer** receives:
- The combined diff and the list of untracked files from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py` and `database/` directory
- Instruction: Review only the changed code for security vulnerabilities. Do not comment on quality or style. Tag every finding with a severity (Critical, High, Medium, Low).

**quality-reviewer** receives:
- The combined diff and the list of untracked files from the pre-flight check
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to reference: `app.py`, `database/` directory, and `templates/` directory
- Instruction: Review only the changed code for quality, Flask best practices, and maintainability. Do not comment on security concerns. Tag every finding with a severity (High, Medium, Low).

---

## Step 2: Unified Report

Once both subagents have completed, combine their findings into a single unified report. De-duplicate overlapping findings: if both agents flagged the same line for different reasons, merge them into one finding with both perspectives noted.

Structure the report as:

### Code Review Report — $ARGUMENTS

**Security Findings**
[security-reviewer output]

**Quality Findings**
[quality-reviewer output]

**Combined Action Plan**
Ordered checklist of everything to fix, by severity:
1. Critical and High security findings
2. High quality findings
3. Medium findings (security and quality)
4. Low findings and polish ideas

**Overall Verdict**
Derive it from the reviewers' severities:
- ❌ CHANGES REQUESTED — any Critical or High finding. Must fix before committing; see the action plan.
- ⚠️ APPROVED WITH SUGGESTIONS — highest severity is Medium or Low. Can commit; address suggestions in future steps.
- ✅ APPROVED — no findings. Ready to commit.

---

## Step 3: Ask for Approval

After presenting the unified report, ask:

"Do you want me to implement the action plan now?"

Wait for explicit user confirmation before making any changes. Do not touch any files until the user approves.

---

## Rules
- Do NOT edit any files before user approval
- Do NOT skip the pre-flight check
- Both reviewers must be launched together in one response
- If either subagent fails or returns no output, report it and do not present a partial review as complete
