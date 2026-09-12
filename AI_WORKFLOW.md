# AI_WORKFLOW

最終更新: 2026-09-12

このRepositoryは店舗Webサイトの公開テンプレート実装を管理する。事業方針・料金・営業・顧客管理は`fromsot/sot-store-web`を確認する。

## 作業開始
`git status` → `git fetch origin` → `git branch --show-current` → `git log -1 --oneline origin/main` → 必要なら`git pull --ff-only origin main` → README確認 → `fromsot/sot-store-web/docs/progress.md` / `backlog.md` / `decisions.md`確認。

## ルール
- Secret、Token、Password、顧客の機微情報をcommitしない。
- 既存テンプレート互換性を壊す大規模変更を避ける。
- 本番公開へ直接変更せず、ローカルbuild/previewを先に確認する。
- mainへ複数AIが同時変更しない。

## 並行開発
`feature/<task>-codex` / `feature/<task>-claude` / `fix/<task>-codex` / `fix/<task>-claude`を使い、同じファイルの同時編集を避ける。

## 作業終了
build/preview → test（存在する場合）→ `git diff` → 関連する`fromsot/sot-store-web`進捗文書更新 → commit → push → branch / commit SHA / 検証結果 / 未完了事項を報告。