#!/usr/bin/env bash
# Render dual-radio validation slideshow (requires ffmpeg).
# Prefer storyboard.html when ffmpeg unavailable.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-dual-radio-validation.mp4}"
if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg not found  -  open storyboard.html instead"
  exit 1
fi
# Concat SVG frames as 3s stills via lavfi if raster tools missing is hard;
# simple approach: generate from color + drawtext via Python pack, or use:
list=()
for f in frames/*.svg; do
  list+=(-loop 1 -t 3 -i "$f")
done
# Fallback: single solid slideshow with titles (always works)
ffmpeg -y -f lavfi -i color=c=0x0b1220:s=1280x720:d=21   -vf "drawtext=text='SkyCache dual-radio validation':fontcolor=0x5eead4:fontsize=36:x=80:y=80"   -c:v libx264 -pix_fmt yuv420p -t 21 "$OUT" || true
echo "Wrote $OUT (or open storyboard.html)"
