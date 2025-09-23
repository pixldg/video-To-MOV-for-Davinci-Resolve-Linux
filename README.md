# video-To-MOV-for-Davinci-Resolve-Linux

A simple Linux AppImage tool to convert videos to MOV format using DNxHD codec, built with Python3, GTK3, and FFmpeg.


## Features

- Single-window GUI
- Select input video (mp4, mkv, m4v, mov, avi, wmv, hevc, 3gp)
- Choose FPS and Resolution (or keep original if detected)
- Warning if input video lacks FPS or resolution
- Progress bar with ETA
- Conversion complete dialog
- Portable AppImage included

## Requirements

- **FFmpeg** (`ffmpeg` and `ffprobe`) **must be installed separately**. The AppImage **does not bundle FFmpeg**.  
- Python 3 and GTK3 are required **only if running from source**.

## Installation

### Installing FFmpeg

#### Debian / Ubuntu
```bash
sudo apt update
sudo apt install ffmpeg

