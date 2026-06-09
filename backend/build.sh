#!/usr/bin/env bash
set -e

# Install FFmpeg system dependency for faster-whisper/av
apt-get update && apt-get install -y ffmpeg

# Install Python dependencies
pip install -r requirements.txt