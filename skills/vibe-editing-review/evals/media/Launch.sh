#!/bin/bash
# Two different drafts, long enough for the defects the notes name (00:18.6, 00:31-00:36).
set -euo pipefail
mkdir -p Launch/renders
ff() { ffmpeg -hide_banner -loglevel error -nostdin -y "$@"; }
ff -f lavfi -i testsrc=size=360x640:rate=30:duration=40 -f lavfi -i "sine=frequency=180:sample_rate=48000:duration=40" \
   -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p -c:a aac Launch/renders/draft_v2.mp4
ff -f lavfi -i testsrc2=size=360x640:rate=30:duration=45 -f lavfi -i "sine=frequency=200:sample_rate=48000:duration=45" \
   -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p -c:a aac Launch/renders/draft_v3.mp4
