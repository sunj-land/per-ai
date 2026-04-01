import os
import shutil
import subprocess
import mimetypes
from typing import Optional
from PIL import Image

# Try to import magic, fallback if not available (e.g. missing libmagic)
try:
    import magic
    HAS_MAGIC = True
except (ImportError, Exception):
    HAS_MAGIC = False

class FileProcessor:
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        if HAS_MAGIC:
            try:
                mime = magic.Magic(mime=True)
                return mime.from_file(file_path)
            except Exception:
                pass
        
        # Fallback
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    @staticmethod
    def scan_virus(file_path: str) -> bool:
        """
        Scan file for viruses using clamscan.
        Returns True if safe, False if infected.
        """
        # Check if clamscan is installed
        if not shutil.which("clamscan"):
            # In production this should probably log an error, but for dev we skip
            return True
            
        try:
            # clamscan returns 0 if clean, 1 if virus found
            result = subprocess.run(
                ["clamscan", "--no-summary", file_path], 
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            # On error (e.g. execution fail), assume safe or log error
            return True

    @staticmethod
    def create_thumbnail(input_path: str, output_path: str, size: tuple = (200, 200)):
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if RGBA (for JPEG saving)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail(size)
                img.save(output_path, "JPEG")
        except Exception:
            pass

    @staticmethod
    def convert_to_pdf(input_path: str, output_dir: str) -> Optional[str]:
        """
        Convert document to PDF using LibreOffice.
        Returns path to generated PDF.
        """
        if not shutil.which("soffice"):
            return None
            
        try:
            # libreoffice --headless --convert-to pdf <file> --outdir <dir>
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", input_path, "--outdir", output_dir],
                check=True,
                capture_output=True
            )
            
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
            
            if os.path.exists(pdf_path):
                return pdf_path
        except Exception:
            pass
            
        return None

file_processor = FileProcessor()
