import os
from dotenv import load_dotenv
from core.extractor import extract_transcript

# Load environment variables from .env file (for Sarvam AI / Whisper / Mistral settings)
load_dotenv()


def test_full_pipeline(url: str, language: str = "english"):
    """
    Runs the full end-to-end pipeline via core.extractor.
    """
    print("=" * 60)
    print(f"Running Extraction Pipeline (language='{language}')...")
    print("=" * 60)
    
    transcript = extract_transcript(url, language=language)
    return transcript


if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=HdafI0t3sEY&t=11s"
    
    # Use language="english" for Whisper or language="hinglish" for Sarvam AI
    transcript = test_full_pipeline(test_url, language="english")
    
    print("\n" + "=" * 60)
    print("FINAL TRANSCRIPT:")
    print("=" * 60)
    print(transcript)
    
    # Save transcript to file for easy viewing
    output_file = "transcript.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcript)
    print(f"\n-> Saved complete transcript to: {os.path.abspath(output_file)}")


