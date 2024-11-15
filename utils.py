# utils.py
import os
import json

import pyktok as pyk
pyk.specify_browser('safari')

metadata = {}

VIDEO_DIR = "tiktok_data/videos/"

def clean_url(url: str) -> str:
   """Remove query parameters from URL."""
   return url.split('?')[0]

def write_metadata():
    with open('metadata.json', 'w') as f:
        f.write(json.dumps(metadata))

def update_metadata(url: str, update_key: str, update_val):
    """Add field to a video's metadata."""
    global metadata
    if metadata == {}:
        with open('metadata.json') as f:
            metadata = json.load(f)
    url = clean_url(url)
    if url not in metadata:
        metadata[url] = {}
    metadata[url][update_key] = update_val
    write_metadata()

def download_video(url: str, csv_output_path: str):
    """Download TikTok video."""
    paths = pyk.save_tiktok(
        url,
        True,
        csv_output_path,
        'safari',
        return_fns=True,
    )
    video_path, metadata_path = paths["video_fn"], paths["metadata_fn"]
    os.makedirs(VIDEO_DIR, exist_ok=True)
    video_filename = os.path.basename(video_path)
    new_video_path = os.path.join(VIDEO_DIR, video_filename)
    os.rename(video_path, new_video_path)
    update_metadata(url, "local_video_path", new_video_path)

if __name__ == "__main__":
    download_video(
        'https://www.tiktok.com/@extramediummedia/video/7437256130079788330?is_from_webapp=1&sender_device=pc',
        'video_data.csv',
    )