---
name: Agent Best Practices
description: A set of core principles and practices for building and maintaining agent-friendly codebases.
---

# Agent Best Practices

This skill outlines mandatory practices for working effectively with AI agents. Follow these guidelines to ensure the codebase remains navigable, understandable, and robust for agentic interaction.

## 1. Start Here (Do These Today)

### Instruction Files as Table of Contents
*   **Concept**: Your instruction file (e.g., `CLAUDE.md`, `AGENTS.md`) is a **Table of Contents**, not a manual.
*   **Constraint**: Keep it to ~100 lines max.
*   **Action**: Use it solely to point to deeper documentation. If everything is "important," nothing is.

### Codebase Is The Only Truth
*   **Concept**: If it's not in the codebase, it doesn't exist.
*   **Action**: Move architectural decisions, specs, and external docs (Google Docs, Slack threads) into the repo as markdown files. Agents cannot see your external tools.

### Ask For Missing Capabilities
*   **Concept**: When you (the agent) fail, do not blindly retry.
*   **Action**: Ask the user: *"What capability is missing from this environment, and how can I make it more visible and enforceable for you?"* Diagnose the blind spot.

## 2. Structure Your Repo For Agents

### Versioned Plans
*   **Concept**: Agents need access to the plan.
*   **Action**: Check plans (what's being built, what's done, tech debt) into the repo as versioned files (e.g., `implementation_plans/`, `roadmap.md`). Do not rely on external tickets (Jira).

### Progressive Disclosure
*   **Concept**: Don't overwhelm the context window.
*   **Action**: Provide a small entry point, then link to further information. Teach the agent where to look next, similar to onboarding a human engineer.

### Boring Tools
*   **Concept**: Reliability > Novelty.
*   **Action**: Choose stable APIs and predictable tools with abundant training data. Agents reason better about well-known technology than obscure libraries.

## 3. Automate Quality

### Automated Garbage Collection
*   **Concept**: Agents copy patterns, including bad ones. Codebases degrade without maintenance.
*   **Action**: Set up background agents/scripts to scan for bad patterns and open cleanup PRs automatically.

### Doc-Gardening
*   **Concept**: Documentation must match reality.
*   **Action**: Implementation of a "doc-gardening" agent or workflow that verifies docs against code and opens fix-up PRs when discrepancies are found.
