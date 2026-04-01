import os
from pathlib import Path
from sqlalchemy import event, text
from sqlmodel import SQLModel, Session, create_engine

# Ensure data directory exists
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

sqlite_file_name = os.path.join(data_dir, "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

def _cleanup_sqlite_wal_files() -> None:
    db_path = Path(sqlite_file_name)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.exists():
            backup = sidecar.with_name(f"{sidecar.name}.corrupt")
            if backup.exists():
                backup.unlink()
            sidecar.rename(backup)

# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
    except Exception as exc:
        if "file is not a database" not in str(exc).lower():
            raise
        cursor.close()
        _cleanup_sqlite_wal_files()
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


def _get_table_columns(session: Session, table_name: str) -> set[str]:
    """
    获取 SQLite 指定表的字段集合。
    :param session: 数据库会话。
    :param table_name: 目标表名。
    :return: 字段名集合。
    """
    rows = session.exec(text(f"PRAGMA table_info({table_name})")).all()
    return {row[1] for row in rows}


def _ensure_columns(session: Session, table_name: str, required_columns: dict[str, str]) -> None:
    """
    为已有表补齐缺失字段，避免历史库结构与模型定义不一致。
    :param session: 数据库会话。
    :param table_name: 目标表名。
    :param required_columns: 字段定义映射，key 为字段名，value 为 SQLite 字段类型定义。
    :return: 无返回值。
    """
    existing_columns = _get_table_columns(session, table_name)

    # ========== 步骤1：逐个检查字段是否缺失 ==========
    for column_name, column_definition in required_columns.items():
        # 仅在缺失时执行补齐，避免重复 ALTER TABLE 报错。
        if column_name in existing_columns:
            continue

        # ========== 步骤2：执行字段补齐 ==========
        session.exec(
            text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_definition}"
            )
        )


def migrate_skill_schema() -> None:
    """
    迁移 skill_store 表结构，补齐历史版本缺失字段。
    :return: 无返回值。
    """
    required_columns = {
        "version": "VARCHAR NOT NULL DEFAULT '0.1.0'",
        "author": "VARCHAR DEFAULT NULL",
        "tags": "JSON DEFAULT NULL",
        "source_type": "VARCHAR NOT NULL DEFAULT 'local'",
        "source_url": "VARCHAR DEFAULT NULL",
        "install_dir": "VARCHAR DEFAULT NULL",
        "install_status": "VARCHAR NOT NULL DEFAULT 'installed'",
        "dependency_snapshot": "JSON DEFAULT NULL",
        "idempotency_key": "VARCHAR DEFAULT NULL",
        "last_install_at": "DATETIME DEFAULT NULL",
        "last_error": "TEXT DEFAULT NULL",
        "is_deleted": "BOOLEAN NOT NULL DEFAULT 0",
    }

    with Session(engine) as session:
        # ========== 步骤1：仅在 skill_store 存在时执行迁移 ==========
        table_exists = session.exec(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='skill_store'"
            )
        ).first()
        if not table_exists:
            return

        # ========== 步骤2：补齐缺失字段 ==========
        _ensure_columns(session, "skill_store", required_columns)

        # ========== 步骤3：补齐索引 ==========
        session.exec(
            text(
                "CREATE INDEX IF NOT EXISTS idx_skill_store_version "
                "ON skill_store(version)"
            )
        )
        session.exec(
            text(
                "CREATE INDEX IF NOT EXISTS idx_skill_store_idempotency_key "
                "ON skill_store(idempotency_key)"
            )
        )
        session.commit()


def migrate_user_schema() -> None:
    """
    迁移 user 表结构，补齐缺失字段。
    :return: 无返回值。
    """
    required_columns = {
        "phone": "VARCHAR(20) DEFAULT NULL",
        "salt": "VARCHAR(255) DEFAULT NULL",
        "role_id": "INTEGER DEFAULT NULL",
        "status": "VARCHAR NOT NULL DEFAULT 'active'",
        "extension_json": "JSON DEFAULT NULL",
        "ext_1": "VARCHAR(255) DEFAULT NULL",
        "ext_2": "VARCHAR(255) DEFAULT NULL",
        "ext_3": "VARCHAR(255) DEFAULT NULL",
        "int_1": "INTEGER DEFAULT NULL",
        "int_2": "INTEGER DEFAULT NULL",
        "int_3": "INTEGER DEFAULT NULL",
        "failed_login_count": "INTEGER DEFAULT 0",
        "locked_until": "DATETIME DEFAULT NULL",
        "reset_token": "VARCHAR(255) DEFAULT NULL",
        "reset_token_expires_at": "DATETIME DEFAULT NULL"
    }
    with Session(engine) as session:
        # ========== 步骤1：仅在 user 存在时执行迁移 ==========
        table_exists = session.exec(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='user'"
            )
        ).first()
        if not table_exists:
            return

        # ========== 步骤2：补齐缺失字段 ==========
        _ensure_columns(session, "user", required_columns)
        session.commit()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    migrate_skill_schema()
    migrate_user_schema()

def get_session():
    with Session(engine) as session:
        yield session
