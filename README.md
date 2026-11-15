# editor-review

日本語の小説を、投稿の前に編集者の目で評価するための Claude Code の skill です。

1話・1章・短編1本を書き終えたら、構成・キャラクター・テンポ・引き・整合性・表記・AI臭さの7項目で読み、優先度つきの修正案と「修正前→修正後」の一覧を `editor_review/` に残します。

生成AIと一緒に小説を書いている人向けに、AI の地の文に出やすい癖（章末のまとめ・「Xではない。Yだ。」・沈黙で閉じる・「〜た。」の連続など）を洗い出すツールも付けています。

## 入れ方

```bash
git clone https://github.com/neuvecom/novel-editor-review.git
cp -r novel-editor-review ~/.claude/skills/editor-review        # 全プロジェクトで使う
# または
cp -r novel-editor-review <あなたのプロジェクト>/.claude/skills/editor-review
```

Claude Code に「第3話の編集者評価をして」のように頼むと使われます。

## AI臭さのツールだけ使う

```bash
python3 scripts/ai_check.py 原稿フォルダ/          # .md / .txt を名前順に全部
python3 scripts/ai_check.py 原稿フォルダ/ep03.md   # 1話だけ
```

フォルダを渡すとファイル名の順に読みます。話の順と名前の順が違うとき（`Prologue.md` と `Chapter01.md` など）は、ファイルを順に並べて渡してください。

Python 3.9 以上、標準ライブラリだけで動きます。目印を並べるだけで、原稿は書き換えません。数字は合否ではなく「ここを読み直す」の目安です。

## 中身

| ファイル | 内容 |
|---|---|
| `SKILL.md` | 評価の手順と守ること |
| `references/ai_smell.md` | AI臭さの癖の一覧・直し方・ツールの読み方 |
| `references/review_template.md` | 評価ファイルのひな形 |
| `scripts/ai_check.py` | AI臭さの目印を並べるツール |

## もとになったもの

ある書き手が、自作の小説（短編・連載・長編）を AI と書きながら続けてきた編集者評価の手順と、自作16作品の点検から作ったルールを、ほかの人も使える形にまとめ直したものです。

## ライセンス

MIT
