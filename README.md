# 小説の評価 skill（クロスレビュー／編集者評価）

自作の小説を AI に辛口で評価してもらうための、手順書のセットです。
Claude（Anthropic の AI）の「スキル」という仕組みで作っていますが、中身はふつうの文章なので、ほかの AI でも使えます。

| skill | 何をするか | いつ使うか |
|---|---|---|
| **cross-review**（クロスレビュー） | 書いた作品をまとめて採点。編集者の点と講評に、10代〜70代の男女14人の**架空の読者**による点と一言を付け、作品をまたいだ癖や、どの読者に届いていないかまでまとめる | 何作か書きためたとき。自分の通信簿が欲しいとき |
| **editor-review**（編集者評価） | 1話・1章・短編1本を、構成・キャラクター・テンポ・引き・整合性・表記・AI臭さの7項目で読み、優先度つきの修正案と「修正前→修正後」の一覧を残す | 1話書き終えて、投稿する前 |

どちらも「甘くしない」「読んでいないところを想像で評価しない」「著者しか知らないことは推測で書かない」を決めごとにしています。
14人の読者像は AI の見立てで、本当の読者の声ではありません。

---

## 使い方

自分の環境に合うものを一つ選んでください。

### A. Claude のアプリで使う（いちばん手軽）

claude.ai（ブラウザ）や Claude のデスクトップアプリで使う方法です。

1. このページの [`dist/`](dist/) フォルダを開き、使いたいほうの ZIP をダウンロードします
   - `cross-review.zip`：クロスレビュー
   - `editor-review.zip`：編集者評価
2. Claude の**設定**を開き、**スキル**の画面で ZIP をアップロードします
   - 画面の名前や場所は変わることがあります。スキルの画面が見当たらないときは、設定の中の「コード実行」（ファイルの作成など）を有効にすると出てくることがあります。プランによっては使えない場合もあります
3. 新しい会話で、原稿のファイルを添付して頼みます

   > この3作を、クロスレビューで辛口に採点してください。

   > 第3話を、投稿前の編集者評価にかけてください。

### B. Claude Code で使う

[Claude Code](https://docs.claude.com/ja/docs/claude-code/overview)（ターミナルで動く Claude）を使っている人向けです。

```bash
git clone https://github.com/neuvecom/novel-editor-review.git
mkdir -p ~/.claude/skills
cp -r novel-editor-review/skills/cross-review ~/.claude/skills/
cp -r novel-editor-review/skills/editor-review ~/.claude/skills/
```

原稿のあるフォルダで Claude Code を起動し、「`chapters/` の作品をクロスレビューして」のように頼むと使われます。
一つのプロジェクトだけで使うなら、`~/.claude/skills/` の代わりにそのプロジェクトの `.claude/skills/` に置きます。

### C. ほかの AI（ChatGPT・Gemini など）で使う

skill の中身はふつうの文章（Markdown）です。

1. `skills/cross-review/` か `skills/editor-review/` の中の `SKILL.md` と、`references/` の中のファイルを開きます
2. 会話の最初に、それを貼るか添付して「この手順で評価してください」と頼み、原稿を渡します

付けているツール（下の `scripts/`）は Python が動く環境でしか走りません。走らないときは、AI に「ツールは使わずに、手順の見るところに沿って読んで」と頼めば評価はできます。

---

## ツールだけ使う

Python 3.9 以上が入っていれば、AI を使わずに数字や目印だけ出せます。どちらも標準ライブラリだけで動き、原稿は書き換えません。

```bash
# 作品ごとの文の型（一文あたりの読点・「〜た。」で終わる文の割合）
python3 skills/cross-review/scripts/style_stats.py 作品Aの原稿フォルダ/ 作品Bの原稿フォルダ/

# AI臭さの目印（章末のまとめ・「Xではない。Yだ。」・沈黙で閉じる・「〜た。」の連続など）
python3 skills/editor-review/scripts/ai_check.py 原稿フォルダ/
python3 skills/editor-review/scripts/ai_check.py 原稿フォルダ/ep03.md
```

原稿は `.md` か `.txt`（UTF-8）。フォルダを渡すとファイル名の順に読みます。話の順と名前の順が違うとき（`Prologue.md` と `Chapter01.md` など）は、ファイルを順に並べて渡してください。

- 1行目が `---` の YAML フロントマターは読み飛ばします。先頭が見出し・箇条書きだけの塊で、そのあとに `---` が来る形（`# 第一話` `- **想定文字数**: …` `---` 本文）も、その塊をメタ情報として飛ばします。本文の途中の `---` は場面転換として扱い、前後とも数えます
- `README.md`・`Progress.md`・まえがき・あとがきと、評価ファイル（`editor_review_…`・`cross_review_…`）は数えません。`style_stats.py` はフォルダの中を下までたどりますが、`editor_review/`・`process_log/`・`common/`・`publish/` は見ません
- Windows でも出力は UTF-8 にそろえるので、パイプや Claude Code から呼んでも止まりません
数字は合否ではなく、「ここを読み直す」の目安です。癖の一覧と直し方は [`skills/editor-review/references/ai_smell.md`](skills/editor-review/references/ai_smell.md) にあります。

---

## 中身

```
skills/
├── cross-review/                 クロスレビュー
│   ├── SKILL.md                  手順と決めごと
│   ├── references/readers.md     読者像14人と、点の付け方の心得
│   ├── references/template.md    評価ファイルのひな形
│   └── scripts/style_stats.py    文の型を数えるツール
└── editor-review/                編集者評価
    ├── SKILL.md                  手順と決めごと
    ├── references/ai_smell.md    AI臭さの癖の一覧と直し方
    ├── references/review_template.md  評価ファイルのひな形
    └── scripts/ai_check.py       AI臭さの目印を並べるツール
dist/                             Claude のアプリに上げる ZIP
```

`dist/` の ZIP は `skills/` の中身をそのまま固めたものです。`skills/` を直したら `./build.sh` で作り直します。

## もとになったもの

ある書き手が、自作の小説を AI と書きながら続けてきた評価の手順と、自作16作品の点検から作ったルールを、ほかの人も使える形にまとめ直したものです。

## ライセンス

MIT
