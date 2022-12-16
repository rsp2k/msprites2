Refactored from: https://github.com/baloda/msprites. THANK YOU baloda

# msprites, media thumbnail sprites, multipule thumbnail sprites

# Requirements:

    1. FFmpeg
```text
sudo apt get install ffmpeg
```
    2. ImageMagick Montage (replaced by magick command in ImageMagick 7.0+)
```text
sudo apt get install imagemagick
```

# Steps:
    1. Extract images using ffmpeg. You can configure size of image and image rate per second(ips)
    2. Convert Image in spirtesheet of grid ROWSxCOLS
    3. Create a webvtt file of spritesheet images

The WebVTT file consists of time-aligned metadata:
https://www.w3.org/TR/webvtt1/#introduction-metadata

and spatial dimension of media fragments (media fragments being jpeg/png thumbnail files or sprites)

https://www.w3.org/TR/media-frags/#naming-space

More info:
https://css-tricks.com/improving-video-accessibility-with-webvtt/

```text
00:00:00.000 --> 00:00:05.000
f08e80da-bf1d-4e3d-8899-f0f6155f6efa.jpg#xywh=0,0,120,67

00:00:05.000 --> 00:00:10.000
f08e80da-bf1d-4e3d-8899-f0f6155f6efa.jpg#xywh=120,0,120,67

00:00:10.000 --> 00:00:15.000
f08e80da-bf1d-4e3d-8899-f0f6155f6efa.jpg#xywh=240,0,120,67

00:00:15.000 --> 00:00:20.000
f08e80da-bf1d-4e3d-8899-f0f6155f6efa.jpg#xywh=360,0,120,67
```

Note that you cannot provide blank lines inside a metadata block, because the blank line signifies the end of the WebVTT cue.

Installation
```pip install msprites2```

# How to use:
```
import os
from sprites2 import MontageSprites

sprite = MontageSprites.from_media(
    video_path="/tmp/SampleVideo_360x240_20mb.mp4",
    thumbnail_dir="/tmp/samplevideo-thumbs" # Must be unique, or pass delete_existing_thumbnail_dir=True
    sprite_file"framge-sprite.jpg",
    webvtt_file="frame-sprite.webvtt",
    delete_existing_thumbnail_dir=False,
)

print(sprite.dir.name)
for filename in os.listdir(sprite.thumbnail_dir):
    print(filename)
```
