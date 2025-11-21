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
