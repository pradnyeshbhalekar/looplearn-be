import os
import re
import uuid
import edge_tts
import asyncio
from dotenv import load_dotenv
from pydub import AudioSegment
import static_ffmpeg
from tenacity import retry, stop_after_attempt, wait_exponential
import cloudinary
import cloudinary.uploader

load_dotenv()

# Render's native Python runtime (no Dockerfile, no apt access) doesn't ship
# ffmpeg or ffprobe, which pydub's stitching (generate_podcast_audio_and_upload)
# needs — pydub's AudioSegment.from_file shells out to BOTH, even when the
# format is passed explicitly (confirmed: it always calls mediainfo_json,
# which runs ffprobe). static-ffmpeg provides static binaries for both via a
# pip dependency, fetched from GitHub on first use and cached for the life of
# the process.
#
# pydub's AudioSegment.converter IS respected for the ffmpeg binary, but its
# ffprobe lookup (get_prober_name() in pydub/utils.py) ONLY ever does
# which("ffprobe") against PATH — there is no equivalent override attribute,
# confirmed by reading pydub's source after AudioSegment.ffprobe = ... had no
# effect. So both binaries' directory is prepended to PATH directly.
#
# Resolved LAZILY (on first podcast-audio call), not at import time: this
# module is imported by pipeline_service.py -> pipeline_routes.py, which
# app/run.py registers at startup, so an eager fetch here would make the
# ENTIRE app's boot depend on a GitHub download succeeding — including the
# existing single-voice daily pipeline, which never needed pydub/ffmpeg at
# all. Confined to only the code path that actually needs it instead.
_ffmpeg_ready = False


def _ensure_ffmpeg_ready():
    global _ffmpeg_ready
    if _ffmpeg_ready:
        return
    ffmpeg_path, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    AudioSegment.converter = ffmpeg_path
    os.environ["PATH"] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")
    _ffmpeg_ready = True

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

async def generate_audio_and_upload(text: str, topic_slug: str):
    local_file = f"{topic_slug}.mp3"
    timestamps = []
    
    try:
        print("Generating audio and extracting timestamps...")
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")

        # Open the local file in binary write mode
        with open(local_file, "wb") as file:
            # Stream the generation instead of just saving it
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    # Write the actual audio bytes to the file
                    file.write(chunk["data"])
                    
                elif chunk["type"] == "WordBoundary":
                    # edge-tts offsets are in 100-nanosecond units. We divide by 10,000,000 to get seconds.
                    start_sec = chunk["offset"] / 10_000_000
                    duration_sec = chunk["duration"] / 10_000_000
                    
                    timestamps.append({
                        "word": chunk["text"],
                        "start": round(start_sec, 3), # Rounding keeps the JSON payload smaller
                        "end": round(start_sec + duration_sec, 3)
                    })

        print("Uploading audio to Cloudinary...")
        response = cloudinary.uploader.upload(local_file, resource_type="video", folder='looplearn_audio')
        audio_url = response.get('secure_url')
        print("✅ Audio uploaded to Cloudinary successfully.")

        # Return both the URL and the timestamp array
        return audio_url, timestamps

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None 

    finally:
        if os.path.exists(local_file):
            os.remove(local_file)
            print(f"🗑️ Cleaned up local file: {local_file}")


def create_commuter_audio(text_content, topic_slug, domain_name="Software Engineering", topic_title="this topic"):
    """Returns a tuple: (audio_url, timestamps)"""
    # Remove markdown syntax to prevent TTS from reading things like "hash hash" or "asterisk asterisk"
    clean_text = re.sub(r'[#*_`]', '', text_content)
    
    # Prepend the polite intro
    intro_text = f"Hello there, welcome to LoopLearn! Today at {domain_name}, we will have a look at {topic_title}. "
    full_text = intro_text + clean_text
    return asyncio.run(generate_audio_and_upload(full_text, topic_slug))


