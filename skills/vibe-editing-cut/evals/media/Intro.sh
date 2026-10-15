#!/bin/bash
# Synthetic stand-ins for the Intro sources: a variable-frame-rate landscape take,
# a portrait take stored as rotated landscape, and a 60 fps screen recording without sound.
# The tone sounds only while a word is spoken in the transcript, so pauses are real silence.
set -euo pipefail
mkdir -p Intro/originals
ff() { ffmpeg -hide_banner -loglevel error -nostdin -y "$@"; }
speech() {  # transcript JSON → aevalsrc expression: a tone during each word, silence between
  python3 -I - "$1" "$2" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if isinstance(data, dict) and "segments" in data:
    words = [w for s in data["segments"] for w in s["words"]]
else:
    words = [w for w in data["words"] if w.get("type", "word") == "word"]
gate = "+".join(f"between(t\\,{w['start']:.2f}\\,{w['end']:.2f})" for w in words)
print(f"0.25*sin(2*PI*{sys.argv[2]}*t)*({gate})")
PY
}
ff -f lavfi -i testsrc2=size=1280x720:rate=60:duration=12 \
   -f lavfi -i "aevalsrc='$(speech Intro/transcripts/take_01.json 180)':s=48000:d=17" \
   -vf "setpts='if(lt(N,300),N*2/60,10+(N-300)/60)/TB'" -fps_mode vfr -c:v libx264 -preset ultrafast -crf 35 \
   -pix_fmt yuv420p -c:a aac -shortest Intro/originals/take_01.mp4
ff -f lavfi -i testsrc2=size=1280x720:rate=30:duration=15.5 \
   -f lavfi -i "aevalsrc='$(speech Intro/transcripts/take_02.json 200)':s=48000:d=15.5" \
   -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p -c:a aac Intro/originals/take_02_landscape.mov
ff -display_rotation 90 -i Intro/originals/take_02_landscape.mov -c copy Intro/originals/take_02.mov
rm -f Intro/originals/take_02_landscape.mov
ff -f lavfi -i testsrc2=size=1280x800:rate=60:duration=12 -c:v libx264 -preset ultrafast -crf 35 -pix_fmt yuv420p \
   Intro/originals/screen_01.mov
