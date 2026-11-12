#!/bin/sh
# Installs everything the project needs, inside this folder. Safe to run again.
# Assumes on the machine: uv, curl and tar.
set -eu
cd "$(dirname "$0")"
ROOT=$(pwd)

ARXIV_ID=2506.01523v2

echo "== scripts' environment"
# If uv has to download a Python, it goes inside the folder too.
export UV_PYTHON_INSTALL_DIR="$ROOT/local/python"
uv sync

echo "== test paper, arXiv $ARXIV_ID, in local/papers/yun2025"
PAPER="$ROOT/local/papers/yun2025"
mkdir -p "$PAPER/latex"
if [ -z "$(ls -A "$PAPER/latex")" ]; then
  curl -fsSL "https://arxiv.org/e-print/$ARXIV_ID" -o "$PAPER/source.tar.gz"
  tar -xzf "$PAPER/source.tar.gz" -C "$PAPER/latex"
  rm "$PAPER/source.tar.gz"
else
  echo "source already present"
fi
if [ -f "$PAPER/paper.pdf" ]; then
  echo "PDF already present"
else
  curl -fsSL "https://arxiv.org/pdf/$ARXIV_ID" -o "$PAPER/paper.pdf"
fi

echo "== done"
