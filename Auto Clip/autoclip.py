import os
import sys
import json
import asyncio
import subprocess
import imageio_ffmpeg
import whisper
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip

# Add ffmpeg to PATH so Whisper can find it
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_exe)

from google.antigravity import Agent, LocalAgentConfig

def extract_audio(video_path, audio_path):
    print(f"[*] Extracting audio from {video_path}...")
    try:
        result = subprocess.run([
            ffmpeg_exe, "-i", video_path, 
            "-q:a", "0", "-map", "a", audio_path, "-y"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print("[!] The video might not have an audio track or an error occurred.")
            print(result.stderr)
            sys.exit(1)
            
        print("[*] Audio extraction complete.")
    except Exception as e:
        print(f"[!] Error extracting audio: {e}")
        sys.exit(1)

def transcribe_audio(audio_path):
    print("[*] Loading Whisper model (this may take a moment on first run)...")
    model = whisper.load_model("base")
    print("[*] Transcribing audio with timestamps...")
    result = model.transcribe(audio_path)
    
    formatted_transcript = []
    for segment in result['segments']:
        formatted_transcript.append(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text'].strip()}")
    
    return "\n".join(formatted_transcript)

async def analyze_with_agent(transcript):
    print("[*] Spawning Antigravity Agent for highlight analysis...")
    
    system_prompt = """You are an expert AI short-form video editor (like a TikTok/Reels clip generator).
You will be provided with a timestamped audio transcript of a longer video.
Analyze the transcript and identify the 4 most engaging, standalone highlight clips (each roughly 15-45 seconds long).
For each clip, provide a catchy title, the start and end time, an overlay theme color (e.g., 'red', 'blue', 'green', 'gold'), and a list of short captions (broken down into smaller time segments).

Respond STRICTLY with a JSON array using this format:
[
  {
    "clip_id": 1,
    "title": "The Big Reveal",
    "start": 120.0,
    "end": 140.0,
    "theme_color": "red",
    "captions": [
      {"text": "Here is the big reveal", "start": 120.0, "end": 123.5},
      {"text": "Look at this data!", "start": 123.5, "end": 127.0}
    ]
  }
]
Do not output any markdown formatting (like ```json), just the raw JSON array.
"""
    
    config = LocalAgentConfig(system_instructions=system_prompt)
    
    async with Agent(config) as agent:
        print("[*] Sending transcript to Antigravity...")
        prompt = f"Analyze the following video transcript and return the JSON edit plan for 4 highlight clips:\n\n{transcript}"
        response = await agent.chat(prompt)
        
        full_text = ""
        async for token in response:
            full_text += token
            
        cleaned = full_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return cleaned.strip()

def create_text_image_clip(text, size, position='bottom', is_overlay=False, bg_color=(200, 50, 50, 200)):
    # Create image using Pillow
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 80 if is_overlay else 55)
    except:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    if position == 'center':
        x = (size[0] - tw) // 2
        y = (size[1] - th) // 2
    elif position == 'top':
        x = (size[0] - tw) // 2
        y = 150
    else:
        x = (size[0] - tw) // 2
        y = size[1] - th - 120
        
    # Draw background box for overlays
    if position == 'top' or is_overlay:
        pad = 30
        draw.rectangle([x-pad, y-pad, x+tw+pad, y+th+pad], fill=bg_color)
        
    # Shadow and text
    draw.text((x+4, y+4), text, font=font, fill=(0,0,0,255))
    draw.text((x, y), text, font=font, fill=(255,255,255,255))
    
    # Convert to MoviePy clip
    img_np = np.array(img)
    rgb = img_np[:, :, :3]
    alpha = img_np[:, :, 3] / 255.0
    
    clip = ImageClip(rgb)
    mask = ImageClip(alpha, is_mask=True)
    clip = clip.with_mask(mask)
    return clip

def apply_edits(video_path, output_path_base, plan_json):
    print("[*] Parsing editing plan and loading video...")
    try:
        plan = json.loads(plan_json)
    except Exception as e:
        print(f"[!] Error parsing JSON plan: {e}")
        return
        
    video = VideoFileClip(video_path)
    w, h = video.w, video.h
    
    colors = {
        'red': (220, 50, 50, 230),
        'blue': (50, 100, 220, 230),
        'green': (50, 200, 100, 230),
        'gold': (230, 180, 0, 230),
        'purple': (150, 50, 220, 230)
    }
    
    for clip_data in plan:
        clip_id = clip_data.get('clip_id', 1)
        title = clip_data.get('title', 'Highlight')
        start = clip_data.get('start', 0)
        end = clip_data.get('end', video.duration)
        theme_color = clip_data.get('theme_color', 'blue').lower()
        bg_color = colors.get(theme_color, colors['blue'])
        
        print(f"\n[*] Generating Clip {clip_id}: {title} ({start}s - {end}s)")
        
        # Ensure we don't go out of bounds
        end = min(end, video.duration)
        if start >= end:
            print("[!] Invalid timestamps for this clip. Skipping...")
            continue
            
        subclip = video.subclipped(start, end)
        overlays = []
        
        # Add big title card overlay at the top for the first 3 seconds
        title_clip = create_text_image_clip(f" {title.upper()} ", (w, h), position='top', bg_color=bg_color, is_overlay=True)
        title_clip = title_clip.with_start(0).with_duration(min(3.0, subclip.duration))
        overlays.append(title_clip)
        
        # Add captions
        for cap in clip_data.get('captions', []):
            c_text = cap.get('text', '')
            c_start = max(0, cap.get('start', start) - start)
            c_end = min(subclip.duration, cap.get('end', end) - start)
            
            if c_start >= c_end:
                continue
                
            cap_clip = create_text_image_clip(c_text, (w, h), position='bottom', is_overlay=False)
            cap_clip = cap_clip.with_start(c_start).with_duration(c_end - c_start)
            overlays.append(cap_clip)
            
        final_clip = CompositeVideoClip([subclip] + overlays)
        
        out_name = f"{output_path_base}_Clip_{clip_id}.mp4"
        print(f"[*] Rendering {out_name}...")
        final_clip.write_videofile(
            out_name, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile=f"temp-audio-{clip_id}.m4a", 
            remove_temp=True,
            logger='bar'
        )
        final_clip.close()
        subclip.close()
        
    video.close()
    print("\n[*] All highlight clips rendered successfully!")

def get_or_set_api_key():
    config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AutoClipAI')
    config_path = os.path.join(config_dir, 'config.json')
    
    # 1. Check environment variable
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
        
    # 2. Check deeply saved config file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                if config.get("GEMINI_API_KEY"):
                    return config["GEMINI_API_KEY"]
        except:
            pass
            
    # 3. Prompt and save
    print("[!] The AI Agent requires a Gemini API Key to run.")
    api_key = input("Enter your Gemini API Key (it will be securely saved): ").strip()
    if api_key:
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump({"GEMINI_API_KEY": api_key}, f)
        print(f"[*] API Key saved securely to {config_path}")
        return api_key
    return None

async def main():
    print("="*50)
    print(" Auto Clip: AI Short-Form Video Generator")
    print("="*50)
    
    api_key = get_or_set_api_key()
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    else:
        print("[!] Warning: Continuing without an API key, the Agent will fail.")
            
    video_path = input("\nEnter the full path to the video file: ").strip().strip('"')
    
    if not os.path.exists(video_path):
        print("[!] Video file not found.")
        input("Press Enter to exit...")
        return
        
    audio_path = "temp_audio.wav"
    transcript_cache = video_path.rsplit('.', 1)[0] + "_transcript.txt"
    
    if os.path.exists(transcript_cache):
        print("[*] Found cached transcript! Skipping audio extraction and transcription...")
        with open(transcript_cache, 'r', encoding='utf-8') as f:
            transcript = f.read()
    else:
        extract_audio(video_path, audio_path)
        transcript = transcribe_audio(audio_path)
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        if not transcript.strip():
            print("[!] No speech detected in the video.")
            input("Press Enter to exit...")
            return
            
        with open(transcript_cache, 'w', encoding='utf-8') as f:
            f.write(transcript)
        print("[*] Transcript saved to cache.")
            
    ai_response = None
    while ai_response is None:
        try:
            ai_response = await analyze_with_agent(transcript)
        except Exception as e:
            print(f"\n[!] AI API Error: {e}")
            retry = input("The AI server might be busy (503). Press Enter to retry, or type 'n' to quit: ")
            if retry.strip().lower() == 'n':
                return
    
    print("\n--- AI Clip Plan (JSON) ---")
    print(ai_response)
    print("===========================\n")
    
    render_choice = input("Do you want to render the highlight clips now? (y/n): ").strip().lower()
    if render_choice == 'y':
        output_path_base = video_path.rsplit('.', 1)[0]
        apply_edits(video_path, output_path_base, ai_response)
    
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    input("\nPress Enter to exit...")
