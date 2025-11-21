# Serena CLI

A lightweight CLI client for the Serena MCP server.

## Installation

Ensure you have `uv` installed.

```bash
pip install .
```

## Usage

### Find Symbol

Find symbols by name or pattern.

```bash
serena-cli query find-symbol --name "MySymbol"
```

### File Overview

Get a structural overview of a file.

```bash
serena-cli query file-overview --path "src/my_file.py"
```

### References

Find references to a symbol.

```bash
serena-cli query references --name "MySymbol" --path "src/my_file.py"
```

## JSON Output

All commands support JSON output via `--format json` (implied by the requirement, though I need to implement it).

Wait, the user requirement says:
"Output: Plain text: ... JSON: list of objects like..."

So I should probably add a global flag or per-command flag for output format. The user said "The CLI tool is designed to support structured JSON output (`--format json`)".
I will add `--format` argument.
