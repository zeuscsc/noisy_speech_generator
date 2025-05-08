# Automated Audio-Visual Data Processing Pipeline

## Overview

This project provides a comprehensive Python-based pipeline for downloading video and audio content (primarily from YouTube), transcribing audio to text, processing audio by adding background noise, chunking audio and transcripts into smaller segments, and finally sampling this data to create structured datasets. This is particularly useful for preparing data for machine learning tasks, audio analysis, or other research purposes.

The main entry point for the pipeline is `pipeline.py`, which orchestrates the execution of several specialized scripts in sequence.

## The Pipeline (`pipeline.py`)

The `pipeline.py` script executes a series of modules to process data from start to finish. The typical workflow is as follows:

1.  **Download YouTube Content (`download_youtube.py`):** Downloads YouTube videos and their transcripts, as well as audio segments for background noise.
2.  **Generate Transcripts (`generate_transcribe.py`):** Transcribes the audio from downloaded videos using OpenAI's Whisper.
3.  **Create Master Noise File (`create_master_noise.py`):** Combines multiple background noise audio files into a single master noise track.
4.  **Combine Noise with Audio (`combine_noise.py`):** Mixes the extracted video audio with the master background noise at various intensity levels.
5.  **Chunk Audio and Transcripts (`chunking_audio.py`):** Splits the processed audio files and their corresponding transcripts into smaller, manageable chunks.
6.  **Sample Data (`sampaling_data.py`):** Samples the chunked audio and transcript data, categorizing it based on metadata (language, accent) to create a diverse and representative final dataset.

The `pipeline.py` script is structured as follows:

```python
import download_youtube
import generate_transcribe
import create_master_noise
import combine_noise
import chunking_audio
import sampaling_data

if __name__ == "__main__":
    download_youtube.pipeline()
    generate_transcribe.pipeline()
    create_master_noise.pipeline()
    combine_noise.pipeline()
    chunking_audio.pipeline()
    sampaling_data.pipeline()
    print("Pipeline completed successfully.")
```

## Consolidated Prerequisites

To run this entire pipeline, you will need the following software and Python libraries installed:

**Software:**

