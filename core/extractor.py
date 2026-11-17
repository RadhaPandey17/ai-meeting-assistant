import os
from utils.Audio_processor import download_youtube_audio, convert_to_wav, chunk_audio
from core.transcriber import transcribe_all

def extract_transcript(source: str, language: str = "english", chunk_minutes: int = 5) -> str:
    """
    Extracts complete transcript from a YouTube URL or local audio/video file.
    
    :param source: YouTube URL or local media file path.
    :param language: 'english' (Whisper local model) or 'hinglish' (Sarvam AI API).
    :param chunk_minutes: Audio split duration in minutes.
    :return: Full transcribed string.
    """
    if source.startswith("http://") or source.startswith("https://"):
        print(f"Downloading YouTube audio from: {source}")
        raw_audio = download_youtube_audio(source)
        remove_orig = True
    else:
        print(f"Using local audio file: {source}")
        raw_audio = source
        remove_orig = False

    print("Converting audio to 16kHz mono WAV...")
    mono_audio = convert_to_wav(raw_audio, remove_original=remove_orig)

    print(f"Chunking audio into {chunk_minutes}-minute segments...")
    chunks = chunk_audio(mono_audio, chunk_minutes=chunk_minutes)

    print(f"Transcribing using language='{language}'...")
    transcript = transcribe_all(chunks, language=language)

    return transcript


if __name__ == "__main__":
    import sys
    test_url = "https://www.youtube.com/watch?v=HdafI0t3sEY&t=11s"
    lang = "english"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    if len(sys.argv) > 2:
        lang = sys.argv[2]
        
    result = extract_transcript(test_url, language=lang)
    print("\n--- Extracted Transcript ---")
    print(result[:500] + ("..." if len(result) > 500 else ""))
