from utils import download_video, extract_comments, transcribe_mp4, DATA_DIR, METADATA_FILE, get_video_urls_from_user, write_metadata, tag_narratives, transfer_metadata

import json
import math
import os

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


def get_10_comments():
    global checked_clean_users
    with open('bad_videos_metadata.json', 'r') as f:
        bad_video_data = json.load(f)

    bad_video_authors = set([video_data['username']
                            for video_data in bad_video_data.values()])
    MAX_CHECK_COMMENTERS_PER_VIDEO = 20

    user_suspicions = {}
    for video_url, video_data in bad_video_data.items():
        for comment in video_data['comments'][:MAX_CHECK_COMMENTERS_PER_VIDEO]:
            username = comment['username']
            if (username in checked_clean_users) or (username in bad_video_authors):
                continue  # We already checked this user
            if username not in user_suspicions:
                user_suspicions[username] = 0  # Initialize suspicion score
            user_suspicions[username] += 10  # We saw this user commenting
            if comment['is_top_list_marked']:
                user_suspicions[username] += 5
            if comment['is_liked_by_author']:
                user_suspicions[username] += 10
            if comment['likes'] > 0:
                user_suspicions[username] += math.log(comment['likes'], 2) + 1

    # Get the 10 most suspicious users by sorting the suspicion scores
    most_suspicious_users = sorted(
        user_suspicions.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 most suspicious users:")
    for username, suspicion_score in most_suspicious_users:
        print(f"{username}: {suspicion_score:.1f}")
    return list(user_suspicions.keys())


def check_user(username):
    urls = get_video_urls_from_user(username, n=1)
    print(f"for suspicious user {username}: {urls}")
    
    all_narratives = []
    for url in urls:
        try:
            download_video(url)
            extract_comments(url)
            transcribe_mp4(url)
            narratives = tag_narratives(url)
            write_metadata()
            all_narratives.extend(narratives)
            if len(narratives) > 0:
                transfer_metadata(url, 'bad_videos_metadata.json')
        except Exception as e:
            print(f"Error processing {url}: {e}")
            continue
    return all_narratives


if __name__ == "__main__":
    # roach drop site
    roach_drop = 'https://www.tiktok.com/@jeffrey1012/video/7298550647857728786?q=ukraine%20war%20corruption&t=1731700011325'
    #roach_drop = 'https://www.tiktok.com/@tulsigabbard/video/7299018744955800874?q=zelensky%20is%20corrupt&t=1731711530705'
    # Clean up data directory
    os.makedirs(DATA_DIR, exist_ok=True)
    for file in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    if os.path.exists('bad_videos_metadata.json'): os.remove('bad_videos_metadata.json')
    with open('metadata.json', 'w') as f: json.dump({}, f)

    download_video(roach_drop)
    extract_comments(roach_drop)
    transcribe_mp4(roach_drop)
    tag_narratives(roach_drop)
    write_metadata()
    os.rename('metadata.json', 'bad_videos_metadata.json')

    checked_clean_users = []
    for roach_cycle_i in range(1):
        with open('metadata.json', 'w') as f: json.dump({}, f)
        suspicious_users = get_10_comments()
        print(suspicious_users)
        for suspicious_user in suspicious_users:
            found_narratives = check_user(suspicious_user)
            if len(found_narratives) == 0: 
                checked_clean_users.append(suspicious_user)
                print(f"User {suspicious_user} is clean")
            else:
                print(f"User {suspicious_user} is bad")
