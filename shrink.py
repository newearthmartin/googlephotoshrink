#!/usr/bin/env python3

import os
import sys
import pathlib
import shutil
from PIL import Image

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp"}
MEDIA_EXTENSIONS = PHOTO_EXTENSIONS.union(VIDEO_EXTENSIONS)


def find_media_with_metadata(root_folder):
    rv = []
    for dirpath, _, jsons in os.walk(root_folder):
        last_dir = os.path.basename(os.path.normpath(dirpath))
        if not last_dir.startswith('Photos from'):
            continue
        dir_json = [file for file in jsons if file.lower().endswith('.json')]
        local_dir = dirpath.replace(root_folder, '')
        if local_dir.startswith('/'):
            local_dir = local_dir[1:]
        for file in jsons:
            filename, extension = os.path.splitext(file)
            extension = extension.lower()
            if extension not in MEDIA_EXTENSIONS:
                continue
            jsons = [j for j in dir_json if j.startswith(file)]
            if not jsons:
                jsons = [j for j in dir_json if j.startswith(filename)]
            jsonpath = os.path.join(dirpath, jsons[0]) if jsons else None
            rv.append((os.path.join(local_dir, file), jsonpath))
    return rv


def process_files(root_folder, out_folder, matched_files):
    for i, (filepath, jsonpath) in enumerate(matched_files):
        filename, extension = os.path.splitext(filepath)
        extension = extension.lower()
        if extension in PHOTO_EXTENSIONS:
            is_photo = True
        elif extension in VIDEO_EXTENSIONS:
            is_photo = False
        else:
            print(f'Unexpected extension {extension}')
            continue
        if is_photo:
            process_photo(filepath, root_folder, out_folder)
        else:
            process_video(filepath, root_folder, out_folder)


def process_photo(filepath, root_folder, out_folder):
    infile = os.path.join(root_folder, filepath)
    outfile = os.path.join(out_folder, filepath)
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    if os.path.exists(outfile):
        if os.path.getsize(outfile) == 0:
            os.remove(outfile)
        else:
            return

    filename, extension = os.path.splitext(filepath)
    extension = extension.lower()

    if extension not in ['.jpg', '.jpeg']:
        print(f'Copying {infile}')
        shutil.copy2(infile, outfile)
        return

    print(f'Compressing {infile}')
    shrink_jpg(infile, outfile, quality=90, min_size=1000)
    if os.path.getsize(outfile) > os.path.getsize(infile):
        print(f'New file larger! Keeping original {infile}')
        os.remove(outfile)
        shutil.copy2(infile, outfile)


def shrink_jpg(input_path, output_path, quality=90, min_size=1000):
    with Image.open(input_path) as img:
        exif_data = img.info.get("exif", b"")
        width, height = img.size
        if width < height:
            new_width = min_size
            new_height = int((min_size / width) * height)
        else:
            new_height = min_size
            new_width = int((min_size / height) * width)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=quality,
                 optimize=True, exif=exif_data)


def process_video(filepath, root_folder, out_folder):
    infile = os.path.join(root_folder, filepath)
    outfile = os.path.join(out_folder, 'videos', os.path.basename(filepath))
    if not os.path.exists(outfile) or os.path.getsize(outfile) == 0:
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        print(f'Compressing {infile}')
        command = (f'ffmpeg -i "{infile}" -vf "scale=-2:720" -c:v libx264 -preset slow -crf 28 -b:v 1M -c:a aac '
                   f'-b:a 128k -movflags +faststart -map_metadata 0 "{outfile}"')
        os.system(command)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python shrink.py path/to/google_photos_folder')
        exit(1)
    root_folder = sys.argv[1]
    root_path = pathlib.Path(root_folder)
    out_folder = os.path.join(root_path.parent, root_path.name + '__out')
    os.makedirs(out_folder, exist_ok=True)

    matched_files = find_media_with_metadata(root_folder)
    print(f'Found {len(matched_files)} media files.')
    process_files(root_folder, out_folder, matched_files)
