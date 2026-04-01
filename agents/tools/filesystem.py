"""
文件系统工具集 (Filesystem Tools)。
提供读取、写入、编辑文件以及列出目录内容的功能。
"""

import difflib
import os
from pathlib import Path
from typing import Any, List, Optional

from tools.base import Tool


def _resolve_path(
    path: str,
    workspace: Optional[Path] = None,
    allowed_dir: Optional[Path] = None,
    extra_allowed_dirs: Optional[List[Path]] = None,
) -> Path:
    """
    解析路径并进行安全检查。

    1. 如果路径是相对路径且提供了 workspace，则将其解析为相对于 workspace 的绝对路径。
    2. 如果设置了 allowed_dir，则检查解析后的路径是否在该目录（或 extra_allowed_dirs）下，防止越权访问。

    Args:
        path (str): 原始路径字符串。
        workspace (Optional[Path]): 工作区根目录。
        allowed_dir (Optional[Path]): 主要允许访问的目录限制。
        extra_allowed_dirs (Optional[List[Path]]): 额外允许访问的目录列表。

    Returns:
        Path: 解析后的绝对路径。

    Raises:
        PermissionError: 如果路径超出允许范围。
    """
    p = Path(path).expanduser()
    if not p.is_absolute() and workspace:
        p = workspace / p
    resolved = p.resolve()
    if allowed_dir:
        all_dirs = [allowed_dir] + (extra_allowed_dirs or [])
        if not any(_is_under(resolved, d) for d in all_dirs):
            raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
    return resolved


def _is_under(path: Path, directory: Path) -> bool:
    """检查 path 是否在 directory 目录下。"""
    try:
        path.relative_to(directory.resolve())
        return True
    except ValueError:
        return False


class _FsTool(Tool):
    """
    文件系统工具的共享基类。
    提供通用的初始化和路径解析逻辑。
    """

    def __init__(
        self,
        workspace: Optional[Path] = None,
        allowed_dir: Optional[Path] = None,
        extra_allowed_dirs: Optional[List[Path]] = None,
    ):
        """
        初始化文件系统工具。

        Args:
            workspace (Optional[Path]): 工作区路径。
            allowed_dir (Optional[Path]): 安全限制目录。
            extra_allowed_dirs (Optional[List[Path]]): 额外允许的目录。
        """
        self._workspace = workspace
        self._allowed_dir = allowed_dir
        self._extra_allowed_dirs = extra_allowed_dirs

    def _resolve(self, path: str) -> Path:
        """调用全局 _resolve_path 进行路径解析。"""
        return _resolve_path(path, self._workspace, self._allowed_dir, self._extra_allowed_dirs)


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class ReadFileTool(_FsTool):
    """
    读取文件内容工具。
    支持按行号分页读取，适用于大文件。
    """

    _MAX_CHARS = 128_000  # 最大字符数限制
    _DEFAULT_LIMIT = 2000  # 默认读取行数限制

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. Returns numbered lines. "
            "Use offset and limit to paginate through large files."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to read"},
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed, default 1)",
                    "minimum": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default 2000)",
                    "minimum": 1,
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, offset: int = 1, limit: Optional[int] = None, **kwargs: Any) -> str:
        """
        执行读取文件操作。

        Args:
            path (str): 文件路径。
            offset (int): 起始行号 (从1开始)。
            limit (Optional[int]): 读取行数限制。

        Returns:
            str: 带有行号的文件内容字符串，或错误信息。
        """
        try:
            fp = self._resolve(path)
            if not fp.exists():
                return f"Error: File not found: {path}"
            if not fp.is_file():
                return f"Error: Not a file: {path}"

            all_lines = fp.read_text(encoding="utf-8").splitlines()
            total = len(all_lines)

            if offset < 1:
                offset = 1
            if total == 0:
                return f"(Empty file: {path})"
            if offset > total:
                return f"Error: offset {offset} is beyond end of file ({total} lines)"

            start = offset - 1
            end = min(start + (limit or self._DEFAULT_LIMIT), total)
            numbered = [f"{start + i + 1}| {line}" for i, line in enumerate(all_lines[start:end])]
            result = "\n".join(numbered)

            # 字符数限制截断
            if len(result) > self._MAX_CHARS:
                trimmed, chars = [], 0
                for line in numbered:
                    chars += len(line) + 1
                    if chars > self._MAX_CHARS:
                        break
                    trimmed.append(line)
                end = start + len(trimmed)
                result = "\n".join(trimmed)

            # 添加分页提示
            if end < total:
                result += f"\n\n(Showing lines {offset}-{end} of {total}. Use offset={end + 1} to continue.)"
            else:
                result += f"\n\n(End of file — {total} lines total)"
            return result
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file: {e}"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

