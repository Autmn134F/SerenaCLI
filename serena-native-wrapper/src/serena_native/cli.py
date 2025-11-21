import argparse
import sys
import json
import os
from pathlib import Path
from typing import List, Optional, Any

from serena_native.config import Config
from serena_native.serena_client import SerenaClient
from serena_native.logging_utils import log_info, log_error

def main():
    parser = argparse.ArgumentParser(description="Serena Native Wrapper")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Project commands
    proj_parser = subparsers.add_parser("project", help="Project management")
    proj_sub = proj_parser.add_subparsers(dest="subcommand", help="Project subcommand")

    init_parser = proj_sub.add_parser("init", help="Initialize project")
    init_parser.add_argument("--project-root", help="Path to project root")

    index_parser = proj_sub.add_parser("index", help="Index project")
    index_parser.add_argument("--project-root", help="Path to project root")

    status_parser = proj_sub.add_parser("status", help="Project status")
    status_parser.add_argument("--project-root", help="Path to project root")

    # Query commands
    query_parser = subparsers.add_parser("query", help="Semantic queries")
    query_sub = query_parser.add_subparsers(dest="subcommand", help="Query subcommand")

    find_sym_parser = query_sub.add_parser("find-symbol", help="Find symbols")
    find_sym_parser.add_argument("--name", required=True, help="Symbol name or pattern")
    find_sym_parser.add_argument("--language", help="Language hint")
    find_sym_parser.add_argument("--project-root", help="Path to project root")

    file_overview_parser = query_sub.add_parser("file-overview", help="File overview")
    file_overview_parser.add_argument("--path", required=True, help="File path")
    file_overview_parser.add_argument("--project-root", help="Path to project root")

    refs_parser = query_sub.add_parser("references", help="Find references")
    refs_parser.add_argument("--name", required=True, help="Symbol name")
    refs_parser.add_argument("--path", required=True, help="File path containing the symbol")
    refs_parser.add_argument("--project-root", help="Path to project root")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = Config()
    # Determine project root
    # 1. arg
    # 2. env var (handled by Config init)
    # 3. CWD (handled by Config init)

    cmd_root = getattr(args, "project_root", None)
    if cmd_root:
        config.set_project_root(cmd_root)

    client = SerenaClient(config.project_root)

    try:
        result = None

        if args.command == "project":
            if args.subcommand == "init":
                result = client.init_project()
            elif args.subcommand == "index":
                result = client.index_project()
            elif args.subcommand == "status":
                result = client.get_status()
            else:
                proj_parser.print_help()
                sys.exit(1)

        elif args.command == "query":
            if args.subcommand == "find-symbol":
                result = client.find_symbol(args.name, getattr(args, "language", None))
            elif args.subcommand == "file-overview":
                result = client.file_overview(args.path)
            elif args.subcommand == "references":
                result = client.find_references(args.name, args.path)
            else:
                query_parser.print_help()
                sys.exit(1)

        # Output handling
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print_text_output(result, args.command, getattr(args, "subcommand", ""))

    except Exception as e:
        if args.format == "json":
            print(json.dumps({"error": str(e)}))
        else:
            log_error(str(e))
        sys.exit(1)

def print_text_output(result: Any, command: str, subcommand: str):
    if command == "project":
        if subcommand == "status":
            print(f"Serena Available: {result.get('serena_available')}")
            print(f"Project Detected: {result.get('project_detected')}")
            print(f"Index State: {result.get('index_state')}")
        else:
            print(f"Status: {result.get('status')}")
            if "project_name" in result:
                print(f"Project: {result['project_name']}")

    elif command == "query":
        if isinstance(result, list):
            for item in result:
                if "name" in item:
                    path = item.get("relative_path", item.get("file", "unknown"))
                    print(f"{item['name']} ({item.get('kind', 'unknown')}) - {path}")
                elif "error" in item:
                    print(f"Error: {item['error']}")
                else:
                    print(item)
        else:
            print(result)

if __name__ == "__main__":
    main()
