# AI Auto clipper (Vibe coded)

AI Auto Clipper is an experimental, fully automated, short-form video generator powered by local transcription models (`openai-whisper`) and the Gemini AI (via `google-antigravity`).

Drop in a 5-minute video, and the AI will analyze the speech, identify the most engaging highlights, slice them into 15-45 second short-form clips, and automatically apply dynamic colored overlays and subtitles.

## 🚀 How to Run

1. Clone or download this repository.
2. Ensure you have Python installed.
3. Install the required dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Double-click the **`run_autoclip.bat`** file to launch the editor.
5. The very first time you run it, you will be asked to paste your **Gemini API Key** (obtainable from Google AI Studio). 
   - *Security Note: Your API Key is NOT saved in the project folder. It is securely generated and cached deep in your computer's `AppData` folder (`%APPDATA%/AutoClipAI/config.json`), keeping your key safe from accidental GitHub commits.*
6. Drag and drop a `.mp4` video file into the console, and let the AI process it!

## ⚙️ Technicalities & Architecture

- **Audio Extraction**: Bypasses `moviepy` limitations by aggressively interfacing with the underlying `ffmpeg` binaries to reliably strip audio from the video.
- **Local Transcription**: Uses OpenAI's `whisper` to transcribe the audio locally on your CPU/GPU, ensuring perfect timestamps. 
- **AI Highlight Pipeline**: Feeds the raw transcript into the Antigravity Python SDK (`Agent`), heavily prompted to extract highlight segments, assign them a "Vibe" color (red, gold, blue, green), and map precise subtitle timings.
- **Dependency Bypass**: Generating captions via `TextClip` on Windows usually strictly requires downloading and pathing ImageMagick. This app natively bypasses ImageMagick by dynamically creating customized RGBA numpy masks using the native Python `Pillow` library, converting them to `ImageClip` masks on the fly.
- **Caching Mechanisms**: Safely caches the transcription (`_transcript.txt`) directly next to the video. If the Gemini API hits a 503 Overload (or you need to retry), it skips the lengthy 2-minute Whisper transcription entirely.

## ⚠️ Current Limitations & Known Issues

Because this is a vibe-coded, highly experimental tool, there are a few limitations to be aware of:

- **Missing/Dropped Clips**: Occasionally, the AI's JSON output might provide invalid timestamp intervals (e.g. `start` is greater than `end` or the segment goes out of bounds of the actual video length). The script is designed to safely skip these invalid clips rather than crashing, which means you might ask for 4 clips but only get 3 successfully rendered.
- **Not Enough Graphic Design**: Currently, the AI's "creative overlay" simply generates a giant, colored Title Card at the top of the video for the first 3 seconds, and standard subtitles at the bottom. It lacks advanced graphic designs, transitions, emojis, or kinetic typography commonly found in TikTok/Reels.
- **Server Spikes (503)**: The Google API sometimes experiences heavy spikes. The script handles this gracefully by pausing and asking you to press Enter to retry, but it can be a slight annoyance.
