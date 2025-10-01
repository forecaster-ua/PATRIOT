# storage.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
import json, os, time

# -------- Local storage --------
class LocalStorage:
    def __init__(self, base_dir: str = "HEDGE.BOT.HISTORY"):
        self.base = Path(base_dir)
        self.base.mkdir(exist_ok=True)

    def write_text(self, ticker: str, filename: str, content: str) -> Path:
        d = self.base / ticker
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(content, encoding="utf-8")
        return p

# -------- Google Drive (Service Account only) --------
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    DRIVE_AVAILABLE = True
except ImportError:
    print("⚠️ Google API libraries not installed. Drive upload disabled.")
    DRIVE_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class DriveStorage:
    def __init__(self, enabled: bool):
        self.enabled = bool(int(os.getenv("GDRIVE_UPLOAD", "0"))) and enabled and DRIVE_AVAILABLE
        self.service = None
        self.parent_id = os.getenv("GDRIVE_PARENT_ID") or None
        self.cache_path = os.getenv("GDRIVE_CACHE", ".gdrive_cache.json")
        self._cache = {}
        if self.enabled:
            self._init_drive()
            self._load_cache()

    # --- cache helpers ---
    def _load_cache(self):
        try:
            if self.cache_path and Path(self.cache_path).exists():
                self._cache = json.loads(Path(self.cache_path).read_text(encoding="utf-8"))
        except Exception:
            self._cache = {}

    def _save_cache(self):
        try:
            if self.cache_path:
                Path(self.cache_path).write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass  # cache errors must never break pipeline

    # --- auth ---
    def _init_drive(self):
        try:
            sa_path = os.getenv("GDRIVE_SA_JSON")
            if not sa_path or not Path(sa_path).exists():
                print("GDRIVE: Service account JSON not found. Continue with local only.")
                self.enabled = False
                return
                
            creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f"GDRIVE: init error → {e}. Continue with local only.")
            self.enabled = False

    # --- folder ops ---
    def ensure_folder(self, *path_parts: str) -> Optional[str]:
        if not self.enabled:
            return None
        parent = self.parent_id
        for name in path_parts:
            key = f"{parent or 'root'}::{name}"
            folder_id = self._cache.get(key)
            if not folder_id:
                folder_id = self._get_or_create_folder(name, parent)
                if not folder_id:
                    return None
                self._cache[key] = folder_id
                self._save_cache()
            parent = folder_id
        return parent

    def _get_or_create_folder(self, name: str, parent_id: Optional[str]) -> Optional[str]:
        try:
            # Escape single quotes in name for query
            escaped_name = name.replace("'", "\\'")
            q = f"mimeType='application/vnd.google-apps.folder' and name='{escaped_name}' and trashed=false"
            if parent_id:
                q += f" and '{parent_id}' in parents"
            
            items = self._retry(lambda: self.service.files().list(q=q, fields="files(id)", pageSize=10))
            files = items.get("files", []) if items else []
            if files:
                return files[0]["id"]
                
            metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
            if parent_id:
                metadata["parents"] = [parent_id]
            created = self._retry(lambda: self.service.files().create(body=metadata, fields="id"))
            return created["id"] if created else None
        except Exception as e:
            print(f"GDRIVE: folder creation failed → {e}")
            return None

    # --- upload ---
    def upload_file(self, local_path: Path, folder_id: Optional[str]) -> Optional[str]:
        if not (self.enabled and folder_id):
            return None
        try:
            media = MediaFileUpload(str(local_path), resumable=True)
            metadata = {"name": local_path.name, "parents": [folder_id]}
            created = self._retry(lambda: self.service.files().create(body=metadata, media_body=media, fields="id"))
            return created.get("id") if created else None
        except Exception as e:
            print(f"GDRIVE: upload failed → {e}")
            return None

    # --- generic retry wrapper ---
    def _retry(self, req_factory, tries: int = 3, base_sleep: float = 1.0):
        for i in range(tries):
            try:
                return req_factory().execute()
            except Exception as e:
                msg = str(e)
                if i == tries - 1:
                    print(f"GDRIVE: request failed (no more retries): {msg}")
                    raise
                # crude backoff; respect Retry-After if present
                sleep_s = base_sleep * (2 ** i)
                print(f"GDRIVE: retry {i+1}/{tries} after {sleep_s}s...")
                time.sleep(sleep_s)
        return None