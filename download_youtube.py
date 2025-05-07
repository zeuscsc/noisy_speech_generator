import os
import subprocess
import sys
import shutil

def check_ffmpeg():
    """Checks if ffmpeg is accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("FFmpeg found.")
        return True
    except FileNotFoundError:
        print("ERROR: FFmpeg not found. FFmpeg is required by yt-dlp for merging formats.")
        print("Please install FFmpeg and ensure it's in your system's PATH.")
        print("Download from: https://ffmpeg.org/download.html")
        return False
    except subprocess.CalledProcessError:
        print("ERROR: Error while checking FFmpeg version. It might not be configured correctly.")
        return False

def download_videos_with_transcripts(urls_file="urls.txt", output_dir="dataset"):
    """
    Downloads YouTube videos and their English transcripts/subtitles
    from a list of URLs in a file using yt-dlp.

    Args:
        urls_file (str): Path to the text file containing YouTube URLs (one per line).
        output_dir (str): Path to the directory where videos and transcripts will be saved.
                          Each video/transcript set gets its own subfolder named by video ID.
    """
    if not os.path.exists('yt-dlp') and not shutil.which('yt-dlp'):
         print("ERROR: yt-dlp command not found. Please install it (pip install -U yt-dlp)")
         print("and ensure it's in your system's PATH or the script's directory.")
         sys.exit(1)

    if not check_ffmpeg():
        sys.exit(1)
    os.makedirs(output_dir, exist_ok=True)
    try:
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{urls_file}'")
        print("Please create this file and add YouTube URLs to it.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file '{urls_file}': {e}")
        sys.exit(1)

    if not urls:
        print(f"No valid URLs found in '{urls_file}'. Please add some URLs.")
        return 

    print(f"Found {len(urls)} URLs in '{urls_file}'. Starting download process...")
    print(f"Output will be saved in '{output_dir}/<video_id>/'")

    success_count = 0
    fail_count = 0
    for i, url in enumerate(urls, 1):
        print(f"\n--- Processing URL {i}/{len(urls)}: {url} ---")
        try:
            output_template = os.path.join(output_dir, '%(id)s', '%(id)s.%(ext)s')

            # Construct the yt-dlp command arguments as a list
            command = [
                'yt-dlp',
                # --- Output Options ---
                '-o', output_template,          # Set output path structure
                '--ignore-errors',              # Continue processing list even if one video fails

                # --- Format Selection ---
                # Download best video format with mp4 extension + best audio format with m4a extension,
                # merge them into an MP4 file. Fallback strategies included.
                '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
                '--merge-output-format', 'mp4', # Ensure merged output is mp4

                # --- Subtitle/Transcript Options ---
                '--write-subs',                 # Download manually uploaded subtitles
                '--write-auto-subs',            # Download automatically generated subtitles (captions)
                '--sub-langs', 'en.*',          # Target English language variants (en, en-US, en-GB etc.)
                                                # Change 'en.*' to 'all' for all languages, or specify others e.g., 'es.*,fr.*'
                # '--sub-format', 'vtt/srt',    # Optional: Specify preferred subtitle format (e.g., vtt or srt)

                # --- Other Useful Options (Optional) ---
                # '--embed-subs',               # Embed subtitles into the video file (if format supports it)
                # '--restrict-filenames',       # Ensure filenames are ASCII and compatible with all OS
                # '--verbose',                  # More detailed output from yt-dlp (for debugging)

                # --- URL ---
                url
            ]

            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.stdout:
                filtered_stdout = "\n".join(line for line in result.stdout.splitlines() if not line.strip().startswith('[download] Destination:'))
                if filtered_stdout.strip():
                     print("yt-dlp Output:\n", filtered_stdout)
            if result.returncode == 0:
                print(f"Successfully processed: {url}")
                success_count += 1
            else:
                print(f"Warning/Error processing {url} (yt-dlp exit code {result.returncode}).")
                fail_count += 1
                if result.stderr:
                    print("yt-dlp Stderr:\n", result.stderr)

        except Exception as e:
            print(f"CRITICAL ERROR: Python script failed while processing {url}: {e}")
            fail_count += 1
    print("\n--- Download Process Summary ---")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Successful downloads (or partially successful with warnings): {success_count}")
    print(f"Failed downloads or critical errors: {fail_count}")
    print(f"Check the '{output_dir}' directory for downloaded files.")
    print("Note: Subtitles/transcripts are only downloaded if they exist for the video in the specified language (English).")

def download_audio_segment(urls_file="urls.txt", output_dir="dataset_audio", duration_minutes=10):
    """
    Downloads a segment (first N minutes) of audio only from YouTube videos
    listed in a file using yt-dlp and ffmpeg.

    Args:
        urls_file (str): Path to the text file containing YouTube URLs (one per line).
        output_dir (str): Path to the directory where audio segments will be saved.
                          Each audio segment gets its own subfolder named by video ID.
        duration_minutes (int): The duration of the audio segment to download from the beginning (in minutes).
    """
    ytdlp_executable = shutil.which('yt-dlp') or ('yt-dlp' if os.path.exists('yt-dlp') else None)
    if not ytdlp_executable:
        print("ERROR: yt-dlp command not found. Please install it (pip install -U yt-dlp)")
        print("and ensure it's in your system's PATH or the script's directory.")
        sys.exit(1)
    print(f"Using yt-dlp executable: {ytdlp_executable}")

    if not check_ffmpeg():
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    try:
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except FileNotFoundError:
        print(f"ERROR: Input file not found at '{urls_file}'")
        print("Please create this file and add YouTube URLs to it.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file '{urls_file}': {e}")
        sys.exit(1)

    if not urls:
        print(f"No valid URLs found in '{urls_file}'. Please add some URLs.")
        return

    duration_seconds = duration_minutes * 60
    print(f"Found {len(urls)} URLs in '{urls_file}'. Starting audio segment (first {duration_minutes} min) download process...")
    print(f"Output will be saved in '{output_dir}/<video_id>/'")

    success_count = 0
    fail_count = 0
    for i, url in enumerate(urls, 1):
        print(f"\n--- Processing URL {i}/{len(urls)} (Audio Segment): {url} ---")
        try:
            output_template = os.path.join(output_dir, '%(id)s', f'%(id)s_{duration_minutes}min_segment.%(ext)s')

            # Use ffmpeg arguments via postprocessor args for slicing
            # -ss 0 specifies start time 0
            # -to {duration_seconds} specifies end time
            # Using ffmpeg_i applies these to the *input* file during processing
            ffmpeg_args = f'ffmpeg_i:-ss 0 -to {duration_seconds}'

            command = [
                ytdlp_executable,
                # --- Output Options ---
                '-o', output_template,          # Set output path structure
                '--ignore-errors',              # Continue processing list even if one video fails

                # --- Format Selection (Audio Only) ---
                '-f', 'bestaudio/best',         # Select best audio stream
                '-x',                           # Extract audio
                '--audio-format', 'mp3',        # Specify audio format (e.g., mp3, m4a, opus, wav)

                 # --- Segmenting/Slicing ---
                # Use postprocessor args to pass arguments to ffmpeg for slicing
                '--postprocessor-args', ffmpeg_args,

                # --- Other Useful Options (Optional) ---
                # '--restrict-filenames',       # Ensure filenames are ASCII and compatible with all OS
                # '--verbose',                  # More detailed output from yt-dlp (for debugging)

                # --- URL ---
                url
            ]

            print(f"Running command: {' '.join(command)}")
             # Use encoding compatible with terminal, often utf-8 is fine
            result = subprocess.run(command, check=False, capture_output=True, text=True, encoding='utf-8', errors='replace')

            # Filter out download progress lines for cleaner output
            if result.stdout:
                filtered_stdout = "\n".join(line for line in result.stdout.splitlines() if not line.strip().startswith('[download] Destination:'))
                # Also filter out ffmpeg messages if too verbose, or keep them for debugging
                # filtered_stdout = "\n".join(line for line in filtered_stdout.splitlines() if not line.strip().startswith('[ExtractAudio] Destination:'))
                # filtered_stdout = "\n".join(line for line in filtered_stdout.splitlines() if not line.strip().startswith('[Merger]')) # If -x implies merging temp files
                # filtered_stdout = "\n".join(line for line in filtered_stdout.splitlines() if not line.strip().startswith('[ffmpeg]')) # If postprocessor args log excessively
                if filtered_stdout.strip():
                    print("yt-dlp Output:\n", filtered_stdout)

            if result.returncode == 0:
                print(f"Successfully processed and extracted audio segment: {url}")
                success_count += 1
            else:
                # Check stderr for specific ffmpeg errors if slicing failed
                print(f"Warning/Error processing {url} (yt-dlp exit code {result.returncode}). Segmenting may have failed.")
                fail_count += 1
                if result.stderr:
                    print("yt-dlp Stderr:\n", result.stderr) # Stderr often contains ffmpeg errors

        except Exception as e:
            print(f"CRITICAL ERROR: Python script failed while processing {url}: {e}")
            fail_count += 1

    print("\n--- Audio Segment Download Process Summary ---")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Successful audio segment extractions: {success_count}")
    print(f"Failed extractions or critical errors: {fail_count}")
    print(f"Check the '{output_dir}' directory for downloaded audio segments.")

def pipeline():
    """
    Main function to run the script.
    """
    print(">>> Starting Full Video Download Process <<<")
    download_videos_with_transcripts(urls_file="urls.txt", output_dir="dataset")
    print("\n--------------------------------------------\n")
    print(">>> Starting Background Noise Audio Segment Download Process <<<")
    download_audio_segment(urls_file="background_noise.txt", output_dir="dataset_background_noise", duration_minutes=10)
if __name__ == "__main__":
    pipeline()