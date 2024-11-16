from openai import OpenAI
from moviepy.editor import VideoFileClip
import os

def transcribe_mp4(filename: str) -> dict:
    """
    Extract audio from MP4 file and transcribe using OpenAI Whisper API
    
    Args:
        filename (str): Path to MP4 file
        
    Returns:
        dict: Whisper API response containing transcription and word-level timestamps
    """
    # Extract audio from video
    video = VideoFileClip(filename)
    audio_filename = filename.replace('.mp4', '.mp3')
    video.audio.write_audiofile(audio_filename)
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Transcribe audio file
    with open(audio_filename, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1", 
            response_format="verbose_json",
            timestamp_granularities=["word"]
        )
    
    # Clean up temporary audio file
    #os.remove(audio_filename)
    
    return transcript


if __name__ == "__main__":
    transcript = transcribe_mp4("test.mp4")
    print(transcript)
