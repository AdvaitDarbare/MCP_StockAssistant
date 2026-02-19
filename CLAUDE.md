# AI Stock Assistant - Claude Code Instructions

## Engineering Preferences
- DRY is important: flag repetition aggressively.
- Well-tested code is non-negotiable: prefer too many tests over too few.
- Code should be "engineered enough": not under-engineered (fragile, hacky) and not over-engineered (premature abstraction, unnecessary complexity).
- Err on the side of handling more edge cases, not fewer.
- Bias toward explicit over clever; thoughtfulness over speed.

## Review Pipeline
Before implementing significant features or making widespread changes, perform a review across 4 axes (Architecture, Code Quality, Tests, Performance). Explain tradeoffs and ask for user input before assuming a direction based on `review-plan.md`.

## Workflows
- **Install dependencies**: `poetry install` (for Python) or `npm install` (for Node).
- **Start development servers**: `./dev.sh` or `npm run dev` at the root.
- **Linting & Formatting**: `npm run lint` and `npm run format`.
- **Python Formatting**: `poetry run black .` and `poetry run isort .`.
- Always typecheck/lint when making a series of changes.
- Prefer running single tests for performance rather than the whole suite during development.
