import shutil
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BackupService:
    """
    提供数据备份服务的类，主要用于备份 ChromaDB 向量数据库的数据。
    """
    
    def __init__(self):
        """
        初始化备份服务，配置基础目录、数据目录和备份存储目录。
        如果备份目录不存在，则自动创建。
        """
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(self.base_dir, "data", "chroma_db")
        self.backup_dir = os.path.join(self.base_dir, "backups")
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self) -> str:
        """
        创建 ChromaDB 数据目录的 ZIP 压缩包备份。

        业务逻辑：
        1. 检查数据目录是否存在。
        2. 生成带有时间戳的备份文件名。
        3. 使用 shutil.make_archive 创建 ZIP 压缩包。

        Returns:
            str: 成功创建的备份文件绝对路径。

        Raises:
            FileNotFoundError: 数据目录不存在时抛出。
            Exception: 创建备份失败时抛出。
        """
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError("ChromaDB data directory not found")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"chroma_backup_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            # shutil.make_archive creates the zip file / 创建 ZIP 压缩包
            shutil.make_archive(backup_path, 'zip', self.data_dir)
            logger.info(f"Backup created at {backup_path}.zip")
            return f"{backup_path}.zip"
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise e

    def list_backups(self):
        """
        列出所有可用的备份文件列表。

        Returns:
            List[str]: 备份文件名称列表，按时间倒序排列（最新的在前面）。
        """
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = [f for f in os.listdir(self.backup_dir) if f.endswith('.zip')]
        backups.sort(reverse=True) # Newest first / 最新优先
        return backups

backup_service = BackupService()
