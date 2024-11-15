# utils.py
import os
import re
import csv
import ast
import json
import hashlib
import pandas as pd
from typing import Union
from pydantic import BaseModel
from datetime import datetime, timezone

from openai import OpenAI
from moviepy.editor import VideoFileClip

import pyktok as pyk
pyk.specify_browser('safari')

metadata = {}
METADATA_FILE = "metadata.json"
DATA_DIR = "tiktok_data/"

### OpenAI client

client = None
def get_openai_client():
    global client
    if client == None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client

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

def sync_metadata():
    """Load from metadata file into local memory."""
    global metadata
    if metadata == {}:
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)

def update_metadata(url: str, update_key: str, update_val):
    """Add field to a video's metadata."""
    sync_metadata()
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
    client = get_openai_client()
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

THREE_DAYS_OLD = 3 * 3600 * 24
def video_is_recent(video_data: dict):
    """Takes video data and returns whether it's from the last few days."""
    timestamp_str = video_data["timestamp"]
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
    timestamp = timestamp.replace(tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)
    time_diff_in_seconds = abs((current_time - timestamp).total_seconds())
    return time_diff_in_seconds < THREE_DAYS_OLD

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
        if video_is_recent(data)
    ]
    os.remove(metadata_path)
    return urls


### Tag video with narratives (Reality Check!)

# Define Pydantic models for structured responses
class DisinformationResponseWithResult(BaseModel):
    result: int
    narratives: list[Union[str, int]]

class DisinformationResponseOnlyNarratives(BaseModel):
    narratives: list[Union[str, int]]

known_narratives = """
1. The "special military operation" is not a war, but a "liberation" of the Ukrainian people.
2. Ukraine has always been and remains a part of Russia.
3. Ukraine is a threat to Russia.
4. The Ukrainian government and military are neo-Nazis.
5. The Russian language and culture are banned in Ukraine.
6. Russia is protecting ethnic Russians in Ukraine.
7. The West is imposing unfair sanctions on Russia.
8. The real aggressor is Ukraine and NATO, while Russia is the victim.
9. Ukraine is developing biological weapons with US help.
10. The Bucha massacre was staged by Ukraine.
11. Ukraine shot down MH17, not Russia.
12. The West is using Ukraine to weaken Russia.
13. Ukrainian refugees are causing problems in host countries.
14. Ukraine's military successes are exaggerated.
15. Western weapons sent to Ukraine end up on the black market.
16. Zelensky has left Ukraine and hasn't returned.
17. Russian retreats are "goodwill gestures."
18. Ukrainian troops may revolt against Zelensky.
19. Ukraine is a failed state.
20. Diseases are spreading widely in the Ukrainian army.
21. Ukrainians are ready to kill their own people.
22. Ukraine is sabotaging peace negotiations with Russia.
23. The Ukrainian Armed Forces are attacking civilian targets.
24. Russia does not spread disinformation on its territory.
25. The conflict can only be resolved if Ukraine surrenders.
"""

