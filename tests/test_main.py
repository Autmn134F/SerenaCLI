import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from serena_cli.main import main_async, transform_symbol_result
from mcp.types import TextContent, CallToolResult

@pytest.mark.asyncio
async def test_find_symbol_command():
    with patch("serena_cli.main.stdio_client") as mock_stdio:
        # Mock the context manager
        mock_cm = AsyncMock()
        mock_stdio.return_value = mock_cm
        mock_cm.__aenter__.return_value = (MagicMock(), MagicMock())

        with patch("serena_cli.main.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__.return_value = mock_session
            mock_session.initialize.return_value = None

            # Mock call_tool result
            mock_result = CallToolResult(
                content=[TextContent(
                    type="text",
                    text='[{"name_path": "MyClass/my_method", "kind": 6, "body_location": {"start_line": 10, "end_line": 20}, "relative_path": "src/foo.py"}]'
                )],
                isError=False
            )
            mock_session.call_tool.return_value = mock_result

            # Mock sys.argv
            # We also need to mock shutil.which to ensure check passes
            with patch("shutil.which", return_value="/usr/bin/uvx"):
                 with patch("sys.argv", ["serena-cli", "query", "find-symbol", "--name", "my_method"]):
                    await main_async()

            # Verify call_tool was called with correct args
            mock_session.call_tool.assert_called_with("find_symbol", arguments={"name_path_pattern": "my_method"})

def test_transform_symbol_result():
    item = {
        "name_path": "MyClass/my_method[0]",
        "kind": 6,
        "body_location": {"start_line": 10, "end_line": 20},
        "relative_path": "src/foo.py"
    }
    res = transform_symbol_result(item)
    assert res["name"] == "my_method"
    assert res["kind"] == "method"
    assert res["range"] == {"start_line": 10, "end_line": 20}
    assert res["file"] == "src/foo.py"
    assert res["language"] == "python"

@pytest.mark.asyncio
async def test_find_symbol_language_filter():
    with patch("serena_cli.main.stdio_client") as mock_stdio:
        mock_cm = AsyncMock()
        mock_stdio.return_value = mock_cm
        mock_cm.__aenter__.return_value = (MagicMock(), MagicMock())

        with patch("serena_cli.main.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value = mock_session
            mock_session.__aenter__.return_value = mock_session
            mock_session.initialize.return_value = None

            mock_result = CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps([
                        {"name_path": "foo", "kind": 6, "relative_path": "src/foo.py"},
                        {"name_path": "bar", "kind": 6, "relative_path": "src/bar.ts"}
                    ])
                )],
                isError=False
            )
            mock_session.call_tool.return_value = mock_result

            with patch("shutil.which", return_value="/usr/bin/uvx"):
                 with patch("sys.argv", ["serena-cli", "query", "find-symbol", "--name", "whatever", "--language", "typescript"]):
                     with patch("builtins.print") as mock_print:
                         await main_async()

                         # Gather all calls
                         printed_str = "\n".join([str(call.args[0]) for call in mock_print.call_args_list if call.args])
                         assert "bar" in printed_str
                         assert "foo" not in printed_str
