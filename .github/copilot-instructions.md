# Project Guidelines

## Workflow
- When a requested code change is complete and validated, prepare a git commit in the same session.
- Before running `git commit`, ask the user for confirmation.
- After the user confirms, create a concise commit message that matches the finished change.
- Commit only the files that belong to the completed task.

## Layout Source Of Truth
- Use `LAYOUT.md` as the canonical project layout document.
- If a task changes the folder structure, major files, or architectural boundaries, update `LAYOUT.md` before committing.
- If `LAYOUT.md` is missing information needed for a structure-changing task, ask the user to fill in the missing section first.