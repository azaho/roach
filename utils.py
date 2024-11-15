# utils.py
import os
import csv
import ast
import json
import hashlib
import pandas as pd

from openai import OpenAI
from moviepy.editor import VideoFileClip

import pyktok as pyk

PYK_BROWSER = 'firefox' 

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


pyk.specify_browser(PYK_BROWSER)

metadata = {}
METADATA_FILE = "metadata.json"
DATA_DIR = "tiktok_data/"

### URL helpers

def clean_url(url: str) -> str:
    """Remove query parameters from URL."""
    return url.split('?')[0]

def hash_url(url: str) -> str:
    """Turn url into unique hash."""
    return hashlib.md5(url.encode()).hexdigest()

### Metadata helpers

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

### Download video

def download_video(url: str):
    """Download TikTok video."""
    metadata_path = os.path.join(DATA_DIR, hash_url(url) + "_metadata.json")
    paths = pyk.save_tiktok(
        url,
        True,
        metadata_path,
        PYK_BROWSER,
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
    video_metadata = get_video_metadata(metadata_path, single_video=True)
    update_metadata(url, "username", video_metadata["author"]["username"])
    update_metadata(url, "timestamp", video_metadata["timestamp"])
    update_metadata(url, "stats", video_metadata["stats"])
    update_metadata(url, "description", video_metadata["description"])
    update_metadata(url, "location", video_metadata["location"])
    os.remove(metadata_path)

def get_video_metadata(metadata_path: str, single_video: bool = False):
    """Extracts info from a video's metadata csv and writes to global metadata."""
    video_data = {}
    with open(metadata_path) as f:
        reader = csv.DictReader(f)
        # there's just one row, but we read them all anyway
        for row in reader:
            vid = row['video_id']
            if vid not in video_data:
                video_data[vid] = {
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
    return video_data if not single_video else list(video_data.values())[0]

### Extract comments

def _convert_none_strings(d):
    if isinstance(d, dict):
        return {k: _convert_none_strings(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [_convert_none_strings(x) for x in d]
    elif d == 'None':
        return None
    return d

def get_comment_data(comment):
    """Takes in dataframe row and returns dict."""
    # Parse the user dictionary string
    user_dict = _convert_none_strings(comment.user)
    
    return {
        'commenter_id': user_dict['uid'],
        'username': user_dict['unique_id'],
        'text': comment.text,
        'likes': comment.digg_count,
        'timestamp': comment.create_time,
        'is_liked_by_author': comment.is_author_digged,
        'is_top_list_marked': ('top_list' in comment.sort_tags)
    }

def extract_comments(url: str, n=30):
    """Takes url and adds comments to video metadata."""
    comments_df = pyk.save_tiktok_comments(
        url,
        comment_count=n,
        save_comments=False,
        return_comments=True
    )
    comments_list = [get_comment_data(comment) for comment in comments_df.itertuples()]
    update_metadata(url, "comments", comments_list)

### Transcribe video

def transcribe_mp4(url: str):
    """Takes url and adds transcription to video metadata."""
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

### Get user's videos

def get_video_urls_from_user(username: str, n=3):
    """Takes username and returns urls of some recent videos by them."""
    metadata_path = os.path.join(DATA_DIR, hash_url(url) + "_videos.json")
    try:
        pyk.save_tiktok_multi_page(
            username,
            ent_type='user',
            video_ct=n,
            save_video=False,
            metadata_fn=metadata_path,
        )
    except:
        pass

    video_metadata = get_video_metadata(metadata_path, single_video=False)
    urls = [
        f'https://www.tiktok.com/@{username}/video/{video_id}'
        for video_id, data in video_metadata.items()
    ]
    os.remove(metadata_path)
    return urls


### Test case if run as main

if __name__ == "__main__":
    url = 'https://www.tiktok.com/@jeffrey1012/video/7298550647857728786?q=ukraine%20war%20corruption&t=1731700011325'
    os.makedirs(DATA_DIR, exist_ok=True)
    for file in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

    download_video(url)
    extract_comments(url)
    transcribe_mp4(url)
    urls = get_video_urls_from_user("cakedivy")
    print(urls)
    write_metadata()
