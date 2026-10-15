#!/bin/bash
set -euo pipefail
mkdir -p Launch/renders
for name in draft_v2 draft_v3; do
  ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i testsrc2=size=360x640:rate=30:duration=2 \
    -f lavfi -i "sine=frequency=200:sample_rate=48000:duration=2" -c:v libx264 -preset ultrafast -crf 35 \
    -pix_fmt yuv420p -c:a aac "Launch/renders/$name.mp4"
done
