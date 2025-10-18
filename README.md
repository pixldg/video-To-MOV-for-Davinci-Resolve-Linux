# video-To-MOV-for-Davinci-Resolve-Linux

A simple Linux AppImage tool to convert videos to MOV format using ProRes, DNxHD and Cineform codec, built with Python3, GTK3, and FFmpeg.


## Features
- Supports vertical, horizontal and square videos
- Single-window GUI
- Select input video (mp4, mkv, m4v, mov, avi, wmv, hevc, 3gp)
- Choose codec (DNxHD, ProRes or Cineform)
- Portable AppImage included

## Requirements

- **FFmpeg** (`ffmpeg` and `ffprobe`) **must be installed separately**. The AppImage **does not bundle FFmpeg**.  
- Python 3 and GTK3 are required **only if running from source**.
- Install libfuse2 to run Appimages.

## Installation

#### Debian / Ubuntu
```bash
sudo apt update
sudo apt install libfuse2
```    

### Installing FFmpeg

```bash
sudo apt update
sudo apt install ffmpeg

