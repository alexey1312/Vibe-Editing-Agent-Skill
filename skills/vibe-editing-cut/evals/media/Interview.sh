#!/bin/bash
set -euo pipefail
mkdir -p Interview
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i testsrc2=size=640x360:rate=25:duration=8 \
  -f lavfi -i "sine=frequency=210:sample_rate=48000:duration=8" -c:v libx264 -preset ultrafast -crf 35 \
  -pix_fmt yuv420p -c:a aac Interview/interview.mp4