class WriteFileTool(_FsTool):
    """
    写入文件内容工具。
    如果文件不存在则创建，如果父目录不存在也会自动创建。
    """

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file at the given path. Creates parent directories if needed."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to write to"},
                "content": {"type": "string", "description": "The content to write"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        """
        执行写入文件操作。

        Args:
            path (str): 文件路径。
            content (str): 要写入的内容。

        Returns:
            str: 成功消息或错误信息。
        """
        try:
            fp = self._resolve(path)
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {fp}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error writing file: {e}"


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------

def _find_match(content: str, old_text: str) -> tuple[Optional[str], int]:
    """
    在内容中查找 old_text。
    首先尝试精确匹配，如果失败则尝试忽略行首尾空白的滑动窗口匹配。

    Args:
        content (str): 目标内容。
        old_text (str): 要查找的文本块。

    Returns:
        tuple[Optional[str], int]: (匹配到的实际文本片段, 匹配次数)。如果没有匹配，返回 (None, 0)。
    """
    if old_text in content:
        return old_text, content.count(old_text)

    old_lines = old_text.splitlines()
    if not old_lines:
        return None, 0
    stripped_old = [l.strip() for l in old_lines]
    content_lines = content.splitlines()

    candidates = []
    # 滑动窗口查找
    for i in range(len(content_lines) - len(stripped_old) + 1):
        window = content_lines[i : i + len(stripped_old)]
        if [l.strip() for l in window] == stripped_old:
            candidates.append("\n".join(window))

    if candidates:
        return candidates[0], len(candidates)
    return None, 0


class EditFileTool(_FsTool):
    """
    编辑文件工具。
    通过查找 old_text 并替换为 new_text 来修改文件。
    支持容错匹配（忽略空白字符差异）。
    """

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing old_text with new_text. "
            "Supports minor whitespace/line-ending differences. "
            "Set replace_all=true to replace every occurrence."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to edit"},
                "old_text": {"type": "string", "description": "The text to find and replace"},
                "new_text": {"type": "string", "description": "The text to replace with"},
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default false)",
                },
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(
        self, path: str, old_text: str, new_text: str,
        replace_all: bool = False, **kwargs: Any,
    ) -> str:
        """
        执行文件编辑操作。

        Args:
            path (str): 文件路径。
            old_text (str): 要查找并替换的旧文本块。
            new_text (str): 新文本块。
            replace_all (bool): 是否替换所有匹配项。

        Returns:
            str: 成功消息或错误信息。
        """
        try:
            fp = self._resolve(path)
            if not fp.exists():
                return f"Error: File not found: {path}"

            raw = fp.read_bytes()
            uses_crlf = b"\r\n" in raw
            content = raw.decode("utf-8").replace("\r\n", "\n")
            # 尝试查找匹配
            match, count = _find_match(content, old_text.replace("\r\n", "\n"))

            if match is None:
                return self._not_found_msg(old_text, content, path)
            if count > 1 and not replace_all:
                return (
                    f"Warning: old_text appears {count} times. "
                    "Provide more context to make it unique, or set replace_all=true."
                )

            norm_new = new_text.replace("\r\n", "\n")
            # 执行替换
            new_content = content.replace(match, norm_new) if replace_all else content.replace(match, norm_new, 1)
            # 恢复 CRLF (如果原文件使用)
            if uses_crlf:
                new_content = new_content.replace("\n", "\r\n")

            fp.write_bytes(new_content.encode("utf-8"))
            return f"Successfully edited {fp}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error editing file: {e}"

    @staticmethod
    def _not_found_msg(old_text: str, content: str, path: str) -> str:
        """生成详细的 '未找到匹配项' 错误消息，包含 diff 建议。"""
        lines = content.splitlines(keepends=True)
        old_lines = old_text.splitlines(keepends=True)
        window = len(old_lines)

        best_ratio, best_start = 0.0, 0
        # 寻找最相似的片段
        for i in range(max(1, len(lines) - window + 1)):
            ratio = difflib.SequenceMatcher(None, old_lines, lines[i : i + window]).ratio()
            if ratio > best_ratio:
                best_ratio, best_start = ratio, i

        if best_ratio > 0.5:
            diff = "\n".join(difflib.unified_diff(
                old_lines, lines[best_start : best_start + window],
                fromfile="old_text (provided)",
                tofile=f"{path} (actual, line {best_start + 1})",
                lineterm="",
            ))
            return f"Error: old_text not found in {path}.\nBest match ({best_ratio:.0%} similar) at line {best_start + 1}:\n{diff}"
        return f"Error: old_text not found in {path}. No similar text found. Verify the file content."


class ListDirTool(_FsTool):
    """
    列出目录内容工具。
    显示文件和子目录列表。
    """

    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List files and directories in the given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory path to list"},
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        """
        执行列出目录操作。

        Args:
            path (str): 目录路径。

        Returns:
            str: 格式化的目录列表字符串，或错误信息。
        """
        try:
            p = self._resolve(path)
            if not p.exists():
                return f"Error: Path not found: {path}"
            if not p.is_dir():
                return f"Error: Not a directory: {path}"

            items = sorted(os.listdir(p))
            result = []
            for item in items:
                full_path = p / item
                type_str = "DIR " if full_path.is_dir() else "FILE"
                result.append(f"{type_str:4} {item}")

            return "\n".join(result) or "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"
