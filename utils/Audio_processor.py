import yt_dlp
from pydub import AudioSegment
import os

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        'format': "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
        "quiet": False,
        "nocheckcertificate": True,
        "logtostderr": False,
        "overwrites": True,
        "restrictfilenames": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base_filename = ydl.prepare_filename(info)
        filename = os.path.splitext(base_filename)[0] + ".wav"

    return filename


def convert_to_wav(input_path: str, remove_original: bool = True) -> str:
    """Converts any local audio/video file to 16kHz mono WAV format and optionally removes the raw input file."""
    try:
        audio = AudioSegment.from_file(input_path)
        base_name = os.path.splitext(input_path)[0]
        if base_name.endswith("_mono16k"):
            output_path = input_path
        else:
            output_path = f"{base_name}_mono16k.wav"

        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(output_path, format="wav")

        # Automatically remove the raw downloaded audio file
        if remove_original and input_path != output_path and os.path.exists(input_path):
            os.remove(input_path)

        return output_path
    except Exception as e:
        print(f"Error converting {input_path} to wav: {e}")
        raise e


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list[str]:
    """Splits a WAV audio file into chunks of chunk_minutes length (mono, 16kHz)."""
    audio = AudioSegment.from_file(wav_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    chunk_length_ms = int(chunk_minutes * 60 * 1000)  # 60 * 1000 -> 1 min in ms
    base_name = os.path.splitext(wav_path)[0]

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start: start + chunk_length_ms]  # Slicing the audio into chunks
        chunk_path = f"{base_name}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks



if __name__ == "__main__":
    audio_file = download_youtube_audio("https://www.youtube.com/watch?v=mtiOK2QG9Q0")
    print(f"Downloaded raw audio saved at: {audio_file}")

    mono_16k_file = convert_to_wav(audio_file)
    print(f"Converted 16kHz Mono audio saved at: {mono_16k_file}")

    chunks = chunk_audio(mono_16k_file, chunk_minutes=5)
    print("\n--- Chunk Paths ---")
    for c in chunks:
        print(c)