def check_disinformation(text):
    """Takes text and returns {result: 0 or 1, narratives: list[int]}."""
    completion = None
    early_no = None
    early_yes = None

    # Define regex patterns for detecting "no" or "yes" conclusions.
    no_regex = re.compile(
        r"(?:conclusion:|in conclusion,?|ultimately,?)?\s*(?:(?:no[,.]?|the (?:text|snippet|statement) (?:does not|doesn't) contain|(?:this )?(?:statement|text|content) is not)(?!\s+elements? consistent with).*?(?:russian narratives?|russian propaganda|elements? of (?:russian )?propaganda|propagandistic elements?)|\b(?:not propaganda|isn'?t propaganda)\b).*?(?:\.|$)",
        re.IGNORECASE,
    )
    yes_regex = re.compile(
        r"(?:conclusion:|in conclusion,?|ultimately,?)?\s*(?:yes[,.]?|the (?:text|snippet|statement) (?:does contain|contains)(?:\s+elements? consistent with)?|(?:this )?(?:statement|text|content) is).*?(?:russian narratives?|russian propaganda|elements? of (?:russian )?propaganda|propagandistic elements?).*?(?:\.|$)",
        re.IGNORECASE,
    )

    client = get_openai_client()
    # Use a short unstructured chain-of-thought approach
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a Russian propaganda detector. Respond concisely.",
            },
            {
                "role": "user",
                "content": f"""
                Here's a transcript from a video:
                <text>
                {text}
                </text>
                
                Does this text contain Russian narratives or propaganda? Think step-by-step, concisely.
                """,
            },
        ],
    )

    cot_analysis = completion.choices[0].message.content.strip()

    # Check for early "no" or "yes" conclusions
    early_no = no_regex.search(cot_analysis)
    early_yes = yes_regex.search(cot_analysis)

    if early_no:
        return {"result": 0, "narratives": []}

    # Instructions for getting Russian narratives
    russian_narratives_instructions = (
        "1-2 known Russian narratives present in the text in 3-8 words, then the corresponding integer ID"
    )

    if early_yes:
        # If early yes, ask for the narratives directly
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Russian propaganda detector. Respond concisely with the narratives present in JSON format.",
                },
                {
                    "role": "user",
                    "content": f"""
                    Here's a transcript from a video:
                    <text>
                    {text}
                    </text>
            
                    Your previous analysis showed that the video contains Russian narratives:
                    <analysis>
                    {cot_analysis}
                    </analysis>

                    Here is a list of known Russian narratives:
                    <known_narratives>
                    {known_narratives}
                    </known_narratives>

                    Write a concise list of {russian_narratives_instructions}.
                    """,
                },
            ],
            response_format=DisinformationResponseOnlyNarratives,
        )
        response_json = completion.choices[0].message.content
        response_dict = json.loads(response_json)
        response_dict["result"] = 1  # Set the result to 1 for "yes" answers
        return response_dict
    else:
        # If not an early yes, ask for further analysis
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Russian propaganda detector. Respond concisely in JSON format.",
                },
                {
                    "role": "user",
                    "content": f"""
                    Here's a transcript from a video:
                    <text>
                    {text}
                    </text>
            
                    Here is your previous analysis of whether it contains Russian narratives:
                    {cot_analysis}

                    Here is a list of known Russian narratives:
                    <known_narratives>
                    {known_narratives}
                    </known_narratives>
            
                    Based on the text and your previous analysis, respond 1 if there is Russian propaganda; respond 0 if not, or if it is ambiguous.

                    Then write a concise list of {russian_narratives_instructions}.
                    """,
                },
            ],
            response_format=DisinformationResponseWithResult,
        )
        response_json = completion.choices[0].message.content
        return json.loads(response_json)

narratives = []
NARRATIVES_PATH = "narratives.json"
def tag_narratives(url):
    """Takes video url and reads its transcript to tag with disinformation narratives."""
    global narratives
    if narratives == []:
        with open(NARRATIVES_PATH, 'r') as f:
            narratives = json.load(f)["narratives"]
    
    metadata = get_metadata(url)
    transcript = metadata["transcript"]
    result = check_disinformation(transcript)
    disinformation_found = result["result"] == 1
    update_metadata(url, "disinformation_found", disinformation_found)
    update_metadata(url, "narratives", result["narratives"])


### Test case if run as main

if __name__ == "__main__":
    #url = 'https://www.tiktok.com/@cakedivy/video/7427654268519189791?is_from_webapp=1&sender_device=pc'  # normal video
    url = 'https://www.tiktok.com/@jeffrey1012/video/7298550647857728786?q=ukraine%20war%20corruption&t=1731700011325'  # disinfo video
    sync_metadata()
    #download_video(url)
    #extract_comments(url)
    #transcribe_mp4(url)
    #write_metadata()
    #urls = get_video_urls_from_user("cakedivy", n=3)
    tag_narratives(url)
    write_metadata()
