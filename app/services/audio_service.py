import os
import edge_tts
import asyncio
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

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

import re

def create_commuter_audio(text_content, topic_slug, domain_name="Software Engineering", topic_title="this topic"):
    """Returns a tuple: (audio_url, timestamps)"""
    # Remove markdown syntax to prevent TTS from reading things like "hash hash" or "asterisk asterisk"
    clean_text = re.sub(r'[#*_`]', '', text_content)
    
    # Prepend the polite intro
    intro_text = f"Hello there, welcome to LoopLearn! Today at {domain_name}, we will have a look at {topic_title}. "
    full_text = intro_text + clean_text
    return asyncio.run(generate_audio_and_upload(full_text, topic_slug))


if __name__ == "__main__":
    sample_text = "Welcome to LoopLearn. Today's case study breaks down how Netflix handles global traffic using API Gateways."
    sample_slug = "netflix-api-gateway-test"
    
    # Test the function
    final_url, word_timestamps = create_commuter_audio(sample_text, sample_slug)
    
    if final_url:
        print(f"\n🔗 URL to save in Neon DB: {final_url}")
        print(f"⏱️ Total words mapped: {len(word_timestamps)}")
        print(f"🔍 Sample of first 3 words:\n{word_timestamps[:3]}")