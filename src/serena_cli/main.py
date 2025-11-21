import argparse
import asyncio
import json
import os
import shutil
import sys
import re
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent

# Default command to launch the server
DEFAULT_SERVER_COMMAND = "uvx --from git+https://github.com/oraios/serena serena start-mcp-server"

def get_symbol_kind_name(kind_id: int) -> str:
    # Mapping from LSP SymbolKind
    kinds = {
        1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class",
        6: "Method", 7: "Property", 8: "Field", 9: "Constructor", 10: "Enum",
        11: "Interface", 12: "Function", 13: "Variable", 14: "Constant", 15: "String",
        16: "Number", 17: "Boolean", 18: "Array", 19: "Object", 20: "Key",
        21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event", 25: "Operator",
        26: "TypeParameter"
    }
    return kinds.get(kind_id, str(kind_id))

def transform_symbol_result(item: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Serena symbol dict to the requested CLI JSON format."""
    # 1. Restore name from name_path if missing
    if "name" not in item and "name_path" in item:
        # name_path example: "MyClass/my_method[0]"
        last_part = item["name_path"].split("/")[-1]
        if "[" in last_part and last_part.endswith("]"):
             last_part = re.sub(r'\[\d+\]$', '', last_part)
        item["name"] = last_part

    # 2. Transform kind to string
    if "kind" in item and isinstance(item["kind"], int):
        item["kind"] = get_symbol_kind_name(item["kind"]).lower()

    # 3. Transform range
    if "range" in item and isinstance(item["range"], dict):
        r = item["range"]
        start = r.get("start", {})
        end = r.get("end", {})
        if "line" in start and "line" in end:
             new_range = {
                 "start_line": start["line"],
                 "end_line": end["line"]
             }
             item["range"] = new_range
    elif "body_location" in item and isinstance(item["body_location"], dict):
         item["range"] = item["body_location"]

    # 4. Ensure 'file' key exists
    if "relative_path" in item:
        item["file"] = item["relative_path"]

    # 5. Guess language if missing
    if "language" not in item and "file" in item:
         ext = os.path.splitext(item["file"])[1]
         if ext == ".py": item["language"] = "python"
         elif ext == ".ts": item["language"] = "typescript"
         elif ext == ".js": item["language"] = "javascript"
         elif ext == ".java": item["language"] = "java"

    return item

async def main_async():
    parser = argparse.ArgumentParser(description="Serena MCP CLI Client")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'query' subcommand
    fs_parser = subparsers.add_parser("query", help="Execute a query")
    query_subparsers = fs_parser.add_subparsers(dest="query_command", required=True)

    # query find-symbol
    find_symbol_parser = query_subparsers.add_parser("find-symbol", help="Find symbols by name/pattern")
    find_symbol_parser.add_argument("--name", required=True, help="Symbol name or pattern")
    find_symbol_parser.add_argument("--language", help="Language hint (optional)")
    find_symbol_parser.add_argument("--limit", type=int, help="Max number of results")

    # query file-overview
    file_overview_parser = query_subparsers.add_parser("file-overview", help="Get file overview")
    file_overview_parser.add_argument("--path", required=True, help="File path")

    # query references
    refs_parser = query_subparsers.add_parser("references", help="Find references")
    refs_parser.add_argument("--name", required=True, help="Symbol name")
    refs_parser.add_argument("--path", required=True, help="File path")

    args = parser.parse_args()

    # Determine server command
    server_cmd_str = os.environ.get("SERENA_SERVER_COMMAND", DEFAULT_SERVER_COMMAND)
    parts = server_cmd_str.split()
    cmd = parts[0]
    cmd_args = parts[1:]

    # Check for executable
    if not shutil.which(cmd):
         print(f"Error: Command '{cmd}' not found. Please ensure it is in your PATH.", file=sys.stderr)
         sys.exit(1)

    # Pass current project if not specified
    if "--project" not in cmd_args:
        cmd_args.extend(["--project", "."])

    # Disable dashboard and GUI logs for headless CLI usage
    if "--enable-web-dashboard" not in cmd_args:
         cmd_args.extend(["--enable-web-dashboard", "False"])
    if "--enable-gui-log-window" not in cmd_args:
         cmd_args.extend(["--enable-gui-log-window", "False"])

    server_params = StdioServerParameters(
        command=cmd,
        args=cmd_args,
        env=os.environ.copy()
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tool_name = ""
                tool_args = {}

                if args.query_command == "find-symbol":
                    tool_name = "find_symbol"
                    tool_args = {"name_path_pattern": args.name}
                    # Ignoring --language

                elif args.query_command == "file-overview":
                    tool_name = "get_symbols_overview"
                    tool_args = {"relative_path": args.path}

                elif args.query_command == "references":
                    tool_name = "find_referencing_symbols"
                    tool_args = {"name_path": args.name, "relative_path": args.path}

                # Call the tool
                result: CallToolResult = await session.call_tool(tool_name, arguments=tool_args)

                if result.isError:
                    print(f"Error calling tool '{tool_name}':", file=sys.stderr)
                    for content in result.content:
                         if isinstance(content, TextContent):
                             print(content.text, file=sys.stderr)
                    sys.exit(1)

                # Parse content
                output_data = []
                for content in result.content:
                    if isinstance(content, TextContent):
                        try:
                            data = json.loads(content.text)
                            if isinstance(data, list):
                                output_data.extend(data)
                            elif isinstance(data, dict):
                                output_data.append(data)
                        except json.JSONDecodeError:
                             print(f"Warning: Non-JSON response received: {content.text}", file=sys.stderr)

                # Transform data
                output_data = [transform_symbol_result(item) for item in output_data]

                # Filter by language if requested
                if args.query_command == "find-symbol" and args.language:
                     target_lang = args.language.lower()
                     output_data = [
                         item for item in output_data
                         if item.get("language", "").lower() == target_lang
                     ]

                # Limit
                if args.query_command == "find-symbol" and args.limit:
                     output_data = output_data[:args.limit]

                # Output
                if args.format == "json":
                    wrapper = {"results": output_data}
                    print(json.dumps(wrapper, indent=2))
                else:
                    # Plain text formatting
                    if args.query_command == "find-symbol":
                        if not output_data:
                            print("No symbols found.")
                        for item in output_data:
                            name = item.get("name", "?")
                            kind = item.get("kind", "?")
                            file = item.get("file", "?")
                            start_line = item.get("range", {}).get("start_line", "?")
                            print(f"{name:<30} {kind:<15} {file}:{start_line}")

                    elif args.query_command == "file-overview":
                        if not output_data:
                            print("No symbols found in file.")
                        for item in output_data:
                            name = item.get("name", "?")
                            kind = item.get("kind", "?")
                            start_line = item.get("range", {}).get("start_line", "?")
                            print(f"{kind:<15} {name:<30} (Line {start_line})")

                    elif args.query_command == "references":
                        if not output_data:
                            print("No references found.")
                        for item in output_data:
                            file = item.get("file", "?")
                            start_line = item.get("range", {}).get("start_line", "?")
                            snippet = item.get("content_around_reference", "").strip()
                            print(f"Referenced in {file}:{start_line}")
                            if snippet:
                                print(f"  Code:\n{snippet}\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
