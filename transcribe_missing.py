import os
import subprocess
import glob
import sys
import shutil 

DATASET_DIR = "dataset"
WHISPER_MODEL = "base" 
TARGET_LANG = None 
OUTPUT_FORMAT = "vtt"
AUTO_DETECT_SUFFIX = "auto"


def check_command(command_name):
    """Checks if a command exists and is executable using shutil.which."""
    if not shutil.which(command_name):
        print(f"❌ ERROR: '{command_name}' command not found or not executable.")
        if command_name == 'ffmpeg':
            print("       Please install FFmpeg and ensure it's in your system's PATH.")
            print("       Download from: https://ffmpeg.org/download.html")
        elif command_name == 'whisper':
            print("       Please install OpenAI Whisper CLI:")
            print("       pip install -U openai-whisper")
            print("       (Ensure the Python environment where you installed it is active).")
            print("       For GPU acceleration, ensure you have a compatible PyTorch with CUDA support installed.")
            print("       See: https://pytorch.org/get-started/locally/")
        return False
    print(f"✔️ '{command_name}' command found.")
    return True

def find_video_file(directory):
    """Finds the first common video file type in a directory."""
    for ext in ["*.mp4", "*.mkv", "*.webm", "*.avi", "*.mov", "*.flv"]:
        videos = glob.glob(os.path.join(directory, ext))
        if videos:
            return videos[0]
    return None

def transcript_exists(directory, video_id, output_format):
    """Checks if a transcript file already exists (yt-dlp or whisper generated)."""
    generic_patterns = [
        os.path.join(directory, f"{video_id}*.vtt"),
        os.path.join(directory, f"{video_id}*.srt"),
    ]
    for pattern in generic_patterns:
        found_files = glob.glob(pattern)
        temp_audio_base = f"_{video_id}_temp_audio"
        non_temp_found = [f for f in found_files if not os.path.basename(f).startswith(temp_audio_base)]
        if non_temp_found:
            print(f"  Found existing transcript matching pattern: {pattern} -> {os.path.basename(non_temp_found[0])}")
            return True
    whisper_pattern = os.path.join(directory, f"{video_id}.whisper.{AUTO_DETECT_SUFFIX}.{output_format}")
    if glob.glob(whisper_pattern):
        print(f"  Found existing Whisper transcript: {os.path.basename(whisper_pattern)}")
        return True

    return False

