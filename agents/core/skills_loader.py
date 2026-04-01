"""
Agent 能力（技能）加载器。
负责发现、加载和管理 Agent 的技能 (Skills)。
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

# 默认内置技能目录 (相对于项目根目录)
# 假设 agents/core/skills_loader.py 位于 agents/core/，即根目录下的 agents/core/
# 技能位于 root/skills 或 agents/skills
# 这里假设为 root/skills
BUILTIN_SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"

class SkillsLoader:
    """
    Agent 技能加载器类。

    技能通常定义为 Markdown 文件 (SKILL.md)，其中包含教学 Agent 如何使用特定工具或执行特定任务的说明。
    本类负责扫描工作区和内置目录，解析技能元数据，并按需加载技能内容。
    """

    def __init__(self, workspace: Path, builtin_skills_dir: Optional[Path] = None):
        """
        初始化技能加载器。

        Args:
            workspace (Path): 当前工作区路径，用于查找用户定义的技能。
            builtin_skills_dir (Optional[Path]): 内置技能目录路径。如果未提供，使用默认路径。
        """
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR

    def list_skills(self, filter_unavailable: bool = True) -> List[Dict[str, str]]:
        """
        列出所有可用的技能。
        
        扫描工作区技能目录和内置技能目录。
        工作区中的技能优先于同名的内置技能。

        Args:
            filter_unavailable (bool): 如果为 True，则过滤掉未满足依赖要求（如缺少 CLI 工具或环境变量）的技能。
            
        Returns:
            List[Dict[str, str]]: 技能信息字典列表，包含 'name' (名称), 'path' (路径), 'source' (来源: workspace/builtin)。
        """
        skills = []

        # 1. 扫描工作区技能 (Workspace Skills)
        if self.workspace_skills.exists():
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "workspace"})

        # 2. 扫描内置技能 (Built-in Skills)
        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    # 避免重复：如果工作区已有同名技能，则忽略内置技能
                    if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):
                        skills.append({"name": skill_dir.name, "path": str(skill_file), "source": "builtin"})

        # 3. 根据依赖要求过滤
        if filter_unavailable:
            return [s for s in skills if self._check_requirements(self._get_skill_meta(s["name"]))]
        return skills

    def load_skill(self, name: str) -> Optional[str]:
        """
        根据名称加载技能内容。
        
        Args:
            name (str): 技能名称 (通常是目录名)。
            
        Returns:
            str | None: 技能文件的文本内容。如果未找到，返回 None。
        """
        # 优先检查工作区
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill.read_text(encoding="utf-8")

        # 然后检查内置目录
        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill.read_text(encoding="utf-8")

        return None

    def load_skills_for_context(self, skill_names: List[str]) -> str:
        """
        加载指定列表的技能，用于包含在 Agent 的上下文提示词中。
        
        Args:
            skill_names (List[str]): 要加载的技能名称列表。
            
        Returns:
            str: 格式化后的技能内容字符串，包含多个技能的说明。
        """
        parts = []
        for name in skill_names:
            content = self.load_skill(name)
            if content:
                # 移除 Frontmatter 元数据，只保留指令内容
                content = self._strip_frontmatter(content)
                parts.append(f"### Skill: {name}\n\n{content}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def build_skills_summary(self) -> str:
        """
        构建所有技能的摘要信息 (XML 格式)。
        包括名称、描述、路径和可用性状态。

        这个摘要用于渐进式加载——Agent 可以先看到摘要，需要时再使用 read_file 读取完整的技能内容。

        Returns:
            str: XML 格式的技能摘要字符串。
        """
        all_skills = self.list_skills(filter_unavailable=False)
        if not all_skills:
            return ""

        def escape_xml(s: str) -> str:
            """转义 XML 特殊字符"""
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines = ["<skills>"]
        for s in all_skills:
            name = escape_xml(s["name"])
            path = s["path"]
            desc = escape_xml(self._get_skill_description(s["name"]))
            skill_meta = self._get_skill_meta(s["name"])
            available = self._check_requirements(skill_meta)

            lines.append(f"  <skill available=\"{str(available).lower()}\">")
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"    <location>{path}</location>")

            # 如果技能不可用，显示缺失的依赖要求
            if not available:
                missing = self._get_missing_requirements(skill_meta)
                if missing:
                    lines.append(f"    <requires>{escape_xml(missing)}</requires>")

            lines.append("  </skill>")
        lines.append("</skills>")

        return "\n".join(lines)

    def _get_missing_requirements(self, skill_meta: Dict) -> str:
        """
        获取缺失的依赖要求描述。
        
        检查 'requires' 字段中的二进制工具 (bins) 和环境变量 (env)。
        """
        missing = []
        requires = skill_meta.get("requires", {})
        # 检查 CLI 工具
        for b in requires.get("bins", []):
            if not shutil.which(b):
                missing.append(f"CLI: {b}")
        # 检查环境变量
        for env in requires.get("env", []):
            if not os.environ.get(env):
                missing.append(f"ENV: {env}")
        return ", ".join(missing)

    def _get_skill_description(self, name: str) -> str:
        """
        从技能的 Frontmatter 中获取描述信息。
        如果未找到描述，回退使用技能名称。
        """
        meta = self.get_skill_metadata(name)
        if meta and meta.get("description"):
            return meta["description"]
        return name  # Fallback to skill name

    def _strip_frontmatter(self, content: str) -> str:
        """
        从 Markdown 内容中移除 YAML Frontmatter。
        Frontmatter 通常位于文件开头，由 --- 包裹。
        """
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end():].strip()
        return content

    def _parse_nanobot_metadata(self, raw: str) -> Dict:
        """
        解析 Frontmatter 中的技能元数据 JSON。
        支持 'nanobot' 或 'openclaw' 键。
        """
        try:
            data = json.loads(raw)
            return data.get("nanobot", data.get("openclaw", {})) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _check_requirements(self, skill_meta: Dict) -> bool:
        """
        检查技能依赖要求是否满足 (bins, env vars)。
        """
        requires = skill_meta.get("requires", {})
        # 检查必须的二进制工具
        for b in requires.get("bins", []):
            if not shutil.which(b):
                return False
        # 检查必须的环境变量
        for env in requires.get("env", []):
            if not os.environ.get(env):
                return False
        return True

    def _get_skill_meta(self, name: str) -> Dict:
        """
        获取技能的 nanobot 元数据 (缓存于 frontmatter 中)。
        """
        meta = self.get_skill_metadata(name) or {}
        return self._parse_nanobot_metadata(meta.get("metadata", ""))

    def get_always_skills(self) -> List[str]:
        """
        获取标记为 always=true 且满足依赖要求的技能列表。
        这些技能应始终加载到 Agent 上下文中。
        """
        result = []
        # 注意: 调用 list_skills 内部也会调用 _get_skill_meta，这里有少量逻辑重复，但为了清晰起见保留
        for s in self.list_skills(filter_unavailable=True):
            meta = self.get_skill_metadata(s["name"]) or {}
            skill_meta = self._parse_nanobot_metadata(meta.get("metadata", ""))
            # 检查 metadata 中的 'always' 标志，或顶级 frontmatter 中的 'always' 标志
            if skill_meta.get("always") or meta.get("always") == "true":
                result.append(s["name"])
        return result

    def get_skill_metadata(self, name: str) -> Optional[Dict]:
        """
        从技能文件的 Frontmatter 中提取元数据。
        
        Args:
            name (str): 技能名称。
            
        Returns:
            Optional[Dict]: 元数据字典，如果未找到或解析失败则返回 None。
        """
        content = self.load_skill(name)
        if not content:
            return None

        if content.startswith("---"):
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                # 简单的 YAML 解析 (key: value)
                metadata = {}
                for line in match.group(1).split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip('"\'')
                return metadata

        return None
