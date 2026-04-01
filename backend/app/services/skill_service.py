import hashlib
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.models.agent_store import SkillDependencyModel, SkillInstallRecordModel, SkillModel
from app.services.skill_install_progress_service import skill_install_progress_service
from app.services.skillhub_client import skillhub_client

logger = logging.getLogger(__name__)

class SkillService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.skill_dir = os.path.join(project_root, "skills")
        self.tmp_dir = os.path.join(self.skill_dir, ".tmp")
        os.makedirs(self.skill_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)

    async def scan_local_skills(self, session: Session) -> List[SkillModel]:
        logger.info(f"Scanning skills from {self.skill_dir}")
        synced_skills: List[SkillModel] = []

        if not os.path.exists(self.skill_dir):
            return []

        for entry in os.scandir(self.skill_dir):
            if entry.is_dir() and not entry.name.startswith('.'):
                skill_name = entry.name
                skill_path = entry.path
                readme_path = os.path.join(skill_path, "SKILL.md")

                description = ""
                if os.path.exists(readme_path):
                    try:
                        with open(readme_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            description = content[:200] + "..." if len(content) > 200 else content
                    except Exception as e:
                        logger.warning(f"Failed to read SKILL.md for {skill_name}: {e}")

                # 同步到数据库
                existing = session.exec(select(SkillModel).where(SkillModel.name == skill_name)).first()
                if existing:
                    existing.file_path = skill_path
                    existing.install_dir = skill_path
                    existing.description = description
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    synced_skills.append(existing)
                else:
                    new_skill = SkillModel(
                        name=skill_name,
                        version="0.1.0",
                        description=description,
                        file_path=skill_path,
                        install_dir=skill_path,
                        status="active",
                        install_status="installed",
                        last_install_at=datetime.utcnow(),
                    )
                    session.add(new_skill)
                    synced_skills.append(new_skill)

        try:
            session.commit()
            for s in synced_skills:
                session.refresh(s)
        except Exception as e:
            logger.error(f"Failed to commit scanned skills: {e}")
            session.rollback()
            raise

        return synced_skills

    def get_skill_markdown(self, skill_name: str) -> str:
        skill_path = os.path.join(self.skill_dir, skill_name)
        readme_path = os.path.join(skill_path, "SKILL.md")

        if not os.path.exists(readme_path):
            return ""

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read SKILL.md for {skill_name}: {e}")
            raise ValueError(f"Failed to read skill documentation: {str(e)}")

    def update_skill_markdown(self, skill_name: str, content: str):
        skill_path = os.path.join(self.skill_dir, skill_name)
        if not os.path.exists(skill_path):
            raise ValueError(f"Skill directory {skill_name} does not exist")

        readme_path = os.path.join(skill_path, "SKILL.md")
        if os.path.exists(readme_path):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = f"{readme_path}.{timestamp}.bak"
            try:
                shutil.copy2(readme_path, backup_path)
            except Exception as e:
                logger.warning(f"Failed to backup SKILL.md: {e}")

        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write SKILL.md for {skill_name}: {e}")
            raise ValueError(f"Failed to update skill documentation: {str(e)}")

    def create_skill(self, session: Session, name: str, description: str) -> SkillModel:
        skill_path = os.path.join(self.skill_dir, name)
        if os.path.exists(skill_path):
            raise ValueError(f"Skill {name} already exists")

        try:
            os.makedirs(skill_path)
            readme_path = os.path.join(skill_path, "SKILL.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\n{description}")
            with open(os.path.join(skill_path, "skill.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "name": name,
                    "version": "0.1.0",
                    "description": description,
                    "author": "local",
                    "tags": [],
                    "dependencies": []
                }, ensure_ascii=False, indent=2))

            new_skill = SkillModel(
                name=name,
                version="0.1.0",
                description=description,
                file_path=skill_path,
                install_dir=skill_path,
                status="active",
                source_type="local",
                install_status="installed",
                last_install_at=datetime.utcnow(),
            )
            session.add(new_skill)
            session.commit()
            session.refresh(new_skill)
            return new_skill
        except Exception as e:
            if os.path.exists(skill_path):
                shutil.rmtree(skill_path)
            logger.error(f"Failed to create skill {name}: {e}")
            raise ValueError(f"Failed to create skill: {str(e)}")

    async def install_from_url(self, session: Session, url: str) -> Dict[str, Any]:
        filename = url.split("/")[-1] if url else f"url-skill-{uuid.uuid4().hex[:8]}"
        skill_name = os.path.splitext(filename)[0] or f"url-skill-{uuid.uuid4().hex[:8]}"
        return await self.install_from_hub(
            session=session,
            skill_name=skill_name,
            version=None,
            operator="system",
            source_url=url,
            operation="install",
        )

    async def search_skillhub(
        self,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await skillhub_client.search(name=name, tags=tags, version=version)

    async def list_versions(self, skill_name: str) -> List[str]:
        records = await skillhub_client.search(name=skill_name)
        versions = sorted({item.get("version", "0.0.0") for item in records}, key=self._version_tuple, reverse=True)
        return versions

    async def install_from_hub(
        self,
        session: Session,
        skill_name: str,
        version: Optional[str],
        operator: str,
        source_url: Optional[str] = None,
        operation: str = "install",
        idempotency_key: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        install_task_id = task_id or str(uuid.uuid4())
        skill_install_progress_service.create_task(install_task_id)
        await skill_install_progress_service.publish(install_task_id, "running", 5, "开始校验安装请求")

        target_version = version or "latest"
        resolved_key = idempotency_key or self._build_idempotency_key(skill_name, target_version, operation)

        dup_record = session.exec(
            select(SkillInstallRecordModel).where(
                SkillInstallRecordModel.idempotency_key == resolved_key,
                SkillInstallRecordModel.status == "success",
            )
        ).first()
        if dup_record:
            await skill_install_progress_service.publish(install_task_id, "success", 100, "命中幂等请求，直接返回历史结果")
            return {
                "task_id": install_task_id,
                "idempotent": True,
                "record_id": str(dup_record.id),
                "skill_name": dup_record.skill_name,
                "version": dup_record.target_version,
                "status": "success",
                "message": dup_record.result_message or "already installed",
            }

        record = SkillInstallRecordModel(
            task_id=install_task_id,
            skill_name=skill_name,
            target_version=target_version,
            operation=operation,
            status="running",
            operator=operator,
            idempotency_key=resolved_key,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        staged_root = os.path.join(self.tmp_dir, install_task_id)
        backup_root = os.path.join(self.tmp_dir, f"{install_task_id}_backup")
        os.makedirs(staged_root, exist_ok=True)
        os.makedirs(backup_root, exist_ok=True)

        touched_paths: List[Tuple[str, str]] = []
        try:
            await skill_install_progress_service.publish(install_task_id, "running", 15, "拉取 SkillHub 元信息")
            package = await skillhub_client.get_skill_package(skill_name, version)
            resolved_dependencies = await self._resolve_dependencies(package.get("dependencies", []))
            install_plan = [package] + resolved_dependencies

            await skill_install_progress_service.publish(install_task_id, "running", 30, "准备安装文件")
            self._prepare_stage_files(staged_root, install_plan)

            await skill_install_progress_service.publish(install_task_id, "running", 45, "替换技能目录")
            touched_paths = self._apply_stage_files(staged_root, backup_root, install_plan)

            await skill_install_progress_service.publish(install_task_id, "running", 70, "写入数据库")
            self._upsert_install_result(
                session=session,
                package=package,
                dependencies=resolved_dependencies,
                operator=operator,
                source_url=source_url,
                idempotency_key=resolved_key,
            )

            record.status = "success"
            record.result_message = f"{skill_name}@{package.get('version')} 安装完成"
            record.log_summary = f"dependencies={len(resolved_dependencies)}"
            record.finished_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()

            await skill_install_progress_service.publish(install_task_id, "success", 100, "安装成功")
            return {
                "task_id": install_task_id,
                "idempotent": False,
                "record_id": str(record.id),
                "skill_name": package.get("name"),
                "version": package.get("version"),
                "status": "success",
                "dependencies": resolved_dependencies,
            }
        except Exception as exc:
            session.rollback()
            self._rollback_files(backup_root, touched_paths)
            record.status = "failed"
            record.result_message = str(exc)
            record.log_summary = str(exc)
            record.finished_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()
            await skill_install_progress_service.publish(install_task_id, "failed", 100, f"安装失败: {exc}")
            raise ValueError(str(exc))
        finally:
            shutil.rmtree(staged_root, ignore_errors=True)
            shutil.rmtree(backup_root, ignore_errors=True)

    async def uninstall_skill(self, session: Session, skill_id: uuid.UUID, operator: str) -> SkillModel:
        skill = session.get(SkillModel, skill_id)
        if not skill or skill.is_deleted:
            raise ValueError("Skill not found")

        task_id = str(uuid.uuid4())
        record = SkillInstallRecordModel(
            task_id=task_id,
            skill_name=skill.name,
            target_version=skill.version,
            operation="uninstall",
            status="running",
            operator=operator,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(record)
        session.commit()

        try:
            if skill.install_dir and os.path.exists(skill.install_dir):
                shutil.rmtree(skill.install_dir, ignore_errors=True)
            skill.install_status = "uninstalled"
            skill.status = "inactive"
            skill.is_deleted = True
            skill.updated_at = datetime.utcnow()
            session.add(skill)

            record.status = "success"
            record.result_message = f"{skill.name} 卸载成功"
            record.finished_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()
            session.refresh(skill)
            return skill
        except Exception as exc:
            session.rollback()
            record.status = "failed"
            record.result_message = str(exc)
            record.finished_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            session.add(record)
            session.commit()
            raise ValueError(str(exc))

    async def upgrade_skill(
        self,
        session: Session,
        skill_id: uuid.UUID,
        version: Optional[str],
        operator: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        skill = session.get(SkillModel, skill_id)
        if not skill or skill.is_deleted:
            raise ValueError("Skill not found")
        return await self.install_from_hub(
            session=session,
            skill_name=skill.name,
            version=version,
            operator=operator,
            operation="upgrade",
            idempotency_key=idempotency_key,
        )

    def list_install_records(self, session: Session, offset: int = 0, limit: int = 20) -> List[SkillInstallRecordModel]:
        stmt = select(SkillInstallRecordModel).order_by(SkillInstallRecordModel.started_at.desc()).offset(offset).limit(limit)
        return list(session.exec(stmt))

    async def _resolve_dependencies(self, dependencies: List[Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for dependency in dependencies:
            if isinstance(dependency, str):
                dep_name = dependency
                dep_version = None
                required_version = "*"
            else:
                dep_name = dependency.get("name")
                dep_version = dependency.get("version")
                required_version = dep_version or "*"
            if not dep_name:
                continue
            pkg = await skillhub_client.get_skill_package(dep_name, dep_version)
            pkg["required_version"] = required_version
            result.append(pkg)
        return result

    def _prepare_stage_files(self, staged_root: str, install_plan: List[Dict[str, Any]]):
        for item in install_plan:
            name = item.get("name")
            version = item.get("version", "0.1.0")
            if not name:
                raise ValueError("Invalid package name")
            folder = os.path.join(staged_root, name, version)
            os.makedirs(folder, exist_ok=True)
            readme_path = os.path.join(folder, "SKILL.md")
            manifest_path = os.path.join(folder, "skill.json")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(item.get("description") or f"# {name}\n\n{name} {version}")
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "name": name,
                    "version": version,
                    "author": item.get("author", "unknown"),
                    "tags": item.get("tags", []),
                    "description": item.get("description", ""),
                    "dependencies": item.get("dependencies", []),
                    "source_type": item.get("source_type", "registry"),
                    "source_url": item.get("download_url", ""),
                }, ensure_ascii=False, indent=2))

    def _apply_stage_files(
        self,
        staged_root: str,
        backup_root: str,
        install_plan: List[Dict[str, Any]],
    ) -> List[Tuple[str, str]]:
        touched_paths: List[Tuple[str, str]] = []
        for item in install_plan:
            name = item.get("name")
            version = item.get("version", "0.1.0")
            source_dir = os.path.join(staged_root, name, version)
            target_base = os.path.join(self.skill_dir, name)
            target_dir = os.path.join(target_base, version)
            backup_dir = os.path.join(backup_root, name)

            os.makedirs(target_base, exist_ok=True)
            if os.path.exists(target_dir):
                os.makedirs(backup_dir, exist_ok=True)
                shutil.move(target_dir, os.path.join(backup_dir, version))
            shutil.move(source_dir, target_dir)
            touched_paths.append((target_dir, os.path.join(backup_dir, version)))
        return touched_paths

    def _rollback_files(self, backup_root: str, touched_paths: List[Tuple[str, str]]):
        for target_dir, backup_dir in touched_paths:
            shutil.rmtree(target_dir, ignore_errors=True)
            if backup_dir and os.path.exists(backup_dir):
                os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                shutil.move(backup_dir, target_dir)
        shutil.rmtree(backup_root, ignore_errors=True)

    def _upsert_install_result(
        self,
        session: Session,
        package: Dict[str, Any],
        dependencies: List[Dict[str, Any]],
        operator: str,
        source_url: Optional[str],
        idempotency_key: str,
    ):
        now = datetime.utcnow()
        install_plan = [package] + dependencies
        for item in install_plan:
            name = item.get("name")
            version = item.get("version", "0.1.0")
            skill = session.exec(select(SkillModel).where(SkillModel.name == name)).first()
            install_dir = os.path.join(self.skill_dir, name, version)
            dependency_snapshot = item.get("dependencies", [])
            if skill:
                skill.version = version
                skill.description = item.get("description", "")
                skill.author = item.get("author", "unknown")
                skill.tags = item.get("tags", [])
                skill.source_type = item.get("source_type", "registry")
                skill.source_url = source_url or item.get("download_url", "")
                skill.install_url = source_url or item.get("download_url", "")
                skill.file_path = install_dir
                skill.install_dir = install_dir
                skill.status = "active"
                skill.install_status = "installed"
                skill.dependency_snapshot = dependency_snapshot
                skill.idempotency_key = idempotency_key
                skill.last_install_at = now
                skill.last_error = None
                skill.is_deleted = False
                skill.updated_at = now
                session.add(skill)
            else:
                session.add(
                    SkillModel(
                        name=name,
                        version=version,
                        description=item.get("description", ""),
                        author=item.get("author", "unknown"),
                        tags=item.get("tags", []),
                        source_type=item.get("source_type", "registry"),
                        source_url=source_url or item.get("download_url", ""),
                        install_url=source_url or item.get("download_url", ""),
                        file_path=install_dir,
                        install_dir=install_dir,
                        status="active",
                        install_status="installed",
                        dependency_snapshot=dependency_snapshot,
                        idempotency_key=idempotency_key,
                        last_install_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )

        old_dependencies = session.exec(
            select(SkillDependencyModel).where(
                SkillDependencyModel.skill_name == package.get("name"),
            )
        ).all()
        for item in old_dependencies:
            session.delete(item)

        for dep in dependencies:
            session.add(
                SkillDependencyModel(
                    skill_name=package.get("name"),
                    skill_version=package.get("version", "0.1.0"),
                    dependency_name=dep.get("name"),
                    required_version=dep.get("required_version", dep.get("version", "*")),
                    resolved_version=dep.get("version", "0.1.0"),
                    source=dep.get("source_type", "registry"),
                    created_at=now,
                    updated_at=now,
                )
            )

        session.commit()

    def _build_idempotency_key(self, skill_name: str, version: str, operation: str) -> str:
        raw = f"{skill_name}:{version}:{operation}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _version_tuple(self, value: str):
        parts = []
        for part in str(value).split("."):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

skill_service = SkillService()
