# reddit-needs-researcher

Reddit の投稿・コメントから「ユーザーの悩み」「未充足ニーズ」「次に掘るべき探索クエリ」を抽出するための技術検証プロジェクトです。

この初期版は依存関係を追加せず、Python 標準ライブラリだけで動くようにしています。Reddit 取得は OAuth/Data API 前提、分析はローカルのヒューリスティックと Codex/Claude CLI のどちらでも回せる構成です。

## 現時点の技術判断

- Reddit 側は 2026年時点で OAuth と承認済み Data API アクセスが前提です。公式 Help は 100 QPM/OAuth client id、`X-Ratelimit-*` ヘッダー監視、未認証トラフィックのブロックを明記しています。
- agent に Reddit を直接探索させるのではなく、収集器が API/rate limit/保存形式を制御し、agent は JSONL snapshot を読むだけにします。
- Codex は `codex exec --output-schema`、Claude Code は `claude -p --json-schema` で構造化出力に寄せます。
- PRAW/Async PRAW は有力ですが、初期版では依存追加確認を避けるため直接 HTTP 実装にしています。必要なら後で差し替え可能です。

詳細な最新調査は [docs/technical-feasibility-2026-06.md](/Users/odasoya/reddit-needs-researcher/docs/technical-feasibility-2026-06.md) を参照してください。

## セットアップ

このプロジェクトは `.env` を読みません。Reddit 側で承認済み OAuth app を用意した上で、実行シェルに環境変数を設定します。

```bash
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export REDDIT_USER_AGENT="macos:reddit-needs-researcher:v0.1.0 (by /u/YOUR_USERNAME)"
```

`REDDIT_USER_AGENT` は Reddit 公式が推奨する一意で説明的な形式にしてください。

## 基本コマンド

設定ファイルを検証します。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli validate-config \
  --config configs/example.topic.json
```

ネットワークなしで収集計画だけ確認します。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli collect \
  --config configs/example.topic.json \
  --db data/reddit.sqlite \
  --dry-run
```

実際に収集します。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli collect \
  --config configs/example.topic.json \
  --db data/reddit.sqlite
```

ローカルで悩みシグナルを抽出します。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli analyze-local \
  --db data/reddit.sqlite \
  --topic "habit and nutrition coaching" \
  --output reports/local-report.md \
  --json-output reports/local-report.json
```

agent に渡す JSONL を作ります。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli export-jsonl \
  --db data/reddit.sqlite \
  --topic "habit and nutrition coaching" \
  --output data/evidence.jsonl
```

Codex で構造化レポートを作ります。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli agent \
  --provider codex \
  --input data/evidence.jsonl \
  --prompt prompts/needs_analysis.md \
  --schema schemas/needs_report.schema.json \
  --output reports/codex-report.json
```

Claude Code で構造化レポートを作ります。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli agent \
  --provider claude \
  --input data/evidence.jsonl \
  --prompt prompts/needs_analysis.md \
  --schema schemas/needs_report.schema.json \
  --output reports/claude-report.json
```

Claude で `--bare` を使う場合は `ANTHROPIC_API_KEY` など明示的な認証が必要です。

agent コマンドの形だけ確認する場合は、合成データの `examples/sample_evidence.jsonl` を使って `--dry-run` できます。

```bash
PYTHONPATH=src python3 -m reddit_needs_researcher.cli agent \
  --provider codex \
  --input examples/sample_evidence.jsonl \
  --prompt prompts/needs_analysis.md \
  --schema schemas/needs_report.schema.json \
  --output reports/sample-codex-report.json \
  --dry-run
```

## 検証

```bash
python3 -m compileall src tests scripts
PYTHONPATH=src python3 -m unittest discover -s tests
```

## ディレクトリ

- `src/reddit_needs_researcher/`: collector, store, analysis, agent runner
- `configs/`: 調査 topic 設定
- `prompts/`: agent に渡す分析プロンプト
- `schemas/`: 構造化出力 JSON Schema
- `docs/`: 技術調査・設計メモ
- `site/`: Reddit Data API access review 用の静的公開ページ
- `tests/`: 標準ライブラリ unittest

## 審査用サイト

`site/` は Reddit Data API access request の `source code or platform URL` に使うための公開説明ページです。個人情報は公開せず、フォーム側に入力する前提にしています。

公開URL: https://soyaoda.github.io/reddit-needs-researcher/
公開リポジトリ: https://github.com/SoyaOda/reddit-needs-researcher

```bash
cd site
npm run build
python3 -m http.server 9876 --bind 127.0.0.1 --directory public
```

公開する場合は、Codex Sites か GitHub Pages などで `site/public` を静的ホストできます。Codex Sites に渡す場合のために、`npm run build` は Cloudflare Worker 互換の `site/dist/worker.mjs` も生成します。
