---
description: Writes and runs tests for a specific Spendly feature. Pass the spec name as argument e.g. /test-feature 05-backend-routes-profile
argument-hint: "Spec name e.g. 05-backend-routes-profile"
---

Run the full testing pipeline for the feature specified in $ARGUMENTS.

If no argument is provided, stop immediately and say:
"Please provide a spec name. Usage: /test-feature <spec-name> e.g. /test-feature 05-backend-routes-profile"

If `.claude/specs/$ARGUMENTS.md` does not exist, stop immediately and say:
"Spec file not found at .claude/specs/$ARGUMENTS.md. Please check the spec name and try again."

---

## Step 1: Write Tests

Invoke the **test-writer** subagent with the following context:

- Spec file to base tests on: `.claude/specs/$ARGUMENTS.md`
- Source files to read only for runnability (route names, form fields, table and column names):
  - `app.py`
  - `database/` directory
- Test file: follow the existing convention `tests/test_<feature_slug>.py`, where the slug is the spec name without its step number, with hyphens replaced by underscores (e.g. `05-backend-routes-profile` → `tests/test_backend_routes_profile.py`). If the file exists, extend it.
- Instruction: Write tests based on what the spec says the feature SHOULD do. Do NOT derive test logic from reading the implementation. Cover happy paths, edge cases, auth guards, validation errors, and DB side effects. Write the tests only; do NOT run them, because Step 2 does that. Report the exact path of the test file you wrote.

Wait for test-writer to fully complete and confirm the test file has been written before proceeding to Step 2.

---

## Step 2: Run Tests

Once test-writer has finished, invoke the **test-runner** subagent with the following context:

- Test file to execute: the path reported by test-writer
- Spec file for context: `.claude/specs/$ARGUMENTS.md`
- Source files to analyze against when diagnosing failures:
  - `app.py`
  - `database/` directory
- Run command: `venv/bin/python -m pytest <test file> -v`
- Instruction: Run ONLY the specified test file. Do NOT run the full test suite. Analyze any failures by cross-referencing the test code, the spec, and the source files. Classify each failure as a **code bug**, **test bug**, or **spec gap/mismatch**.

---

## Handoff Rules

- Do NOT start Step 2 until Step 1 is fully complete
- Do NOT attempt to fix any code regardless of what the test results show
- Do NOT run any tests beyond the test file written in Step 1
- If test-writer reports it could not write the test file, stop and report the reason. Do NOT proceed to Step 2

---

## Final Output

After both subagents complete, produce a combined summary:

### Testing Pipeline Report — $ARGUMENTS

**Step 1 — Tests Written**
- List each test written with a one-line description of which spec requirement it validates

**Step 2 — Test Results**
- Mirror the test-runner's structured report

**Verdict**
One of:
- ✅ Ready for code review — all tests pass
- ❌ Needs code fixes — list the failing tests classified as code bugs, with root causes
- ⚠️ Needs test or spec fixes — list the failing tests classified as test bugs or spec gaps, with what to correct
