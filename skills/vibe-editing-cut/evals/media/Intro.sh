#!/bin/bash
# Synthetic stand-ins for the Intro sources: a variable-frame-rate landscape take,
# a portrait take stored as rotated landscape, and a 60 fps screen recording without sound.
set -euo pipefail
mkdir -p Intro/originals
ff() { ffmpeg -hide_banner -loglevel error -nostdin -y "$@"; }
ff -f lavfi -i testsrc2=size=1280x720:rate=60:duration=12 -f lavfi -i "sine=frequency=180:sample_rate=48000:duration=17" \
   -vf "setpts='if(lt(N,300),N*2/60,10+(N-300)/60)/TB'" -fps_mode vfr -c:v libx264 -preset ultrafast -crf 35 \
   -pix_fmt yuv420p -c:a aac -shortest Intro/originals/take_01.mp4
ff -f lavfi -i testsrc2=size=1280x720:rate=30:duration=15.5 -f lavfi -i "sine=frequency=200:sample_rate=48000:duration=15.5" \
   -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p -c:a aac Intro/originals/take_02_landscape.mov
ff -display_rotation 90 -i Intro/originals/take_02_landscape.mov -c copy Intro/originals/take_02.mov
rm -f Intro/originals/take_02_landscape.mov
ff -f lavfi -i testsrc2=size=1280x800:rate=60:duration=12 -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p \
   Intro/originals/screen_01.mov
