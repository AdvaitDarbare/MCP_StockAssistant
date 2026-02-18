---
name: Token Efficiency & Productivity
description: Strategies for minimizing token usage while maximizing productivity when working with AI coding agents.
---

# Token Efficiency & Productivity

This skill provides concrete strategies to reduce token consumption and increase work efficiency when using Claude Code or similar AI coding agents.

## 1. Tool Selection (Critical for Token Savings)

### ❌ NEVER Use Task Tool For:
- Simple find-and-replace operations
- Single-file edits
- Straightforward code changes
- Basic file operations

**Why:** Task tool spawns a full sub-agent with its own context window. A single Task call can use **40,000+ tokens** for work that could be done with **500 tokens** using Edit.

### ✅ Use Direct Tools Instead:
```
# WRONG (uses 40k+ tokens):
Task tool to replace "blue" with "orange" across files

# RIGHT (uses ~500 tokens):
Edit(file1, "bg-blue-50", "bg-orange-50", replace_all=true)
Edit(file1, "text-blue-600", "text-orange-600", replace_all=true)
Edit(file2, "bg-blue-50", "bg-orange-50", replace_all=true)
```

### ✅ DO Use Task Tool For:
- Complex multi-file exploration requiring research
- When you need to search, analyze, and make decisions across 10+ files
- Planning complex implementation strategies
- Exploring unfamiliar codebases

---

## 2. Read Tool Optimization

### Use Offset + Limit for Large Files
```python
# WRONG (reads entire 5000-line file):
Read(file_path="App.jsx")

# RIGHT (reads only relevant section):
Read(file_path="App.jsx", offset=2095, limit=30)
```

### Read Only What You Need
- Use Grep to find the section first
- Then Read with offset/limit
- Don't read entire files when you only need a function

### Parallel Reads When Possible
```python
# WRONG (sequential calls, multiple messages):
Read file1
<wait for response>
Read file2
<wait for response>

# RIGHT (parallel reads, single message):
Read file1
Read file2
Read file3
# All in one message block
```

---

## 3. Grep Tool Efficiency

### Use Specific Patterns
```bash
# WRONG (returns too many results):
Grep pattern="function"

# RIGHT (precise search):
Grep pattern="def run_check\(" output_mode="content"
```

### Use output_mode Wisely
- `files_with_matches`: When you just need file paths (minimal tokens)
- `content`: When you need to see the actual code
- `count`: When you just need to know how many matches

### Use head_limit to Reduce Output
```bash
# Limit to first 10 matches
Grep pattern="import.*React" head_limit=10
```

---

## 4. Edit Tool Best Practices

### Use replace_all for Repetitive Changes
```python
# WRONG (multiple edits):
Edit(file, old="color1", new="color2")
Edit(file, old="color1", new="color2")  # Again for 2nd occurrence
Edit(file, old="color1", new="color2")  # Again for 3rd...

# RIGHT (single edit):
Edit(file, old="color1", new="color2", replace_all=true)
```

### Batch Edits in Single Message
When making multiple independent edits, do them all in one message to save round-trips.

---

## 5. Glob Tool Optimization

### Use Specific Patterns
```bash
# WRONG (too broad):
Glob pattern="*.jsx"

# RIGHT (specific location):
Glob pattern="frontend/src/components/charts/*.jsx"
```

---

## 6. Message Efficiency

### Batch Independent Operations
```
# WRONG (3 separate messages):
Message 1: Read file1.jsx
<wait>
Message 2: Read file2.jsx
<wait>
Message 3: Read file3.jsx

# RIGHT (1 message with 3 tool calls):
Message with:
  - Read file1.jsx
  - Read file2.jsx
  - Read file3.jsx
```

### Provide Context Upfront
Instead of asking clarifying questions, provide all necessary context in your first message:

```
# WRONG:
"Update the colors"
<agent asks which colors>
"The blue ones"
<agent asks to what>
"To violet"

# RIGHT:
"Replace all bg-blue-* classes with bg-violet-* in the frontend/src directory"
```

---

## 7. Avoid Re-reading Files

### Track What You've Read
The agent should remember what it has read in the current conversation. Don't re-read files unnecessarily.

### Use Context from Previous Reads
Reference line numbers and content from earlier in the conversation instead of re-reading.

---

## 8. Strategic Use of Web Tools

### WebFetch vs Manual Research
- Use WebFetch sparingly (uses significant tokens for HTML processing)
- Prefer reading local documentation files when available
- Cache important information from web searches in repo docs

---

## 9. Commit Message Efficiency

### Write Commits Without Extra Research
When committing, use knowledge from the current session instead of:
- Re-reading files to write commit messages
- Running extra git commands
- Exploring the codebase again

---

## 10. Know When to Stop

### Avoid Over-optimization
- Don't read 10 files looking for the "perfect" solution
- Make reasonable assumptions based on patterns
- Ask the user if truly unclear

### Progressive Enhancement
- Get the core working first
- Optimize in follow-up commits
- Don't try to handle every edge case upfront

---

## Token Budget Awareness

### Current Session Limits
- Check token usage periodically
- If usage is high (>50%), be extra conservative
- Prioritize user's explicit requests over nice-to-haves

### High-Value vs Low-Value Operations
**High-Value (worth tokens):**
- Implementing user-requested features
- Fixing critical bugs
- Reading documentation for complex decisions

**Low-Value (waste tokens):**
- Reading files "just to check"
- Over-analyzing simple changes
- Spawning Task agents for trivial work

---

## Summary Checklist

Before using any tool, ask:
- [ ] Can I use Edit instead of Task?
- [ ] Can I use Grep to narrow down before Read?
- [ ] Can I batch this with other operations?
- [ ] Do I really need to read this file, or can I infer from context?
- [ ] Am I using the most specific pattern/path possible?
- [ ] Can I use offset/limit to read less?

**Remember:** Every token saved allows for more productive work later in the session.
