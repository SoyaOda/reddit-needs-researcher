# AGENTS.md

## Language
- 日本語で応答すること。
- コードの識別子は英語、コメントは必要な場合のみ日本語可。

## Project Scope
- Reddit の公開投稿・コメントを、承認済み Data API/OAuth 経由で低頻度に収集し、ユーザーの悩み・ニーズ仮説を抽出する技術検証プロジェクト。
- ブラウザスクレイピング、未認証 `.json` 取得、制限回避、複数アカウントによるレート制限回避は実装しない。
- `.env` は作成・読取しない。認証情報は環境変数からのみ読む。

## Dependencies
- 初期実装は Python 標準ライブラリのみ。
- 新しい依存関係を追加する前にユーザー確認を取る。

## Commands
- 静的構文確認: `python3 -m compileall src tests scripts`
- テスト: `PYTHONPATH=src python3 -m unittest discover -s tests`
- 設定検証: `PYTHONPATH=src python3 -m reddit_needs_researcher.cli validate-config --config configs/example.topic.json`
- ドライラン: `PYTHONPATH=src python3 -m reddit_needs_researcher.cli collect --config configs/example.topic.json --db data/reddit.sqlite --dry-run`

## Coding Standards
- 型は明示する。安易な `Any` は使わない。
- 本番コードでデバッグ出力を残さない。
- マジックナンバーは定数化する。
- Fallback 実装は避け、必須条件が欠ける場合は明示的にエラーで止める。

