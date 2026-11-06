# YouTube Translator — Google Drive 連携版

YouTubeの字幕（取得できなければ音声）を文字起こしし、OpenAI APIで日本語訳を作成するStreamlitアプリです。WebshareプロキシとRailwayに対応しています。Cosense機能は削除しました。

## 保存仕様

Google Driveにアプリが作成した `YouTube Translator` フォルダを使います。各動画のYouTube動画IDごとにサブフォルダを作成し、以下を保存します。

```text
My Drive/
  YouTube Translator/
    48B5noDTy90/
      48B5noDTy90_original.txt
      48B5noDTy90_japanese.txt
      48B5noDTy90_bilingual.txt
      manifest.json
```

`manifest.json` に動画ID・正規化したYouTubeリンク・タイトル・言語・保存日時・3ファイルの情報を保存します。

動画URLを貼り付けて実行すると、**先にDriveを検索**します。保存済みデータがあればDriveから読み出して画面に表示し、OpenAI APIは呼びません。`youtu.be/VIDEO_ID` と `youtube.com/watch?v=VIDEO_ID` も同一動画として扱います。再生成チェックを入れた場合のみ再処理・上書きします。ファイル整合性が壊れている場合はエラーを表示します。

## 1. Google Cloudの初期設定（初回のみ）

Google DriveをこのRailwayアプリ自身から操作するには、**Google Drive API用のOAuth認証**が必要です。ChatGPTのGoogle Drive連携とは別の設定です。

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成または選択。
2. `API とサービス` → `ライブラリ` から **Google Drive API** を有効にする。
3. `Google Auth Platform`（またはOAuth同意画面）でアプリを設定する。利用者が自分だけなら `External` でも構いません。`Testing` の場合は自分のGoogleアカウントをテストユーザーに追加する。
4. データアクセス／スコープに `https://www.googleapis.com/auth/drive.file` を指定する。このアプリが自分で作成したファイルのみを扱う権限です。
5. `Google Auth Platform` → `Clients`（または `認証情報` → `OAuthクライアントIDを作成`）→ **デスクトップアプリ** を選択する。
6. OAuthクライアントのJSONをダウンロードして `credentials.json` とリネームし、`setup_drive_oauth.py` と同じフォルダに配置する。
7. **自分のPC** のPowerShellで次を実行する。

```powershell
cd "C:\Users\fugak\OneDrive\Desktop\youtube-translator"
py -m pip install -r requirements.txt
py setup_drive_oauth.py
```

Googleの認可画面がブラウザで開きます。Driveへのアクセスに同意すると、PowerShellに3つの値が表示されます。**これらをGitHubへアップロードしないでください。** `credentials.json` は `.gitignore` で除外しています。

> 注意: 外部向けOAuthアプリを `Testing` のまま運用すると、Googleのリフレッシュトークンは原則**7日で期限切れ**になります。常時運用する場合はGoogle Cloud側で公開ステータスを `In production` に変更する必要があります。アプリ公開・認証審査の要否はGoogle Cloud Consoleの表示に従って確認してください。

## 2. Railwayの環境変数

Railway → 対象サービス → `Variables` で次を登録します。

| Variable | 内容 |
|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー（既存値を維持） |
| `APP_PASSWORD` | アプリのログインパスワード（既存値を維持） |
| `WEBSHARE_PROXY_USERNAME` | Webshareのプロキシ用Username（既存値を維持） |
| `WEBSHARE_PROXY_PASSWORD` | Webshareのプロキシ用Password（既存値を維持） |
| `GOOGLE_CLIENT_ID` | 上記スクリプトの表示値 |
| `GOOGLE_CLIENT_SECRET` | 上記スクリプトの表示値 |
| `GOOGLE_REFRESH_TOKEN` | 上記スクリプトの表示値 |

`YOUTUBE_PROXY_URL` を使っている場合は、Webshareの2変数の代わりに指定しても動きます（`YOUTUBE_PROXY_URL`が優先されます）。

旧 `COSENSE_PAT` / `COSENSE_PROJECT` は不要です。削除して問題ありません。

## 3. GitHubにpushしてRailwayを更新

新しい `app.py`、`drive_store.py`、`setup_drive_oauth.py`、`requirements.txt`、`.gitignore`、`railpack.json`、`.env.example`、`README.md` を同じリポジトリのルートに配置します。

```powershell
git add app.py drive_store.py setup_drive_oauth.py requirements.txt .gitignore railpack.json .env.example README.md
git commit -m "Replace Cosense with Google Drive transcript cache"
git push origin main
```

Railwayのデプロイが完了し、Variablesの変更も反映されていることを確認してください。

## 4. 動作確認

1. **初回**: URLを入力 → `保存済みデータを検索 / なければ文字起こし・翻訳` を押す → 翻訳とDrive保存が完了する。
2. **2回目**: 同じ動画URLを入力 → 同じボタンを押す → `保存済みの翻訳が見つかりました` と表示され、Drive上のテキストが使われる。
3. **再生成**: `既存データを無視して再生成する` をオン → 同じ動画を再処理し、Drive上の3ファイルとマニフェストを更新する。OpenAI API料金が発生する。

Drive保存に失敗した場合でも、生成済みのテキストは画面からダウンロードできます。`Google Driveへの保存を再試行する`ボタンから、文字起こし・翻訳を再実行せず保存を再試行できます。

## 注意事項

- Google Driveのファイルはアプリが管理します。`manifest.json` を消したり、動画IDサブフォルダ名を変えたりすると既存データを見つけられなくなります。
- 保存途中でエラーになった場合、整合性チェックで不完全なキャッシュを検出します。再生成するか、手動でファイルを修復してください。
- `drive.file`権限では、アプリが作成していない既存のDriveファイルを任意に検索することはできません。この実装で作成した`YouTube Translator`フォルダ内を使用してください。
- Railwayのコンテナ内`outputs/`は永続保存ではありません。永続コピーはDrive側です。
- アプリにパスワード認証を残しています。公開URLからAPI料金が勝手に発生しないよう、秘密情報をGitHubに入れないでください。
- YouTube字幕取得・音声ダウンロードは動画の条件やYouTube側の制限で失敗することがあります。
