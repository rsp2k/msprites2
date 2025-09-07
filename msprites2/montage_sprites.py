import logging
import os
import shlex
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)


FFMPEG_THUMBNAIL_COMMAND = """
    ffmpeg -loglevel error -i {input} -r 1/{ips} -vf scale={width}:{height} {output}
"""

MONTAGE_COMMAND = """montage -background '#336699' -tile {rows}x{cols} -geometry {width}x{height}+0+0 {input}/* {output}"""
# Check for imagemagick6
if shutil.which("magick"):
    MONTAGE_COMMAND = "magick " + MONTAGE_COMMAND


class MontageSprites:
    IPS = 1  #  will be used as 1 in every 5 sec
    WIDTH = 512
    HEIGHT = 288
    ROWS = 30
    COLS = 30
    FILENAME_FORMAT = "%04d.jpg"

    WEBVTT_HEADER = "WEBVTT\n"
    WEBVTT_TIME_FORMAT = "%H:%M:%S"
    WEBVTT_TIMELINE_FORMAT = "{start} --> {end}\n"
    WEBVTT_IMAGE_TITLE_FORMAT = "{filename}#xywh={x},{y},{w},{h}\n\n"

    video_path = None
    thumbnail_dir = None
    sprite_file = None

    def __init__(self, video_path, thumbnail_dir):
        self.video_path = video_path
        self.thumbnail_dir = thumbnail_dir
        if not os.path.isdir(self.thumbnail_dir):
            os.mkdir(self.thumbnail_dir, mode=0o777)

    def frame_filename(self, number):
        return self.sprite_file

    def count_files(self):
        count = 0
        for path in os.scandir(self.thumbnail_dir):
            if path.is_file():
                count += 1
        return count

    def generate_thumbs(self):
        output = os.path.join(self.thumbnail_dir, self.FILENAME_FORMAT)
        cmd = FFMPEG_THUMBNAIL_COMMAND.format(
            input=self.video_path,
            ips=self.IPS,
            width=self.WIDTH,
            height=self.HEIGHT,
            output=output,
        )

        logger.debug(f"ffmpeg generate thumbnails [{cmd}]")
        result = subprocess.run(shlex.split(cmd))
        logger.debug(f"ffmpeg generate thumbnails [{cmd}]\n{result}")

    def generate_sprite(self, sprite_file):
        self.sprite_file = sprite_file
        cmd = MONTAGE_COMMAND.format(
            rows=self.ROWS,
            cols=self.COLS,
            width=self.WIDTH,
            height=self.HEIGHT,
            input=self.thumbnail_dir,
            output=sprite_file,
        )
        subprocess.run(shlex.split(cmd))

        return self

    def ips_seconds_to_timestamp(self, ips):
        return time.strftime(self.WEBVTT_TIME_FORMAT, time.gmtime(ips))

    def webvtt_getx(self, imnumber, w, h):
        # coordinate in sprite image for a given image
        gridsize = self.ROWS * self.COLS
        imnumber = imnumber - ((imnumber // gridsize) * gridsize)
        windex = imnumber % self.COLS
        return windex * w

    def webvtt_gety(self, imnumber, w, h):
        # coordinate in sprite image for a given image
        gridsize = self.ROWS * self.COLS
        imnumber = imnumber - ((imnumber // gridsize) * gridsize)
        hindex = imnumber // self.ROWS
        return hindex * h

    def webvtt_content(self):
        contents = [self.WEBVTT_HEADER]
        file_name = os.path.split(self.sprite_file)[1]
        start, end = 0, self.IPS
        w, h = self.WIDTH, self.HEIGHT
        for i in range(0, self.count_files()):
            contents += [
                self.WEBVTT_TIMELINE_FORMAT.format(
                    start=self.ips_seconds_to_timestamp(start),
                    end=self.ips_seconds_to_timestamp(end),
                ),
                self.WEBVTT_IMAGE_TITLE_FORMAT.format(
                    x=self.webvtt_getx(i, w, h),
                    y=self.webvtt_gety(i, w, h),
                    w=w,
                    h=h,
                    filename=file_name,
                ),
            ]
            start = end
            end += self.IPS
        return contents

    def generate_webvtt(self, webvtt_file):
        with open(webvtt_file, "w") as f:
            f.writelines(self.webvtt_content())

    @classmethod
    def from_media(
        cls,
        video_path,
        thumbnail_dir,
        sprite_file,
        webvtt_file,
        delete_existing_thumbnail_dir=False,
    ):
        if os.path.isdir(thumbnail_dir):
            if os.listdir(thumbnail_dir):
                raise Exception(f"There are already files in {thumbnail_dir}!")
        else:
            raise Exception(
                f"{thumbnail_dir} doesn't exist, create it before calling MontageSprites.from_media()"
            )

        montage = MontageSprites(
            video_path=video_path,
            thumbnail_dir=thumbnail_dir,
        )
        montage.generate_thumbs()
        montage.generate_sprite(sprite_file)
        montage.generate_webvtt(webvtt_file)
        return montage
