#!/bin/bash
set -euo pipefail
mkdir -p Drift/exports
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i testsrc2=size=640x360:rate=30:duration=5.2 \
  -f lavfi -i "sine=frequency=220:sample_rate=48000:duration=5.2" -c:v libx264 -preset ultrafast -crf 35 \
  -pix_fmt yuv420p -c:a aac Drift/exports/final.mp4
