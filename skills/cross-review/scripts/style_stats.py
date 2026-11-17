#!/usr/bin/env python3
"""作品ごとに、地の文の「一文あたりの読点」と「〜た。で終わる文の割合」を数える。

    python3 style_stats.py 作品A/ 作品B/ 作品C.md
    python3 style_stats.py --each 作品A/          # 話ごとにも出す

1つの引数を1作品として数える（フォルダなら中の .md / .txt を全部まとめる）。
標準ライブラリだけで動く（Python 3.9 以上）。数字は荒い目安で、合否ではない。

- 台詞（「」『』の中）・見出し（#）・引用（>）・URL・画像・区切り記号の行は外す
- 1行目が `---` なら YAML フロントマターとして、閉じの `---` まで読み飛ばす
- 最初の `---` より前が見出し・箇条書き・太字だけなら、メタ情報として読み飛ばす
- それ以外の `---` は場面転換として扱い、前後とも本文に数える
- README.md・Progress.md・まえがき・あとがき（Foreword / Afterword）は外す
- フォルダの中を下までたどるが、editor_review/・process_log/・common/・publish/ と
  隠しフォルダ、名前が editor_review_ / cross_review_ で始まるファイル（評価）は数えない
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_LINE = re.compile(r"^\s*(#|!\[|>|https?:|---|\*\*|　*[◇◆＊*]+\s*$)")
SKIP_STEMS = {"readme", "progress", "foreword", "afterword", "まえがき", "あとがき"}
# 原稿でないものを置くフォルダ（評価・制作記録・設定資料・生成物）
SKIP_DIRS = {"editor_review", "cross_review", "process_log", "common", "publish"}
SKIP_PREFIXES = ("editor_review", "cross_review")


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


def is_manuscript(f: Path, root: Path) -> bool:
    stem = f.stem.lower()
    parts = f.relative_to(root).parts[:-1]
    return (f.is_file() and f.suffix in (".md", ".txt") and stem not in SKIP_STEMS
            and not stem.startswith(SKIP_PREFIXES)
            and not any(d.lower() in SKIP_DIRS or d.startswith(".") for d in parts))


def files_of(p: Path) -> list[Path]:
    if p.is_dir():
        return sorted(f for f in p.rglob("*") if is_manuscript(f, p))
    if p.exists():
        return [p]
    sys.exit(f"見つからない：{p}")


def sentences(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    lines = lines[strip_header(lines):]
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
    utf8_stdout()
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
