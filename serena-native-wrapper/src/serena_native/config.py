import os
from pathlib import Path
from typing import Optional

class Config:
    def __init__(self):
        self.project_root = os.environ.get("SERENA_NATIVE_PROJECT_ROOT", os.getcwd())
        self.log_level = os.environ.get("SERENA_NATIVE_LOG_LEVEL", "INFO")
        self.format = "text"

    def set_project_root(self, path: str):
        self.project_root = str(Path(path).resolve())
