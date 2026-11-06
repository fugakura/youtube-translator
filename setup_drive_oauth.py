"""One-time Google OAuth authorization on your own PC.

1. Download Desktop OAuth credentials from Google Cloud as credentials.json.
2. Run: python setup_drive_oauth.py
3. Copy the three printed values into Railway Variables (never GitHub).
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_PATH = Path(__file__).resolve().parent / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    if not CREDENTIALS_PATH.exists():
        raise SystemExit(
            "credentials.jsonが見つかりません。Google Cloudでデスクトップアプリの"
            "OAuthクライアントを作成し、このフォルダに保存してください。"
        )
    with CREDENTIALS_PATH.open(encoding="utf-8") as file:
        config = json.load(file)
    installed = config.get("installed")
    if not installed:
        raise SystemExit("credentials.jsonは『デスクトップアプリ』のOAuthクライアントを使用してください。")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        raise SystemExit("refresh tokenが取得できませんでした。再度同意画面を通してください。")

    print("\nRailway → Variables に次の3つを登録してください。")
    print("注意：以下は認証情報です。GitHubやチャットには貼らないでください。\n")
    print("GOOGLE_CLIENT_ID=" + installed["client_id"])
    print("GOOGLE_CLIENT_SECRET=" + installed["client_secret"])
    print("GOOGLE_REFRESH_TOKEN=" + credentials.refresh_token)
    print("\n登録後はこの端末の表示内容も慎重に扱ってください。")


if __name__ == "__main__":
    main()
