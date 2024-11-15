# utils.py
import pyktok as pyk
pyk.specify_browser('safari')

def download_video(url: str, csv_output_path: str):
    """Download TikTok video."""
    pyk.save_tiktok(
        url,
        True,
        csv_output_path,
        'safari'
    )

if __name__ == "__main__":
    download_video(
        'https://www.tiktok.com/@extramediummedia/video/7437256130079788330?is_from_webapp=1&sender_device=pc',
        'video_data.csv',
    )