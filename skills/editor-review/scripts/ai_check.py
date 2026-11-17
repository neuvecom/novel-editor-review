#!/usr/bin/env python3
"""日本語の小説原稿から、AI の文章に出やすい癖（いわゆる「AI臭さ」）を洗い出す。

    python3 ai_check.py chapters/                 # フォルダ内の .md / .txt を名前順に全部
    python3 ai_check.py chapters/ep03.md          # 1話だけ
    python3 ai_check.py ep01.md ep02.md ep03.md   # 指定した順に

標準ライブラリだけで動く（Python 3.9 以上）。

## 直さずに並べるだけ

**癖かどうかは文脈で決まる。** 「何も言わなかった」も、沈黙そのものが主題の作品では
正しい使い方になる。猫の語り（読点が多い）や落語（――が多い）も、語りの型として
使っているなら癖ではない。だから置換はせず、候補を出すだけにする。
数字は「ここを読み直せ」という目印で、合格ラインではない。

## 見るもの

1. 文のリズム：地の文で「〜た。」が3文続く割合
2. 表現：1行ごとに引っかける型（決め台詞・二段ぼかし・説明的な感情など）
3. 章末：最後の数行が、まとめ・教訓・予告・沈黙で閉じていないか
4. 話をまたいで：同じ小道具・同じ型で章を閉じていないか
   （1話ずつ見ていると気づけない。同じ「ポケットの中のバッジ」が3話の締めに
   出ていた、というのが実例）

## ファイルの扱い

- 1行目が `---` なら YAML フロントマターとして、閉じの `---` まで読み飛ばす
- 最初の `---` より前が見出し・箇条書き・太字だけなら、メタ情報として読み飛ばす
- それ以外の `---` は場面転換として扱い、前後とも本文に数える
- 見出し（#）・引用（>）・画像・URL・区切り記号だけの行は本文から外す
- ファイル名が Foreword / Afterword / まえがき / あとがき のものは語りが違うので外す
- README.md・Progress.md と、名前が editor_review_ / cross_review_ で始まるもの（評価ファイル）も外す
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── 1行ごとに引っかける型 ─────────────────────────────────
# (名前, 正規表現, 一言)。一言は「なぜ癖なのか」。直し方は references/ai_smell.md。
LINE_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("XではなくY", re.compile(r"(ではない。[^。」]{1,25}だ。|わけじゃない」.{0,30}「[^」]{1,15}んだ」)"),
     "「Xではない。Yだ。」の言い切り。1作に1回なら効くが、章末に来ると型が見える"
     "（「AではなくBだった」のような事実の言い分けは普通の日本語なので拾わない）"),
    ("二段ぼかし", re.compile(r"(かもしれない。あるいは|かもしれなかった。あるいは|かもしれないし、[^。]{0,30}かもしれない)"),
     "「〜かもしれない。あるいは〜」。どちらとも言わずに逃げる"),
    ("気持ちの説明", re.compile(r"(気持ちが[^。]{0,8}(交換|伝わ|通じ)|胸が(熱く|いっぱい|締め付け)|心が(温か|満た|震え)|何かが[^。]{0,6}(変わった|ほどけた|溶けた))"),
     "会話や動作で伝わっていることを地の文で言い直している"),
    ("まとめの一文", re.compile(r"(それが[^。」]{2,30}(生き方|答え|意味|値打ち|すべて)(だった|なのだ|である|でございます)|大切なのは|本当の[^。」]{1,4}とは)"),
     "読者が受け取るはずのものを先に言ってしまう"),
    ("沈黙で閉じる", re.compile(r"(何も言わなかった|何も答えなかった|とだけ言った)"),
     "沈黙で余韻を出す定番。続くと効かなくなる"),
    ("数え上げの台詞", re.compile(r"「(一つ|ひとつ)。"),
     "「一つ。二つ。三つ。」と整理して話す人物は、AI の説明口調に寄りやすい"),
    ("決まり文句の反応", re.compile(r"(空気が[^。]{0,4}凍(った|りつ)|息を呑(む|んだ)|目を見開(く|いた)|唇を噛(む|んだ))"),
     "驚き・緊張の反応の型。何度も出るなら別の具体に"),
]

# ── 数を数えるだけのもの（1万字あたりの回数で出す） ────────────
# (名前, 正規表現, 目安)。目安を超えたら印を付ける。16作品を点検したとき、
# 癖が少なかった作品（文語調・落語・ナンセンスなど語りの型がはっきりしたもの）の値を参考に決めた。
COUNT_PATTERNS: list[tuple[str, re.Pattern, float]] = [
    ("――", re.compile(r"――"), 10.0),
    ("少しだけ／ほんの少し", re.compile(r"(少しだけ|ほんの少し)"), 4.0),
    ("まるで", re.compile(r"まるで"), 2.0),
    ("静かに／そっと", re.compile(r"(静かに|そっと)"), 3.0),
    ("黙った／黙って", re.compile(r"黙[っら]"), 4.0),
]

# 「〜た。」が3文続く割合（地の文）の目安。癖の強い長編では54%という例があった
TA_RUN_LIMIT = 0.30

# ── 章末で見る型 ─────────────────────────────────────
ENDING_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("教訓・まとめ", re.compile(r"(それが[^。]{2,40}(だった|のだ|である|でございます)。|生き方|大切|明日も|これからも|信じていた|噛みしめ)")),
    ("XではなくY", re.compile(r"(ではない。|ではなく)")),
    ("先の予告", re.compile(r"(それから[^。]{0,10}(年|か月|日)(後|あと)|二度と[^。]{0,10}なかった|のは、[^。]{0,20}(後|あと)のこと)")),
    ("沈黙", re.compile(r"(何も言わなかった|黙っていた|答えなかった)")),
]

# 本文から外す行（メタ・挿絵・記事の飾り・終わりの印）
SKIP_LINE = re.compile(
    r"^\s*(#|〈挿絵|!\[|\*\*|---|>|https?:|ご支援|このマガジン|　*[◇◆＊*]+\s*$|（了）|―\s*おわり|お後がよろしい)"
)
# 章末の小道具の候補（2字以上のカタカナ・漢字の語）
WORD = re.compile(r"[ァ-ヶー]{2,}|[一-龥]{2,}")
# 章末の語の重なりで無視するもの（どの話にも出て当然の語）
COMMON_WORDS = {"自分", "言っ", "思っ", "時間", "今日", "明日", "最後", "一人", "二人"}


# 先頭のメタ情報とみなす行（見出し・箇条書き・太字・引用・空行）
META_LINE = re.compile(r"^\s*($|#|[-*+] |\*\*|>)")


def strip_header(lines: list[str]) -> int:
    """本文の始まる行の位置（0始まり）を返す。

    - 1行目が `---` なら YAML フロントマター。次の `---` までを飛ばす
    - 最初の `---` より前が見出し・箇条書き・太字だけなら、メタ情報として飛ばす
      （「# 第一話」「- **想定文字数**: …」のような見出しの塊）
    - それ以外の `---` は場面転換。どこも飛ばさない
    """
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                return i + 1
        return 0  # 閉じていなければフロントマターではない
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if i > 0 and all(META_LINE.match(l) for l in lines[:i]):
                return i + 1
            return 0
    return 0


def utf8_stdout() -> None:
    """Windows（cp932）でパイプに書くと絵文字・日本語で止まるので、出力を UTF-8 にする。"""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure") and (s.encoding or "").lower().replace("-", "") != "utf8":
            s.reconfigure(encoding="utf-8")


def body_lines(path: Path) -> list[tuple[int, str]]:
    """（行番号, 行）の本文だけを返す。先頭のメタ情報は捨てる（strip_header）。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    start = strip_header(lines)
    out = []
    for i, line in enumerate(lines[start:], start=start + 1):
        if line.strip() and not SKIP_LINE.match(line):
            out.append((i, line))
    return out


