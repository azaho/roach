# utils.py
from openai import OpenAI
from utils import update_metadata
from moviepy.editor import VideoFileClip
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
    """Write metadata to disk. Slow, call sparingly."""
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


def transcribe_mp4(video_data):
    video_path = video_data["local_video_path"]
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

    update_metadata(video_data["url"], "transcript",
                    transcript["text"])

    video.close()
    os.remove(video_path)
    os.remove(audio_filename)


if __name__ == "__main__":
    download_video(
        'https://www.tiktok.com/@extramediummedia/video/7437256130079788330?is_from_webapp=1&sender_device=pc',
        'video_data.csv',
    )
    write_metadata()
