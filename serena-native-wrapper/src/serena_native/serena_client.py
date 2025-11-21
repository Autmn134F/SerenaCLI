"""
Client for interacting with Serena.
"""
import logging
import sys
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

# Since we are in a wrapper, we try to import serena.
# In a real environment, serena-agent should be installed.
try:
    from serena.agent import SerenaAgent, ProjectNotFoundError
    from serena.tools.symbol_tools import (
        FindSymbolTool,
        GetSymbolsOverviewTool,
        FindReferencingSymbolsTool,
    )
    SERENA_AVAILABLE = True
except ImportError:
    SERENA_AVAILABLE = False
    # For type checking
    SerenaAgent = Any

from serena_native.logging_utils import log_info, log_error


class SerenaClient:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.agent: Optional[SerenaAgent] = None

        if not SERENA_AVAILABLE:
            log_error("Serena is not installed or not found in python path.")
            return

    def ensure_agent(self):
        if not SERENA_AVAILABLE:
            raise RuntimeError("Serena is not available.")

        if self.agent is None:
            # Initialize agent without project first
            try:
                self.agent = SerenaAgent(project=None)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Serena agent: {e}")

    def init_project(self) -> Dict[str, Any]:
        self.ensure_agent()
        try:
            project, created = self.agent.activate_project_from_path_or_name(self.project_root)
            return {
                "status": "ok",
                "project_name": project.project_name,
                "project_root": project.project_root,
                "created": created
            }
        except Exception as e:
             # Try to load it if it exists
            try:
                 project = self.agent.load_project_from_path_or_name(self.project_root, autogenerate=True)
                 if project:
                     return {
                        "status": "ok",
                        "project_name": project.project_name,
                        "project_root": project.project_root,
                        "created": False
                     }
            except Exception:
                pass
            raise RuntimeError(f"Failed to init project: {e}")

    def index_project(self) -> Dict[str, Any]:
        self.ensure_agent()
        try:
            # Activation triggers indexing if in LS mode
            project, _ = self.agent.activate_project_from_path_or_name(self.project_root)

            # Wait for indexing if needed (Serena usually does this async but we might want to block or check status)
            # The agent.activate_project_from_path_or_name triggers reset_language_server_manager
            # which issues a task. We can wait for tasks.

            # We can force a reset to ensure it's running
            self.agent.reset_language_server_manager()

            # Wait for tasks to complete?
            # self.agent._task_executor.join() # If exposed

            return {"status": "indexing_triggered", "project": project.project_name}
        except Exception as e:
             raise RuntimeError(f"Failed to index project: {e}")

    def get_status(self) -> Dict[str, Any]:
        status = {
            "serena_available": SERENA_AVAILABLE,
            "project_detected": False,
            "index_state": "unknown"
        }

        if SERENA_AVAILABLE:
            try:
                self.ensure_agent()
                project = self.agent.serena_config.get_project(self.project_root)
                if project:
                    status["project_detected"] = True
                    # In a real scenario we'd check if LS is running
                    status["index_state"] = "configured"
            except Exception:
                pass

        return status

    def find_symbol(self, name: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        self.ensure_agent()
        # Ensure project is active
        self.agent.activate_project_from_path_or_name(self.project_root)

        tool = self.agent.get_tool(FindSymbolTool)
        result_json = tool.apply(name_path_pattern=name)
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return [{"error": "Failed to parse JSON response", "raw": result_json}]

    def file_overview(self, path: str) -> List[Dict[str, Any]]:
        self.ensure_agent()
        self.agent.activate_project_from_path_or_name(self.project_root)

        tool = self.agent.get_tool(GetSymbolsOverviewTool)
        # relative path needed
        rel_path = os.path.relpath(path, self.project_root)
        result_json = tool.apply(relative_path=rel_path)
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return [{"error": "Failed to parse JSON response", "raw": result_json}]

    def find_references(self, name: str, path: str) -> List[Dict[str, Any]]:
        self.ensure_agent()
        self.agent.activate_project_from_path_or_name(self.project_root)

        tool = self.agent.get_tool(FindReferencingSymbolsTool)
        rel_path = os.path.relpath(path, self.project_root)
        result_json = tool.apply(name_path=name, relative_path=rel_path)
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return [{"error": "Failed to parse JSON response", "raw": result_json}]