def narrative(line: str) -> str:
    """セリフ（「」の中）を外した地の文。"""
    return re.sub(r"「[^」]*」", "", line)


def ta_run_rate(lines: list[tuple[int, str]]) -> float:
    sents = []
    for _, line in lines:
        sents += [s for s in re.split(r"(?<=[。！？])", narrative(line).strip("　 ")) if len(s) > 1]
    if len(sents) < 3:
        return 0.0
    ends = [s.endswith("た。") for s in sents]
    runs = sum(1 for i in range(len(ends) - 2) if ends[i] and ends[i + 1] and ends[i + 2])
    return runs / (len(sents) - 2)


def last_lines(lines: list[tuple[int, str]], n: int = 3) -> list[tuple[int, str]]:
    return lines[-n:]


def scan(path: Path) -> dict:
    lines = body_lines(path)
    text = "".join(re.sub(r"\s", "", l) for _, l in lines)
    size = max(len(text), 1)
    hits = []
    for ln, line in lines:
        for name, pat, _ in LINE_PATTERNS:
            for m in pat.finditer(line):
                ctx = line.strip("　 ")[max(0, m.start() - 12):m.end() + 8]
                hits.append((ln, name, ctx))
    counts = []
    for name, pat, limit in COUNT_PATTERNS:
        n = len(pat.findall(text))
        counts.append((name, n, n / size * 10000, limit))
    endings = []
    tail = last_lines(lines)
    for ln, line in tail:
        for name, pat in ENDING_PATTERNS:
            if pat.search(line):
                endings.append((ln, name, line.strip("　 ")[:60]))
    return {"lines": lines, "size": size, "hits": hits, "counts": counts,
            "ta": ta_run_rate(lines), "endings": endings, "tail": tail}


