#!/bin/bash
# The tone sounds only while a word is spoken in transcripts/take.json.
set -euo pipefail
mkdir -p Retime/originals Retime/exports
gate=$(python3 -I - Retime/transcripts/take.json <<'PY'
import json, sys
words = json.load(open(sys.argv[1], encoding="utf-8"))
print("+".join(f"between(t\\,{w['start']:.3f}\\,{w['end']:.3f})" for w in words))
PY
)
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i testsrc2=size=640x360:rate=30:duration=10 \
  -f lavfi -i "aevalsrc='0.25*sin(2*PI*220*t)*($gate)':s=48000:d=10" -c:v libx264 -preset ultrafast -crf 35 \
  -pix_fmt yuv420p -c:a aac Retime/originals/take.mov
