#!/bin/bash
# The delivered promo with planted defects; the review case must find them without this script.
set -euo pipefail
mkdir -p Promo/exports
ffmpeg -hide_banner -loglevel error -nostdin -y \
  -f lavfi -i "color=black:size=1080x1080:rate=30:duration=0.5" \
  -f lavfi -i "testsrc2=size=1080x1080:rate=30:duration=3" \
  -f lavfi -i "testsrc2=size=1080x1080:rate=30:duration=0.04,loop=loop=89:size=1:start=0,setpts=N/30/TB" \
  -f lavfi -i "testsrc2=size=1080x1080:rate=30:duration=2" \
  -f lavfi -i "aevalsrc='0.3*sin(2*PI*220*t)*(1-between(t\,2.5\,4.6))':s=48000:d=8.5" \
  -filter_complex "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0,format=yuv420p[v]" -map "[v]" -map 4:a \
  -c:v libx264 -preset ultrafast -crf 35 -c:a aac -shortest -movflags +faststart Promo/exports/final.mp4
