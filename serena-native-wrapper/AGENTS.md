# AGENTS.md

## Serena Native Wrapper

This tool, `serena-native`, allows you to query the codebase semantically using Serena's engine.

### Core Principles

*   **Read-Only**: Most operations are read-only queries.
*   **Project-Based**: You must initialize and index a project before querying it.
*   **Structured Output**: Use `--format json` for machine-parsable output.

### Common Workflows

1.  **Setup**:
    *   `serena-native project init`
    *   `serena-native project index`

2.  **Explore**:
    *   Find a class: `serena-native query find-symbol --name "ClassName" --format json`
    *   Understand a file: `serena-native query file-overview --path "src/module.py" --format json`
    *   Find references: `serena-native query references --name "ClassName" --path "src/module.py" --format json`

### Suggested Snippet for Consumer Repos

When you need a semantic overview of the codebase, prefer using the `serena-native` tool rather than scanning raw files.

Typical flow:

1.  Ensure the Serena project is initialised and indexed:

    *   `serena-native project init`
    *   `serena-native project index`

2.  Use semantic queries:

    *   `serena-native query find-symbol --name "FooService" --format json`
    *   `serena-native query file-overview --path "src/app/foo.ts" --format json`