def cross_episode(scanned: list[tuple[Path, dict]]) -> tuple[list, list]:
    """話をまたいで、章末に同じ語・同じ型が出ていないか。"""
    # 主人公の名前のように、どこにでも出る語は小道具ではないので外す
    all_text = "".join(narrative(l) for _, r in scanned for _, l in r["lines"])
    size = max(len(all_text), 1)
    frequent = {w for w in set(WORD.findall(all_text)) if all_text.count(w) / size * 10000 > 15}
    word_eps = defaultdict(set)
    for path, r in scanned:
        words = set()
        for _, line in r["tail"]:
            words |= {w for w in WORD.findall(narrative(line)) if w not in COMMON_WORDS and w not in frequent}
        for w in words:
            word_eps[w].add(path.stem)
    min_eps = 3 if len(scanned) >= 5 else 2
    words = sorted(((w, sorted(eps)) for w, eps in word_eps.items() if len(eps) >= min_eps),
                   key=lambda x: -len(x[1]))
    type_eps = defaultdict(set)
    for path, r in scanned:
        for _, name, _ in r["endings"]:
            type_eps[name].add(path.stem)
    types = sorted(((t, sorted(eps)) for t, eps in type_eps.items() if len(eps) >= 2),
                   key=lambda x: -len(x[1]))
    return words, types


def report(path: Path, r: dict) -> int:
    print(f"\n{'=' * 70}\n{path.name}（{r['size']:,}字）\n{'=' * 70}")
    flags = 0

    mark = "⚠️ " if r["ta"] > TA_RUN_LIMIT else "✅"
    flags += r["ta"] > TA_RUN_LIMIT
    print(f"\n{mark} 地の文で「〜た。」が3文続く割合: {r['ta']:.0%}（目安 {TA_RUN_LIMIT:.0%} 以下）")

    # 短い話では1〜2回でも率が跳ねるので、3回以上のときだけ印を付ける
    over = [c for c in r["counts"] if c[2] > c[3] and c[1] >= 3]
    flags += len(over)
    print("\n📊 回数（1万字あたり）")
    for name, n, per, limit in r["counts"]:
        m = "⚠️ " if per > limit and n >= 3 else "  "
        print(f"   {m}{name:<12} {n:>3}回  {per:>5.1f}/万字（目安 {limit:g}）")

    if r["hits"]:
        flags += len(r["hits"])
        print(f"\n🔍 型にはまった表現（{len(r['hits'])}件）― 読み直す")
        for ln, name, ctx in r["hits"]:
            print(f"   L{ln:<4} [{name}] …{ctx}…")
    else:
        print("\n✅ 型にはまった表現：なし")

    print("\n🔚 章末の3行")
    for ln, line in r["tail"]:
        print(f"   L{ln:<4} {line.strip('　 ')[:70]}")
    if r["endings"]:
        flags += len(r["endings"])
        for ln, name, _ in r["endings"]:
            print(f"   ⚠️  L{ln} が「{name}」の型で閉じている")
    return flags


SKIP_STEMS = {"readme", "progress", "foreword", "afterword", "まえがき", "あとがき"}
# 評価ファイル（editor_review_2026-11-01.md など）は原稿ではない
SKIP_PREFIXES = ("editor_review", "cross_review")


def is_manuscript(f: Path) -> bool:
    stem = f.stem.lower()
    return (f.suffix in (".md", ".txt") and stem not in SKIP_STEMS
            and not stem.startswith(SKIP_PREFIXES))


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.is_file() and is_manuscript(f))
        elif p.exists():
            files.append(p)
        else:
            sys.exit(f"見つからない：{p}")
    if not files:
        sys.exit("対象の原稿が無い")
    return files


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description="AI臭さの目印を並べる（直さない）")
    ap.add_argument("paths", nargs="+", help="原稿ファイルか、原稿の入ったフォルダ")
    args = ap.parse_args(argv)

    scanned = [(p, scan(p)) for p in collect(args.paths)]
    total = sum(report(p, r) for p, r in scanned)

    if len(scanned) >= 2:
        words, types = cross_episode(scanned)
        print(f"\n{'=' * 70}\n話をまたいだ章末の重なり\n{'=' * 70}")
        if words:
            total += len(words)
            print("\n⚠️  同じ語が複数の話の締めに出ている（小道具の締めの繰り返し）")
            for w, eps in words[:10]:
                print(f"   「{w}」 {len(eps)}話: {', '.join(eps)}")
        if types:
            total += len(types)
            print("\n⚠️  同じ型で閉じている話")
            for t, eps in types:
                print(f"   [{t}] {len(eps)}話: {', '.join(eps)}")
        if not words and not types:
            print("\n✅ 重なりなし")

    print(f"\n{'=' * 70}")
    print(f"目印 {total}件。直すかどうかは人が決める（references/ai_smell.md）。")
    return 0  # 目印を並べるだけ。終了コードは常に 0


if __name__ == "__main__":
    sys.exit(main())
