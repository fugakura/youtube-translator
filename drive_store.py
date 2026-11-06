"""Persist YouTube transcripts in the user's Google Drive via OAuth.

Only requests the drive.file scope, so the app can see files it creates,
not unrelated files in the user's Drive.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_MIME = "application/vnd.google-apps.folder"
ROOT_FOLDER_NAME = "YouTube Translator"
MANIFEST_NAME = "manifest.json"
REQUIRED_KEYS = ("original", "japanese", "bilingual")


def missing_drive_variables() -> list[str]:
    return [
        key for key in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN",
        )
        if not os.environ.get(key, "").strip()
    ]


def new_drive_service():
    missing = missing_drive_variables()
    if missing:
        raise RuntimeError("Google Drive認証情報が未設定です: " + ", ".join(missing))
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"].strip(),
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"].strip(),
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveStore:
    def __init__(self, service):
        self.service = service
        self._root_id: str | None = None

    def _find_child(self, parent_id: str, name: str, mime_type: str | None = None):
        # Always use exact name and a parent folder to avoid unrelated matches.
        query = (
            f"'{_escape_drive_query(parent_id)}' in parents and "
            f"name = '{_escape_drive_query(name)}' and trashed = false"
        )
        if mime_type:
            query += f" and mimeType = '{_escape_drive_query(mime_type)}'"
        response = self.service.files().list(
            q=query,
            fields="nextPageToken,files(id,name,mimeType)",
            page_size=100,
        ).execute()
        files = response.get("files", [])
        return files[0] if files else None

    def _create_folder(self, parent_id: str, name: str):
        return self.service.files().create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
            fields="id,name",
        ).execute()

    def root_folder_id(self) -> str:
        if self._root_id:
            return self._root_id
        existing = self._find_child("root", ROOT_FOLDER_NAME, FOLDER_MIME)
        root = existing or self._create_folder("root", ROOT_FOLDER_NAME)
        self._root_id = root["id"]
        return self._root_id

    def video_folder(self, video_id: str, *, create: bool = False):
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("YouTube動画IDが不正です。")
        parent_id = self.root_folder_id()
        folder = self._find_child(parent_id, video_id, FOLDER_MIME)
        if folder is None and create:
            folder = self._create_folder(parent_id, video_id)
        return folder

    def _read(self, file_id: str) -> str:
        data = self.service.files().get_media(fileId=file_id).execute()
        if isinstance(data, str):
            return data
        return data.decode("utf-8-sig")

    def _write(self, folder_id: str, name: str, content: str, *, mime_type: str):
        data = content.encode("utf-8")
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        existing = self._find_child(folder_id, name)
        if existing:
            return self.service.files().update(
                fileId=existing["id"],
                media_body=media,
                fields="id,name",
            ).execute()
        return self.service.files().create(
            body={"name": name, "parents": [folder_id], "mimeType": mime_type},
            media_body=media,
            fields="id,name",
        ).execute()

    def load(self, video_id: str):
        """Return saved transcripts or None. Do not treat incomplete uploads as hits."""
        folder = self.video_folder(video_id, create=False)
        if not folder:
            return None
        manifest_file = self._find_child(folder["id"], MANIFEST_NAME)
        if not manifest_file:
            return None
        try:
            manifest = json.loads(self._read(manifest_file["id"]))
            if manifest.get("video_id") != video_id or manifest.get("schema_version") != 1:
                raise ValueError("manifest.jsonの動画IDまたはバージョンが一致しません。")
            files = manifest["files"]
            texts = []
            for kind in REQUIRED_KEYS:
                item = files[kind]
                if not item.get("id") or not item.get("name"):
                    raise ValueError(f"{kind}のファイル情報が不完全です。")
                content = self._read(item["id"])
                checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                if checksum != item.get("sha256"):
                    raise ValueError(f"{kind}のファイル整合性を確認できません。")
                texts.append((item["name"], content))
        except (ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
            raise ValueError(
                "Driveに不完全な保存データがあります。Driveのファイルを確認するか、"
                "「既存データを無視して再生成」をオンにしてください。"
            ) from exc

        return {
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "source_language": manifest.get("source_language", "unknown"),
            "title": manifest.get("title", "YouTube翻訳"),
            "texts": texts,
            "drive_folder_url": f"https://drive.google.com/drive/u/0/folders/{folder['id']}",
            "saved_to_drive": True,
            "from_drive": True,
        }

    def save(self, result: dict) -> str:
        """Upsert TXT files first, then commit the manifest last.

        Updating an existing video rewrites the files instead of creating duplicates.
        """
        video_id = result["video_id"]
        folder = self.video_folder(video_id, create=True)
        saved_files = {}
        for kind, (name, content) in zip(REQUIRED_KEYS, result["texts"]):
            uploaded = self._write(folder["id"], name, content, mime_type="text/plain")
            saved_files[kind] = {
                "id": uploaded["id"],
                "name": uploaded["name"],
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        manifest = {
            "schema_version": 1,
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "title": result["title"],
            "source_language": result["source_language"],
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "files": saved_files,
        }
        self._write(
            folder["id"],
            MANIFEST_NAME,
            json.dumps(manifest, ensure_ascii=False, indent=2),
            mime_type="application/json",
        )
        return f"https://drive.google.com/drive/u/0/folders/{folder['id']}"
