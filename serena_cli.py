
import argparse
import asyncio
import json
import sys
import os
from contextlib import AsyncExitStack
from typing import Optional, Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

async def run_query(args: argparse.Namespace):
    # Determine transport
    exit_stack = AsyncExitStack()

    try:
        if args.server_command:
            # Stdio transport
            server_params = StdioServerParameters(
                command=args.server_command,
                args=args.server_args,
                env=None # Inherit env?
            )
            # We need to handle the async context manager manually or use exit_stack
            read_stream, write_stream = await exit_stack.enter_async_context(stdio_client(server_params))
        else:
            # SSE transport
            read_stream, write_stream = await exit_stack.enter_async_context(sse_client(url=args.server_url))

        session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()

        # Execute the requested tool
        result = None

        if args.subcommand == 'find-symbol':
            tool_name = "find_symbol"
            tool_args = {
                "name_path_pattern": args.name,
                "relative_path": args.path if args.path else "",
                "max_answer_chars": -1 # We handle limit client-side
                # "include_kinds": [],
                # "exclude_kinds": [],
            }
            # Handle language hint? The tool doesn't seem to take language hint directly.
            # "language" is not a param in FindSymbolTool.apply.
            # We will ignore it for now.

            result = await session.call_tool(tool_name, arguments=tool_args)

        elif args.subcommand == 'file-overview':
            tool_name = "get_symbols_overview"
            tool_args = {
                "relative_path": args.path,
                # "max_answer_chars": -1
            }
            result = await session.call_tool(tool_name, arguments=tool_args)

        elif args.subcommand == 'references':
            tool_name = "find_referencing_symbols"
            # User prompt: "--name and --path, or Some stable symbol identifier"
            # Tool definition: name_path, relative_path

            tool_args = {
                "name_path": args.name,
                "relative_path": args.path,
                # "include_kinds": [],
                # "exclude_kinds": [],
                "max_answer_chars": -1
            }
            result = await session.call_tool(tool_name, arguments=tool_args)

        else:
            print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
            return

        # Process Output
        final_data = []

        for content in result.content:
            if content.type == 'text':
                try:
                    # The tools return a JSON string. We need to parse it.
                    data = json.loads(content.text)
                    if isinstance(data, list):
                        final_data.extend(data)
                    elif isinstance(data, dict):
                         # SearchForPattern returns dict {file: [matches]}
                         # But the query commands we support return list usually.
                         # If it's a dict, treat as single item or special case?
                         # For now, append it.
                         final_data.append(data)
                    else:
                        final_data.append(data)
                except json.JSONDecodeError:
                     # Not JSON, ignore or handle?
                     pass

        # Apply limit if applicable (only for find-symbol which returns a list)
        if args.subcommand == 'find-symbol' and args.limit and args.limit > 0:
            final_data = final_data[:args.limit]

        if args.format == 'json':
            print(json.dumps({"results": final_data}, indent=2))
        else:
            format_plain_text(args.subcommand, final_data)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await exit_stack.aclose()

def format_plain_text(command, data):
    if command == 'find-symbol':
        # data is list of symbol dicts
        if not isinstance(data, list):
            print(data)
            return
        for sym in data:
            name = sym.get('name_path', sym.get('name', 'unknown'))
            kind = sym.get('kind', 'unknown')
            # location is usually flattened or in 'location' dict
            # The tool helper _sanitize_symbol_dict removes 'location' and promotes 'relative_path'
            path = sym.get('relative_path', 'unknown')

            # range?
            start_line = "?"
            if 'body_location' in sym:
                start_line = sym['body_location'].get('start_line', '?')
            elif 'selection_range' in sym:
                start_line = sym['selection_range'].get('start', {}).get('line', '?')
            elif 'range' in sym:
                start_line = sym['range'].get('start', {}).get('line', '?')

            print(f"{name} ({kind}) - {path}:{start_line}")

    elif command == 'file-overview':
        # data is list of top-level symbols
        if not isinstance(data, list):
            print(data)
            return
        print(f"File Overview:")
        for sym in data:
            name = sym.get('name_path', sym.get('name', 'unknown'))
            kind = sym.get('kind', 'unknown')
            print(f"  - {name} ({kind})")

    elif command == 'references':
        # data is list of referencing symbols
        if not isinstance(data, list):
            print(data)
            return
        for ref in data:
            name = ref.get('name_path', ref.get('name', 'unknown'))
            path = ref.get('relative_path', 'unknown')

            line = "?"
            if 'body_location' in ref:
                line = ref['body_location'].get('start_line', '?')
            elif 'selection_range' in ref:
                line = ref['selection_range'].get('start', {}).get('line', '?')
            elif 'range' in ref:
                line = ref['range'].get('start', {}).get('line', '?')

            print(f"Referenced by {name} in {path}:{line}")
            if 'content_around_reference' in ref:
                print(f"    Snippet: {ref['content_around_reference'].strip()}")

def main():
    parser = argparse.ArgumentParser(description="Serena MCP Client")

    # Server connection args
    parser.add_argument("--server-url", default="http://localhost:8000/sse", help="URL for SSE transport (default: http://localhost:8000/sse)")
    parser.add_argument("--server-command", help="Command to run the server (Stdio transport). If set, ignores --server-url.")
    parser.add_argument("--server-args", nargs="*", default=[], help="Arguments for the server command")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Query subcommand group
    query_parser = subparsers.add_parser("query", help="Query the code")
    query_subparsers = query_parser.add_subparsers(dest="subcommand", required=True)

    # find-symbol
    fs_parser = query_subparsers.add_parser("find-symbol", help="Find symbols")
    fs_parser.add_argument("--name", required=True, help="Symbol name or pattern")
    fs_parser.add_argument("--path", help="Relative path restriction")
    fs_parser.add_argument("--language", help="Language hint (ignored currently)")
    fs_parser.add_argument("--limit", type=int, help="Max results")
    fs_parser.add_argument("--format", choices=['text', 'json'], default='text')

    # file-overview
    fo_parser = query_subparsers.add_parser("file-overview", help="Get file overview")
    fo_parser.add_argument("--path", required=True, help="Path to the file")
    fo_parser.add_argument("--format", choices=['text', 'json'], default='text')

    # references
    ref_parser = query_subparsers.add_parser("references", help="Find references")
    ref_parser.add_argument("--name", required=True, help="Symbol name")
    ref_parser.add_argument("--path", required=True, help="File path where symbol is defined")
    ref_parser.add_argument("--format", choices=['text', 'json'], default='text')

    args = parser.parse_args()

    if args.command == 'query':
        asyncio.run(run_query(args))

if __name__ == "__main__":
    main()