1.  **Python 3.x:**
    * Download and install from [python.org](https://www.python.org/downloads/).
2.  **FFmpeg:** A complete, cross-platform solution to record, convert and stream audio and video.
    * Required by `yt-dlp`, `pydub`, and several scripts in this pipeline for audio/video processing.
    * Download from: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
    * Ensure `ffmpeg` is installed and added to your system's PATH.
    * **On macOS (using Homebrew):** `brew install ffmpeg`
    * **On Debian/Ubuntu Linux:** `sudo apt-get update && sudo apt-get install ffmpeg` (or `libav-tools`)
    * **On Windows:** Download FFmpeg, extract it, and add the `bin` directory to your system's PATH.
3.  **yt-dlp:** A command-line program to download videos from YouTube and other sites.
    * Required by `download_youtube.py`.
    * Installation: `pip install -U yt-dlp` or download from [yt-dlp GitHub releases](https://github.com/yt-dlp/yt-dlp/releases/latest). Ensure executable is in PATH.
4.  **OpenAI Whisper CLI:** For audio transcription.
    * Required by `generate_transcribe.py`.
    * Installation: `pip install -U openai-whisper`
    * **For GPU Acceleration (Recommended for Whisper):** Install PyTorch with CUDA support. Follow instructions at [pytorch.org/get-started/locally/](https://pytorch.org/get-started/locally/).

**Python Libraries:**

Install these using pip:

```bash
pip install -U yt-dlp openai-whisper pydub ffmpeg-python
```

* `yt-dlp`: For downloading YouTube content (also listed under software).
* `openai-whisper`: For audio transcription (also listed under software).
* `pydub`: For audio manipulation (used in `create_master_noise.py` and `chunking_audio.py`).
* `ffmpeg-python`: A Python wrapper for FFmpeg (used in `combine_noise.py`).

## Consolidated Setup

1.  **Clone or download the repository:** Obtain all the Python scripts (`pipeline.py`, `download_youtube.py`, etc.) and place them in your project directory.
2.  **Install Software:** Ensure Python 3.x, FFmpeg, yt-dlp (executable), and OpenAI Whisper CLI are installed and correctly configured in your system's PATH as described in the "Prerequisites" section.
3.  **Install Python Libraries:**
    ```bash
    pip install -U yt-dlp openai-whisper pydub ffmpeg-python
    ```
4.  **Prepare Initial Input Files and Directories:**
    * **For `download_youtube.py`:**
        * Create `urls.meta.json` for video and transcript downloads. (See `download_youtube.py` section for format).
        * Create `background_noise.txt` for audio segment downloads. (See `download_youtube.py` section for format).
    * **For `generate_transcribe.py`:**
        * By default, it looks for a `dataset/` directory structured with video subdirectories (e.g., `dataset/video_001/video.mp4`). This `dataset/` directory is typically populated by `download_youtube.py`.
    * **For `create_master_noise.py`:**
        * Ensure the input folder for background noise MP3s (e.g., `dataset_background_noise/`, often populated by the audio segment download part of `download_youtube.py`) is correctly specified within the script.
    * **For `combine_noise.py`:**
        * Ensure the `dataset/` directory (with video subfolders from `download_youtube.py`) exists.
        * Ensure the master noise file (e.g., `final_mixed_audio_limited.mp3`, created by `create_master_noise.py`) is available and its path is correctly specified in the script.
    * **For `chunking_audio.py`:**
        * Input directories for noisy audio (e.g., `output_noisy_audio/`, created by `combine_noise.py`) and original transcripts (e.g., `dataset/`, populated by `download_youtube.py` and `generate_transcribe.py`) need to be present.
    * **For `sampaling_data.py`:**
        * The `chunked_dataset/` directory (created by `chunking_audio.py`) should be available.
        * The `urls.meta.json` file (used by `download_youtube.py`) is also used here for language/accent metadata.

## Usage

To run the entire data processing pipeline, navigate to the project's root directory in your terminal and execute:

```bash
python pipeline.py
```

The script will then run each module in sequence, printing progress and status messages to the console. Ensure all prerequisite software, libraries, and necessary input files/directories are correctly set up before running the pipeline.

## Pipeline Modules

Below are details for each Python script involved in the pipeline.

---

### 1. `download_youtube.py`: YouTube Video and Audio Downloader

This Python script provides functionalities to download YouTube videos along with their English transcripts/subtitles, and to download specific duration audio segments from a list of YouTube URLs. It utilizes the `yt-dlp` command-line tool for downloading and `ffmpeg` for media processing.

**Features:**

* **Video and Transcript Download:**
    * Downloads full YouTube videos in MP4 format.
    * Attempts to download both official and automatically generated English subtitles/transcripts.
    * Organizes downloaded videos and their corresponding transcripts into separate subdirectories named by the video ID.
    * Reads video URLs from a JSON file (`urls.meta.json`).
* **Audio Segment Download:**
    * Downloads a specified duration (default: first 10 minutes) of audio-only from YouTube videos.
    * Saves audio segments in MP3 format.
    * Organizes downloaded audio segments into separate subdirectories named by the video ID.
    * Reads video URLs from a plain text file (`background_noise.txt`).
* **Dependency Checks:**
    * Verifies the presence and accessibility of `yt-dlp` and `ffmpeg`.
* **Error Handling:**
    * Provides feedback on missing dependencies, input file errors, and download issues.
    * Summarizes the number of successful and failed downloads.

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3
* yt-dlp
* FFmpeg

**Setup (Covered in Consolidated Setup):**

1.  Ensure dependencies are installed and in PATH.
2.  **Prepare input files:**
    * **For Video and Transcript Downloads:**
        Create a JSON file named `urls.meta.json` in the same directory as the script.
        Example `urls.meta.json`:
        ```json
        [
            {
                "url": "https://www.youtube.com/watch?v=CU5R9c3Wc60",
                "language": "English",
                "accent": "Indian",
                "tags": ["General", "Data Science"]
            },
            {
                "url": "https://www.youtube.com/watch?v=VN4E6Mp_ljs",
                "language": "English",
                "accent": "Indian",
                "tags": ["General", "Algorithm"]
            }
        // ... more entries
        ]
        ```
    * **For Audio Segment Downloads:**
        Create a text file named `background_noise.txt` in the same directory as the script.
        Example `background_noise.txt`:
        ```
        # Category: Nature Sounds
        https_://[www.youtube.com/watch?v=NATURE_VIDEO_ID_1](https://www.youtube.com/watch?v=NATURE_VIDEO_ID_1)
        https_://[www.youtube.com/watch?v=NATURE_VIDEO_ID_2](https://www.youtube.com/watch?v=NATURE_VIDEO_ID_2)

        # Category: City Ambience
        https_://[www.youtube.com/watch?v=CITY_VIDEO_ID_1](https://www.youtube.com/watch?v=CITY_VIDEO_ID_1)
        ```

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone (after setup):

```bash
python download_youtube.py
```

---

### 2. `generate_transcribe.py`: Video to Transcript Pipeline

This script automates the process of transcribing audio from video files within a structured dataset directory using OpenAI's Whisper. It extracts audio from video files, transcribes it, and saves the transcriptions in the specified format (default VTT).

**Features:**

* **Automatic Video Detection**: Scans subdirectories within a main `dataset` directory.
* **Audio Extraction**: Uses FFmpeg to extract audio to a temporary MP3 file.
* **Transcription via Whisper**: Leverages the OpenAI Whisper CLI.
    * Supports configurable Whisper models.
    * Supports automatic language detection.
* **GPU Acceleration**: Whisper CLI will attempt to use a CUDA-enabled GPU if available.
* **Skip Existing Transcripts**: Avoids reprocessing.
* **Organized Output**: Saves transcripts in the video's directory.
* **Error Handling**: Checks for FFmpeg and Whisper.
* **Process Summary**: Outputs a summary of operations.

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3.x
* FFmpeg
* OpenAI Whisper CLI
* (Optional for GPU) PyTorch with CUDA support.

**Setup (Covered in Consolidated Setup):**

1.  Ensure prerequisites are installed.
2.  **Dataset Directory**: By default, expects a `dataset/` directory. Videos (e.g., from `download_youtube.py`) should be in subdirectories like `dataset/video_id/video.mp4`.
3.  **Configure Script Variables (Optional)**: Modify global variables in `generate_transcribe.py` for `DATASET_DIR`, `WHISPER_MODEL`, `TARGET_LANG`, `OUTPUT_FORMAT`.

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone:

```bash
python generate_transcribe.py
```

**Output:**

* Transcript files (e.g., `dataset/video_001/video_001.whisper.auto.vtt`).
* Console logs detailing progress and a summary.

---

### 3. `create_master_noise.py`: MP3 Audio Overlay Script

This Python script searches for MP3 audio files (typically background noises downloaded by `download_youtube.py`) within a specified folder, overlays them into a single audio track, and saves the result as a new MP3 file (the "master noise" file). It can load initial segments of each file to manage memory.

**Features:**

* Recursively finds `.mp3` files.
* Loads multiple audio tracks, optionally only initial N seconds.
* Trims all tracks to the shortest effective loaded segment.
* Overlays trimmed tracks into a single audio stream.
* Exports the combined audio to an MP3 file.

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3.x
* Pydub
* FFmpeg or Libav (for Pydub)

**Setup (Covered in Consolidated Setup):**

1.  Ensure prerequisites are installed.
2.  **Prepare audio files:** Place source MP3 noise files in a folder.
3.  **Configure the script:** Modify variables in the `pipeline()` function within `create_master_noise.py`:
    * `dataset_folder`: Path to your folder containing MP3s (e.g., `dataset_background_noise`).
    * `output_file`: Desired output filename for the master noise (e.g., `final_mixed_audio_limited.mp3`).
    * `initial_load_duration`: Seconds to load from each track (e.g., `30 * 60` for 30 mins, or `None` for full tracks).

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone:

```bash
python create_master_noise.py
```

---

### 4. `combine_noise.py`: Video Audio Noiser

This Python script processes video files by extracting their audio, mixing it with a specified background noise file (created by `create_master_noise.py`) at various intensity levels, and saving the resulting audio tracks as MP3 files. It uses `ffmpeg` and `multiprocessing`.

**Features:**

* **Automated Audio Extraction.**
* **Noise Mixing** with a master noise file.
* **Variable Noise Levels** (configurable percentages).
* **Parallel Processing** for efficiency.
* **Efficient Looping** of noise audio to match video audio duration.
* **Structured Output** for noisy audio files.
* **Skip Existing** processed files.

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3.x
* FFmpeg
* `ffmpeg-python` library.

**Setup (Covered in Consolidated Setup):**

1.  Ensure prerequisites are installed.
2.  **Prepare Data:**
    * **Video Files:** In a root `dataset` directory, with subdirectories per video (e.g., from `download_youtube.py`).
    * **Noise File:** The master noise file (e.g., `final_mixed_audio_limited.mp3`) should be available.
3.  **Configuration (in `combine_noise.py`'s `pipeline()` function):**
    * `video_dataset_root`: Root for video files (e.g., `"dataset"`).
    * `single_master_noise_file`: Path to the master noise audio.
    * `output_audio_dir_base`: Root for output noisy audio (e.g., `"output_noisy_audio"`).
    * `noise_levels_percentage`: List of noise levels (e.g., `[0, 25, 50, 75, 100, 150, 200]`).

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone:

```bash
python combine_noise.py
```

**Output:**

Creates an output directory (e.g., `output_noisy_audio/`) with subfolders for each video ID, containing noisy audio MP3s named like `noisy_{level}.mp3`.

---

### 5. `chunking_audio.py`: Audio and Transcript Chunker

This Python script processes audio files (MP3, typically the noisy audio from `combine_noise.py`) and their corresponding VTT transcript files to create a chunked dataset. It splits audio into smaller segments and generates corresponding VTT transcript chunks.

**Features:**

* **VTT Parsing** and timestamp conversion.
* **Audio Chunking** (e.g., 8, 30, 60 seconds) using `pydub`.
* **Transcript Chunking** to match audio segments.
* **Parallel Processing.**
* **Organized Output** for chunked audio and transcripts.

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3.x
* pydub
* FFmpeg or LibAV (for pydub).

**Setup (Covered in Consolidated Setup):**

1.  Ensure prerequisites are installed.
2.  **Prepare Input Data:**
    * **Input Audio Directory** (e.g., `./output_noisy_audio/` from `combine_noise.py`).
    * **Input Transcript Directory** (e.g., `./dataset/` with original VTTs from `download_youtube.py` and `generate_transcribe.py`).
    The script expects specific sub-folder structures as detailed in its original README.
3.  **Configure Paths (Optional):** Modify paths in `chunking_audio.py` if defaults are not suitable:
    * `input_audio_directory`
    * `input_transcript_directory`
    * `output_chunked_directory` (e.g., `./chunked_dataset`)
    * `chunk_sizes_seconds`

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone:

```bash
python chunking_audio.py
```

**Output:**

Creates a structured `output_chunked_directory` (e.g., `./chunked_dataset/`) containing subfolders for each video ID, then by chunk size, then by noise level, holding the audio chunks (`audio_N.mp3`) and their corresponding transcript chunks (`original_vtt_basename_audio_N.vtt`).

---

### 6. `sampaling_data.py`: Audio Dataset Sampler and Organizer

This script processes a directory of chunked audio files (from `chunking_audio.py`), categorizes them based on language and accent metadata (from `urls.meta.json`), and creates a new, smaller, sampled dataset.

**Features:**

* **Loads Metadata** from JSON (`urls.meta.json`) for language/accent.
* **Scans Source Dataset** (e.g., `chunked_dataset`).
* **Categorizes Audio** by language, accent, and chunk type.
* **Samples Audio Files** aiming for diversity (different noise levels) and minimum sample counts.
* **Copies Selected Files** (audio and VTT transcripts) to a new structured output directory (e.g., `sampled_dataset`).

**Prerequisites (Covered in Consolidated Prerequisites):**

* Python 3.x (standard libraries are used).

**Setup (Covered in Consolidated Setup):**

1.  Ensure Python is installed.
2.  **Prepare Data:**
    * `chunked_dataset/` directory (output from `chunking_audio.py`) should be available.
    * `urls.meta.json` file (used by `download_youtube.py`) must be present with language/accent metadata.
3.  **Configuration (in `sampaling_data.py`'s `pipeline()` function):**
    * `chunked_dataset_path` (default: `"chunked_dataset"`).
    * `new_dataset_path` (default: `"sampled_dataset"`).
    * `metadata_json_file` (default: `"urls.meta.json"`).
    * `min_samples_to_select` (default: `5`).

**`urls.meta.json` Format (relevant fields for this script):**

```json
[
    {
        "url": "https://www.youtube.com/watch?v=CU5R9c3Wc60",
        "language": "English",
        "accent": "Indian",
        "tags": ["General", "Data Science"]
    },
    {
        "url": "https://www.youtube.com/watch?v=VN4E6Mp_ljs",
        "language": "English",
        "accent": "Indian",
        "tags": ["General", "Algorithm"]
    }
  // ... more entries
]
```

**Usage:**

This script is typically called by `pipeline.py`. To run it standalone:

```bash
python sampaling_data.py
```

**Output:**

Creates a `new_dataset_path` (e.g., `sampled_dataset/`) organized by `[LANGUAGE]/[ACCENT]/[CHUNK_TYPE_ID]/`, containing the sampled audio and transcript files, renamed for traceability.

---

## Contributing

Contributions are welcome! If you have suggestions for improvements or find any bugs, please feel free to open an issue or submit a pull request on the repository.

## License

This project is open-source. You may consider adding a specific license file (e.g., MIT, Apache 2.0) to define how others can use, modify, and distribute the code.