HOST_VOICES = {
    "HOST_A": "en-US-AvaNeural",
    "HOST_B": "en-US-AndrewNeural",
}
LINE_GAP_MS = 350


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=15), reraise=True)
async def _synthesize_line_to_file(text: str, voice: str, local_file: str):
    # edge-tts intermittently raises "No audio was received" on a transient
    # connection hiccup with the underlying service — retry rather than
    # fail the whole podcast over one flaky line.
    communicate = edge_tts.Communicate(text, voice)
    wrote_audio = False
    with open(local_file, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
                wrote_audio = True

    if not wrote_audio:
        raise RuntimeError(f"edge-tts produced no audio for voice={voice}")


async def generate_podcast_audio_and_upload(dialogue: list[dict], topic_slug: str):
    """
    Synthesizes a two-host podcast script: each line gets its host's
    edge-tts voice, lines are stitched into one MP3 (with a short silence
    between lines) via pydub, and the result is uploaded to Cloudinary.

    Returns (audio_url, line_timestamps) where line_timestamps is
    [{"host", "text", "start", "end"}, ...] in seconds, measured against
    the final stitched track — not word-level, but enough to sync a
    transcript to the audio.
    """
    _ensure_ffmpeg_ready()

    run_id = uuid.uuid4().hex[:8]
    line_files = []
    combined = AudioSegment.empty()
    line_timestamps = []
    cursor_ms = 0

    try:
        for i, line in enumerate(dialogue):
            host = line.get("host")
            text = line.get("text", "")
            voice = HOST_VOICES.get(host)
            # edge-tts deterministically errors on text with no speakable
            # content (empty, or punctuation-only like "..."), so filter
            # those out rather than let a bad line fail the whole podcast.
            if not voice or not re.search(r"[A-Za-z0-9]", text):
                continue

            local_file = f"loop_in_line_{run_id}_{i}.mp3"
            line_files.append(local_file)

            await _synthesize_line_to_file(text, voice, local_file)

            segment = AudioSegment.from_file(local_file, format="mp3")
            duration_ms = len(segment)

            line_timestamps.append({
                "host": host,
                "text": text,
                "start": round(cursor_ms / 1000, 3),
                "end": round((cursor_ms + duration_ms) / 1000, 3)
            })

            combined += segment
            if i < len(dialogue) - 1:
                combined += AudioSegment.silent(duration=LINE_GAP_MS)
            cursor_ms += duration_ms + LINE_GAP_MS

        if len(combined) == 0:
            raise ValueError("No dialogue lines produced audio")

        final_file = f"loop_in_podcast_{topic_slug}_{run_id}.mp3"
        combined.export(final_file, format="mp3")

        print("Uploading podcast audio to Cloudinary...")
        response = cloudinary.uploader.upload(final_file, resource_type="video", folder="loop_in_podcast")
        audio_url = response.get("secure_url")
        print("✅ Podcast audio uploaded to Cloudinary successfully.")

        if os.path.exists(final_file):
            os.remove(final_file)

        return audio_url, line_timestamps

    except Exception as e:
        print(f"❌ Error generating podcast audio: {e}")
        return None, None

    finally:
        for local_file in line_files:
            if os.path.exists(local_file):
                os.remove(local_file)


def create_podcast_audio(dialogue: list[dict], topic_slug: str):
    """Returns a tuple: (audio_url, line_timestamps)"""
    return asyncio.run(generate_podcast_audio_and_upload(dialogue, topic_slug))


if __name__ == "__main__":
    sample_text = "Welcome to LoopLearn. Today's case study breaks down how Netflix handles global traffic using API Gateways."
    sample_slug = "netflix-api-gateway-test"
    
    # Test the function
    final_url, word_timestamps = create_commuter_audio(sample_text, sample_slug)
    
    if final_url:
        print(f"\n🔗 URL to save in Neon DB: {final_url}")
        print(f"⏱️ Total words mapped: {len(word_timestamps)}")
        print(f"🔍 Sample of first 3 words:\n{word_timestamps[:3]}")