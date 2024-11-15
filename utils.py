# utils.py
from openai import OpenAI
from moviepy.editor import VideoFileClip
import os
import json

import pyktok as pyk
pyk.specify_browser('safari')

metadata = {}
METADATA_FILE = "metadata.json"
DATA_DIR = "tiktok_data/"

def clean_url(url: str) -> str:
    """Remove query parameters from URL."""
    return url.split('?')[0]


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
    paths = pyk.save_tiktok(
        url,
        True,
        "test.json",
        'safari',
        return_fns=True,
    )
    video_path, metadata_path = paths["video_fn"], paths["metadata_fn"]
    os.makedirs(DATA_DIR, exist_ok=True)
    video_filename = os.path.basename(video_path)
    new_video_path = os.path.join(DATA_DIR, video_filename)
    os.rename(video_path, new_video_path)
    update_metadata(url, "local_video_path", new_video_path)


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
