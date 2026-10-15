#!/bin/bash
set -euo pipefail
mkdir -p Talk/exports
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i testsrc2=size=1280x720:rate=30:duration=20 \
  -f lavfi -i "aevalsrc='0.12*sin(2*PI*190*t)*(0.6+0.4*sin(2*PI*3*t))*lt(mod(t\,4)\,3.2)':s=48000:d=20" \
  -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p -c:a aac -movflags +faststart Talk/exports/talk.mp4
