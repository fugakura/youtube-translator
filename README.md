# YouTube Translator for Railway

YouTube字幕、またはyt-dlpとOpenAI音声認識で文字起こしし、日本語に翻訳します。
TXTダウンロードおよびCosense（旧Scrapbox）への新規ページ投稿が可能です。

## GitHub → Railway

1. このフォルダ内のファイルをGitHubのリポジトリ直下へアップロードします（`.env`はアップロードしません）。
2. Railwayで **New Project → Deploy from GitHub Repo** を選びます。
3. Railwayのサービスの **Variables** に次を設定します。
   - `OPENAI_API_KEY`: OpenAI APIキー
   - `APP_PASSWORD`: 自分だけが知っている長いパスワード（必須）
   - `COSENSE_PAT`: Cosense Personal Access Token（投稿機能に必須）
   - `COSENSE_PROJECT`: `youtube-translator`
4. Railwayで **Settings → Networking → Generate Domain** を実行します。
5. **Settings → Deploy → Serverless** はオフにします（常時起動する場合）。

`railpack.json`に、Python、Deno、FFmpeg、Streamlitの起動コマンドを設定してあります。
追加の`Dockerfile`や旧式の`railway.json`は不要です。

### ローカル実行

`.env.example`を参考にして `.env` を作成します。

```bash
pip install -r requirements.txt
streamlit run app.py
```

音声認識を使う場合はローカルにもFFmpegとDenoをインストールしてください。

### 注意

- YouTube側の制限で字幕・音声取得が失敗する場合があります。
- Cosenseの投稿は編集APIのプレビューと確定を使用します。ページタイトルが既存と重複した場合は中断します。
- Railwayのローカルファイルは永続保存ではありません。TXTは生成直後にブラウザから保存するか、Cosenseへ投稿してください。
- 文字起こし・翻訳の公開には権利関係を確認してください。
- 実際のCosense書き込みにはPATが必要です。API疎通テストは各自の環境で行ってください。
