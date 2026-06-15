#!/usr/bin/env bash
# Build a LaTeX deliverable into a PDF, staging in an ASCII temp directory to
# avoid the OneDrive/accented-path problems that break MiKTeX on the synced
# project folder (same trick used for Dynare). Usage: ./build.sh Comprehend
set -u
NAME="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
FIGS="$HERE/../outputs/figures"
WORK="/c/Temp/nktex_${NAME}"
ENGINE="${2:-pdflatex}"
PDFLATEX="/c/Users/joaoz/AppData/Local/Programs/MiKTeX/miktex/bin/x64/${ENGINE}.exe"

rm -rf "$WORK"; mkdir -p "$WORK/figures"
cp "$FIGS"/*.png "$WORK/figures/" 2>/dev/null
cp "$HERE/${NAME}.tex" "$WORK/"

cd "$WORK" || exit 2
for pass in 1 2; do
  "$PDFLATEX" -interaction=nonstopmode -halt-on-error=0 "${NAME}.tex" >"pass${pass}.log" 2>&1
done

if [ -f "$WORK/${NAME}.pdf" ]; then
  cp "$WORK/${NAME}.pdf" "$HERE/${NAME}.pdf"
  echo "OK: built $HERE/${NAME}.pdf ($(wc -c < "$HERE/${NAME}.pdf") bytes)"
else
  echo "FAIL: ${NAME}.pdf not produced. Last errors:"
  grep -iE "^!|fatal|error|undefined|not found" "$WORK/pass2.log" | head -25
  exit 1
fi
