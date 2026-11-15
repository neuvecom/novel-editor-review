#!/usr/bin/env python3
"""作品ごとに、地の文の「一文あたりの読点」と「〜た。で終わる文の割合」を数える。

    python3 style_stats.py 作品A/ 作品B/ 作品C.md
    python3 style_stats.py --each 作品A/          # 話ごとにも出す

1つの引数を1作品として数える（フォルダなら中の .md / .txt を全部まとめる）。
標準ライブラリだけで動く（Python 3.9 以上）。数字は荒い目安で、合否ではない。

- 台詞（「」『』の中）・見出し（#）・引用（>）・URL・画像・区切り記号の行は外す
- 最初の `---` だけの行より前はメタ情報として読み飛ばす（無ければ全部が本文）
- README.md・まえがき・あとがき（Foreword / Afterword）は外す
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_LINE = re.compile(r"^\s*(#|!\[|>|https?:|---|\*\*|　*[◇◆＊*]+\s*$)")
SKIP_STEMS = {"readme", "foreword", "afterword", "まえがき", "あとがき"}


def files_of(p: Path) -> list[Path]:
    if p.is_dir():
        return sorted(f for f in p.rglob("*")
                      if f.suffix in (".md", ".txt") and f.stem.lower() not in SKIP_STEMS)
    if p.exists():
        return [p]
    sys.exit(f"見つからない：{p}")


def sentences(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    if "---" in lines:
        lines = lines[lines.index("---") + 1:]
    out = []
    for line in lines:
        if not line.strip() or SKIP_LINE.match(line):
            continue
        nar = re.sub(r"「[^」]*」|『[^』]*』", "", line).strip("　 ")
        out += [s for s in re.split(r"(?<=[。！？])", nar) if len(s) > 1 and s[-1] in "。！？"]
    return out


def stats(paths: list[Path]) -> tuple[int, float, float]:
    sents = [s for p in paths for s in sentences(p)]
    if not sents:
        return 0, 0.0, 0.0
    commas = sum(s.count("、") for s in sents) / len(sents)
    ta = sum(s.endswith("た。") for s in sents) / len(sents)
    return len(sents), commas, ta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="地の文の読点と「〜た。」止めを数える")
    ap.add_argument("works", nargs="+", help="作品のフォルダかファイル（1つ＝1作品）")
    ap.add_argument("--each", action="store_true", help="話ごとの数字も出す")
    args = ap.parse_args(argv)

    print("| 作品 | 地の文の文数 | 一文あたりの読点 | 「〜た。」止め |")
    print("|---|---:|---:|---:|")
    for w in map(Path, args.works):
        fs = files_of(w)
        n, c, t = stats(fs)
        print(f"| {str(w).rstrip('/')} | {n:,} | {c:.2f} | {t:.0%} |")
        if args.each and len(fs) > 1:
            for f in fs:
                n, c, t = stats([f])
                print(f"| 　{f.stem} | {n:,} | {c:.2f} | {t:.0%} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
