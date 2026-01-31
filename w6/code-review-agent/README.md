# Code Review Agent

An AI-powered code review agent built on the `simple-agent` SDK.

## Core Design

**Agent only provides System Prompt and Tools. The entire review process is autonomously driven by the LLM.**

The agent doesn't:
- Parse user input
- Decide tool calling order
- Contain any business logic

The LLM:
- Interprets user intent
- Decides which tools to call and when
- Analyzes code changes
- Generates structured review reports

## Installation

```bash
pnpm install
```

## Usage

### Basic Example

```typescript
import { createCodeReviewAgent, createSession } from "code-review-agent"

const agent = createCodeReviewAgent({
  model: "gpt-4o",
  onEvent: (event) => {
    if (event.type === "text") process.stdout.write(event.text)
    if (event.type === "tool_call") console.log(`\n[Tool: ${event.name}]`)
  }
})

const session = createSession()

// The LLM autonomously decides how to handle these requests
await agent.run(session, "帮我 review 当前 branch 新代码")
await agent.run(session, "详细解释第 2 个问题")
await agent.run(session, "保存审查结果到 REVIEW.md")
```

### Run Examples

```bash
# Basic review
pnpm example

# With custom message
pnpm example "帮我 review PR #42"

# Interactive mode
pnpm tsx examples/interactive.ts
```

## Supported Scenarios

The LLM dynamically decides how to handle each request:

| User Request | LLM's Tool Calls |
|--------------|------------------|
| "review 当前代码" | `git diff` + `git diff --cached` |
| "review 当前 branch" | `git diff main...HEAD` |
| "review commit abc123 之后的代码" | `git diff abc123..HEAD` |
| "review commit abc123" | `git show abc123` |
| "review PR #42" | `gh pr diff 42` |

## Tools

All tools are passive (LLM-invoked):

### read_file
Read file contents for context understanding.

### write_file
Write content to files (for saving review reports).

### git_command
Execute read-only git commands:
- `diff`, `show`, `log`, `blame`, `status`, `branch`
- Dangerous commands (push, reset, etc.) are blocked

### gh_command
Execute read-only GitHub CLI commands:
- `pr view/diff/list/checks`
- `issue view/list`
- `repo view`
- Modification operations are blocked

### bash_command
Execute safe, read-only bash commands:
- File browsing: `ls`, `find`, `cat`, `head`, `tail`, `tree`
- Search: `grep`, `rg`
- Package managers: `npm`, `pnpm`, `pip`, `cargo` (info only)
- Code tools: `tsc`, `eslint`, `prettier` (check mode)
- Destructive operations are blocked

## Configuration

Environment variables:
- `OPENAI_API_KEY` - OpenAI API key (required)
- `OPENAI_BASE_URL` - Custom API base URL (optional)
- `DEFAULT_MODEL` - Default model (optional, defaults to gpt-4o)

## Project Structure

```
code-review-agent/
├── src/
│   ├── index.ts          # Main entry, creates Agent
│   └── tools/
│       ├── read-file.ts  # File reading tool
│       ├── write-file.ts # File writing tool
│       ├── git-command.ts # Git command tool (with safety checks)
│       └── gh-command.ts  # GitHub CLI tool (with whitelist)
├── prompts/
│   └── system.md         # System prompt (defines LLM behavior)
├── examples/
│   ├── basic.ts          # Basic usage example
│   └── interactive.ts    # Interactive mode example
├── package.json
└── tsconfig.json
```

## License

ISC
