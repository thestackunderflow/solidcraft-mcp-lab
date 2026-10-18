#!/bin/bash
# Spike 1: does the SolidCraft 0.15.0 desktop app open and draw under Xvfb (software Vulkan)?
set -u
OUT=/work/spike/out
Xvfb :99 -screen 0 1920x1080x24 >/dev/null 2>&1 &
export DISPLAY=:99
sleep 2
solidcraft --version > $OUT/version.txt 2>&1
solidcraft --control 7878 > $OUT/app.log 2>&1 &
APP=$!
sleep 25
ffmpeg -loglevel error -y -f x11grab -video_size 1920x1080 -i :99 -frames:v 1 $OUT/window.png
xwininfo -root -tree | grep -i -E "solid|craft" | head -5 > $OUT/windows.txt
ls -la ~/.local/share/solidcraft/control/ > $OUT/control-dir.txt 2>&1
kill -0 $APP && echo "app alive" || echo "app exited"
tail -20 $OUT/app.log