def run_subprocess(command, description="command"):
    """Runs a subprocess command, captures output, and handles errors."""
    print(f"  Running {description}: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"  ✔️ {description} successful.")
        if result.stdout and result.stdout.strip():
             print(f"    Output:\n{result.stdout.strip()}")
        if result.stderr and result.stderr.strip():
             print(f"    Info/Warnings (incl. GPU detection/progress):\n{result.stderr.strip()}")
        return True
    except FileNotFoundError:
         print(f"  ❌ ERROR: Command not found: '{command[0]}'. Ensure it's installed and in PATH.")
         return False
    except subprocess.CalledProcessError as e:
        print(f"  ❌ ERROR during {description}:")
        print(f"    Command: {' '.join(e.cmd)}")
        print(f"    Return Code: {e.returncode}")
        if e.stdout and e.stdout.strip(): print(f"    Stdout: {e.stdout.strip()}")
        if e.stderr and e.stderr.strip(): print(f"    Stderr: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"  ❌ An unexpected Python error occurred during {description}: {e}")
        return False

if __name__ == "__main__":
    print("--- Starting Transcription Process for Missing Files (GPU Enabled, Language Auto-Detect) ---")
    print(f"Dataset directory: '{DATASET_DIR}'")
    print(f"Using Whisper model: '{WHISPER_MODEL}' (Multilingual recommended for auto-detect)")
    if TARGET_LANG:
         print(f"Target language: '{TARGET_LANG}'")
    else:
         print("Target language: Auto-Detect")
    print(f"Output format: '{OUTPUT_FORMAT}'")
    print("-" * 60)
    print("INFO: Ensure you have installed PyTorch with CUDA support for GPU acceleration.")
    print("      Whisper CLI will automatically attempt to use GPU if available.")
    print("-" * 60)
    if not os.path.isdir(DATASET_DIR):
        print(f"❌ ERROR: Dataset directory '{DATASET_DIR}' not found.")
        print("       Please run the first script (download_youtube.py) to create it.")
        sys.exit(1)

    print("Checking for required tools...")
    ffmpeg_ok = check_command("ffmpeg")
    whisper_ok = check_command("whisper")
    if not (ffmpeg_ok and whisper_ok):
        print("\n❌ ERROR: One or more required tools (ffmpeg, whisper) were not found.")
        print("       Please install them and ensure they are in your system's PATH.")
        sys.exit(1)
    print("-" * 60)

    processed_dirs = 0
    videos_found = 0
    transcripts_needed = 0
    transcribed_successfully = 0
    skipped_existing = 0
    errors = 0
    for item_name in os.listdir(DATASET_DIR):
        item_path = os.path.join(DATASET_DIR, item_name)

        if os.path.isdir(item_path):
            processed_dirs += 1
            video_id = item_name
            print(f"\n[{processed_dirs}] Processing directory: {item_path}")

            video_file_path = find_video_file(item_path)
            if not video_file_path:
                print(f"  ⚠️ Warning: No video file found in {item_path}. Skipping.")
                errors += 1
                continue
            videos_found += 1
            print(f"  Found video file: {os.path.basename(video_file_path)}")

            if transcript_exists(item_path, video_id, OUTPUT_FORMAT):
                skipped_existing += 1
                continue

            print(f"  Transcript needed for '{video_id}'. Initiating process...")
            transcripts_needed += 1
            temp_audio_path = None

            try:
                temp_audio_filename = f"_{video_id}_temp_audio.mp3"
                temp_audio_path = os.path.join(item_path, temp_audio_filename)
                ffmpeg_command = [
                    'ffmpeg', '-i', video_file_path,
                    '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
                    '-ar', '16000', '-ac', '1', '-y',
                    temp_audio_path
                ]
                if not run_subprocess(ffmpeg_command, "Audio Extraction"):
                    errors += 1
                    continue

                whisper_command = [
                    'whisper',
                    temp_audio_path,
                    '--model', WHISPER_MODEL,
                    '--output_format', OUTPUT_FORMAT,
                    '--output_dir', item_path,
                    '--verbose', 'True' 
                ]

                if not run_subprocess(whisper_command, "Transcription"):
                    errors += 1
                    continue

                expected_whisper_output_base = os.path.splitext(temp_audio_filename)[0]
                expected_whisper_output_path = os.path.join(item_path, f"{expected_whisper_output_base}.{OUTPUT_FORMAT}")
                final_transcript_name = f"{video_id}.whisper.{AUTO_DETECT_SUFFIX}.{OUTPUT_FORMAT}"
                final_transcript_path = os.path.join(item_path, final_transcript_name)

                if os.path.exists(expected_whisper_output_path):
                    try:
                        os.rename(expected_whisper_output_path, final_transcript_path)
                        print(f"  ✔️ Renamed transcript to: {final_transcript_name}")
                        transcribed_successfully += 1
                    except OSError as e:
                        print(f"  ❌ ERROR: Failed to rename transcript '{expected_whisper_output_path}' to '{final_transcript_path}': {e}")
                        errors += 1
                else:
                     print(f"  ❌ ERROR: Expected Whisper output file not found: {expected_whisper_output_path}")
                     print(f"        Check the contents of '{item_path}' for alternatively named .{OUTPUT_FORMAT} files.")
                     errors += 1

            except Exception as e:
                print(f"  ❌ An critical Python error occurred processing {video_id}: {e}")
                errors += 1
            finally:
                if temp_audio_path and os.path.exists(temp_audio_path):
                    try:
                        os.remove(temp_audio_path)
                        print(f"  Removed temporary audio file: {os.path.basename(temp_audio_path)}")
                    except OSError as e:
                        print(f"  ⚠️ Warning: Could not remove temporary audio file {temp_audio_path}: {e}")
    print("\n" + "=" * 60)
    print("--- Transcription Process Summary ---")
    print(f"Total directories scanned: {processed_dirs}")
    print(f"Videos found and processed: {videos_found}")
    print(f"Transcripts needed (missing): {transcripts_needed}")
    print(f"Transcripts generated successfully: {transcribed_successfully}")
    print(f"Skipped (transcript already existed): {skipped_existing}")
    print(f"Errors encountered: {errors}")
    print("=" * 60)
    print("--- Finished ---")