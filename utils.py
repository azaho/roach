# utils.py
import os
import csv
import json
import hashlib

from openai import OpenAI
from moviepy.editor import VideoFileClip

import pyktok as pyk
pyk.specify_browser('safari')

metadata = {}
METADATA_FILE = "metadata.json"
DATA_DIR = "tiktok_data/"

def clean_url(url: str) -> str:
    """Remove query parameters from URL."""
    return url.split('?')[0]

def hash_url(url: str) -> str:
    """Turn url into unique hash."""
    return hashlib.md5(url.encode()).hexdigest()

def write_metadata():
    """Write metadata to disk. Slow, call sparingly."""
    with open('metadata.json', 'w') as f:
        f.write(json.dumps(metadata))


def update_metadata(url: str, update_key: str, update_val):
    """Add field to a video's metadata."""
    global metadata
    if metadata == {}:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)

    url = clean_url(url)
    if url not in metadata:
        metadata[url] = {"url": url}
    metadata[url][update_key] = update_val


def get_metadata(url: str):
    """Returns metadata object given url identifier."""
    url = clean_url(url)
    return metadata[url]

def get_metadata_by_author(author_id: str):
    for url, data in metadata.items():
        if data["author_id"] == author_id:
            return data
    return {}


def download_video(url: str):
    """Download TikTok video."""
    metadata_path = os.path.join(DATA_DIR, hash_url(url) + "_metadata.json")
    paths = pyk.save_tiktok(
        url,
        True,
        metadata_path,
        'safari',
        return_fns=True,
    )

    # write local video path
    video_path, metadata_path = paths["video_fn"], paths["metadata_fn"]
    os.makedirs(DATA_DIR, exist_ok=True)
    video_filename = os.path.basename(video_path)
    new_video_path = os.path.join(DATA_DIR, video_filename)
    os.rename(video_path, new_video_path)
    update_metadata(url, "local_video_path", new_video_path)

    # write video metadata
    video_metadata = get_video_metadata(metadata_path)
    update_metadata(url, "username", video_metadata["author"]["username"])
    update_metadata(url, "timestamp", video_metadata["timestamp"])
    update_metadata(url, "stats", video_metadata["stats"])
    update_metadata(url, "description", video_metadata["description"])
    update_metadata(url, "location", video_metadata["location"])
    os.remove(metadata_path)

def get_video_metadata(metadata_path: str):
    """Extracts info from a video's metadata csv and writes to global metadata."""
    video_data = {}
    with open(metadata_path) as f:
        reader = csv.DictReader(f)
        # there's just one row, but we read them all anyway
        row = next(reader)
        vid = row['video_id']
        video_data = {
            'video_id': row['video_id'],
            'timestamp': row['video_timestamp'],
            'stats': {
                'duration': int(row['video_duration']),
                'likes': int(row['video_diggcount']),
                'shares': int(row['video_sharecount']), 
                'comments': int(row['video_commentcount']),
                'plays': int(row['video_playcount'])
            },
            'author': {
                'username': row['author_username'],
                'name': row['author_name']
            },
            'description': row['video_description'],
            'location': row['video_locationcreated']
        }
    return video_data

def transcribe_mp4(url):
    try:
        video_metadata = get_metadata(url)
    except:
        print(f"Oops, don't have metadata yet for url {url}")
        return False

    url = video_metadata["url"]
    video_path = video_metadata["local_video_path"]
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    video = VideoFileClip(video_path)
    audio_filename = video_path.replace('.mp4', '.mp3')

    video.audio.write_audiofile(audio_filename)
    transcript = ""
    with open(audio_filename, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
        )

    update_metadata(url, "transcript", transcript.text)

    video.close()
    os.remove(video_path)
    os.remove(audio_filename)


if __name__ == "__main__":
    url = 'https://www.tiktok.com/@cakedivy/video/7427654268519189791?is_from_webapp=1&sender_device=pc'
    download_video(url)
    transcribe_mp4(url)
    write_metadata()
