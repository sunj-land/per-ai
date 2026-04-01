import os
import shutil
import aiofiles
from datetime import datetime
from fastapi import UploadFile, HTTPException

class StorageService:
    def __init__(self):
        # Default to 'data/attachments' relative to project root
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.base_dir = os.getenv("ATTACHMENT_DIR", os.path.join(self.root_dir, "data", "attachments"))
        
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    async def save_file(self, file: UploadFile, uuid: str, ext: str) -> tuple[str, str]:
        """
        Save uploaded file to storage.
        Returns: (relative_path, absolute_path)
        """
        date_folder = datetime.now().strftime("%Y%m%d")
        directory = os.path.join(self.base_dir, date_folder)
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        filename = f"{uuid}{ext}"
        relative_path = os.path.join(date_folder, filename)
        absolute_path = os.path.join(self.base_dir, relative_path)
        
        try:
            async with aiofiles.open(absolute_path, 'wb') as out_file:
                while content := await file.read(1024 * 1024):  # 1MB chunks
                    await out_file.write(content)
            # Reset file pointer just in case
            await file.seek(0)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
            
        return relative_path, absolute_path

    def get_absolute_path(self, relative_path: str) -> str:
        return os.path.join(self.base_dir, relative_path)

    def delete_file(self, relative_path: str):
        absolute_path = self.get_absolute_path(relative_path)
        if os.path.exists(absolute_path):
            try:
                os.remove(absolute_path)
            except OSError:
                pass

storage_service = StorageService()
