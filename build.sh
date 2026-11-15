#!/bin/sh
# skills/ の各フォルダを、Claude のアプリに上げられる ZIP にする（dist/<名前>.zip）
set -e
cd "$(dirname "$0")"
mkdir -p dist
for d in skills/*/; do
  name=$(basename "$d")
  rm -f "dist/$name.zip"
  (cd skills && zip -qr "../dist/$name.zip" "$name" -x '*/__pycache__/*' '*.pyc')
  echo "dist/$name.zip"
done
