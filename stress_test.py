import os
import re
import traceback
import numpy as np
import librosa
from google.cloud import speech
import concurrent.futures
from tqdm import tqdm
from google.oauth2 import service_account
import json
import time
from typing import Tuple, Optional, List, Dict
import pandas as pd
import asyncio

# --- Configuration ---
# Path to your Google Cloud service account key file
CREDENTIALS_PATH = "C:/Users/User/stt-benchmark-key.json"
# Directory containing the audio files for testing
BASE_AUDIO_DIRECTORY = "testset"
# The sample rate that the Google STT API expects
TARGET_SAMPLE_RATE = 16000
# The name of the JSON file containing metadata about the audio files
URL_META_JSON_PATH = "urls.meta.json"
# The BCP-47 language codes for the languages you want to test
USER_SPECIFIED_TARGET_LANGUAGE_CODES = ["yue-Hant-HK", "en-US", "cmn-Hans-CN"]

# This dictionary maps the language names used in your metadata to the
# official BCP-47 language codes required by the Google STT API.
LANGUAGE_NAME_TO_STT_CODE_MAP = {
    "Cantonese": "yue-Hant-HK",
    "English": "en-US",
    "Mandarin": "cmn-Hans-CN"
}

# --- Stress Test Stages ---
# Defines the number of concurrent calls for each stage of the stress test.
# The test will start with 2 concurrent calls and progressively increase to 1024.
LOAD_STAGES = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
# The duration, in seconds, to run each stage of the stress test.
# This should be long enough to get a stable measure of performance.
STAGE_DURATION_SECONDS = 900  # 15 minutes

def load_url_metadata(json_file_path: str, name_to_code_map: dict, target_codes_list: list) -> dict:
    """
    This function loads language metadata from a JSON file.
    """
    video_id_to_lang_code = {}
    if not os.path.exists(json_file_path):
        print(f"Error: Metadata JSON file not found at {json_file_path}")
        return video_id_to_lang_code

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)

        for item in metadata_list:
            language_name = item.get("language")
            if not language_name:
                continue

            # This logic extracts the video ID from the URL if it's not explicitly provided.
            # It is designed to handle various YouTube URL formats.
            current_video_id = item.get("video_id")
            if not current_video_id:
                url_str = item.get("url")
                if url_str:
                    # This regular expression is a robust way to find YouTube video IDs in URLs.
                    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url_str)
                    if match:
                        current_video_id = match.group(1)

            if not current_video_id:
                continue

            # It maps the human-readable language name to the BCP-47 code.
            stt_language_code = name_to_code_map.get(language_name)
            if not stt_language_code or stt_language_code not in target_codes_list:
                continue

            video_id_to_lang_code[current_video_id] = stt_language_code

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}.")
    except Exception as e:
        print(f"An unexpected error occurred while loading URL metadata: {e}")

    return video_id_to_lang_code

def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """
    This function resamples the audio to the target sample rate required by the API.
    """
    if current_sr == target_sr:
        return audio_array
    # Librosa is a powerful library for audio analysis and manipulation.
    return librosa.resample(y=audio_array.astype(np.float32), orig_sr=current_sr, target_sr=target_sr)

def transcribe_audio_file(task_details: tuple) -> Dict:
    """
    This is the core function that sends an audio file to the Google STT API and measures performance.
    It's designed to be run in a separate process for each concurrent call.
    """
    audio_file_path, language_code = task_details
    results = {
        'start_time': time.time(),
        'end_time': None,
        'ttfb_first_partial': None,
        'latency_to_final': None,
        'rtf': None,
        'error': None,
        'connection_successful': False
    }

    try:
        # Here, we load the audio file and get its duration.
        audio_array, original_sr = librosa.load(audio_file_path, sr=None, mono=True)
        audio_duration = librosa.get_duration(y=audio_array, sr=original_sr)
        if audio_array.size == 0:
            raise ValueError("Loaded audio array is empty.")

        # Resample the audio if it's not at the target sample rate.
        if original_sr != TARGET_SAMPLE_RATE:
            audio_array = resample_audio(audio_array, original_sr, TARGET_SAMPLE_RATE)

        # The audio is converted to the format required by the API (16-bit PCM).
        content = (audio_array * 32767).astype(np.int16).tobytes()

        # These are the configuration settings for the STT API call.
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=TARGET_SAMPLE_RATE,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )

        # A streaming request is used to get partial results and measure TTFB.
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )

        # The audio content is prepared as a streaming request.
        requests = [speech.StreamingRecognizeRequest(audio_content=content)]
        client = speech.SpeechClient(credentials=service_account.Credentials.from_service_account_file(CREDENTIALS_PATH))

        # This is where the API call happens.
        api_call_start_time = time.time()
        responses = client.streaming_recognize(config=streaming_config, requests=requests)
        results['connection_successful'] = True

        # Process the streaming response to capture metrics.
        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if not result.alternatives:
                continue
            
            # The TTFB for the first partial result is recorded here.
            if result.is_final is False and results['ttfb_first_partial'] is None:
                results['ttfb_first_partial'] = time.time() - api_call_start_time
            
            # When the final transcript is received, latency and RTF are calculated.
            if result.is_final:
                final_transcript_time = time.time()
                processing_time = final_transcript_time - api_call_start_time
                results['latency_to_final'] = processing_time
                results['rtf'] = processing_time / audio_duration if audio_duration > 0 else 0

    except Exception as e:
        results['error'] = str(e)

    results['end_time'] = time.time()
    return results

def run_load_stage(stage_concurrency: int, duration: int, tasks: List[Tuple[str, str]]) -> Dict:
    """
    This function manages a single stage of the load test.
    """
    print(f"\n--- Starting Stage: {stage_concurrency} Concurrent Calls for {duration} seconds ---")
    stage_results = []
    
    # A process pool is used to simulate concurrent users.
    with concurrent.futures.ProcessPoolExecutor(max_workers=stage_concurrency) as executor:
        start_time = time.time()
        # The test runs for the specified duration.
        while time.time() - start_time < duration:
            # A batch of tasks is submitted to the executor.
            futures = [executor.submit(transcribe_audio_file, tasks[i % len(tasks)]) for i in range(stage_concurrency)]
            
            # As each task completes, its results are collected.
            for future in concurrent.futures.as_completed(futures):
                try:
                    stage_results.append(future.result())
                except Exception as e:
                    stage_results.append({'error': str(e)})

    return analyze_stage_results(stage_results, stage_concurrency)

def analyze_stage_results(results: List[Dict], concurrency: int) -> Dict:
    """
    This function analyzes the results from a load stage and calculates the KPIs.
    """
    df = pd.DataFrame([r for r in results if r is not None and r.get('error') is None])
    
    # If there are no successful results, return an empty dictionary.
    if df.empty:
        return {f"{concurrency} Calls": {}}

    # The analysis calculates average, max, and 95th percentile for latency.
    analysis = {
        'Avg. TTFB (First Partial)': df['ttfb_first_partial'].mean() * 1000,
        'Avg. Latency to Final': df['latency_to_final'].mean() * 1000,
        'Max Latency to Final': df['latency_to_final'].max() * 1000,
        'P95 Latency to Final': df['latency_to_final'].quantile(0.95) * 1000,
        'Avg. Real-Time Factor (RTF)': df['rtf'].mean(),
        'Total Transcripts Processed': len(df),
        'API Error Rate': (len(results) - len(df)) / len(results) * 100 if results else 0,
        'Connection Success Rate': df['connection_successful'].mean() * 100
    }
    return {f"{concurrency} Calls": analysis}

def pipeline():
    """
    This is the main function that orchestrates the entire stress test.
    """
    print("--- Starting STT API Stress Test ---")

    # Load the metadata and prepare the list of transcription tasks.
    url_language_metadata = load_url_metadata(
        URL_META_JSON_PATH,
        LANGUAGE_NAME_TO_STT_CODE_MAP,
        USER_SPECIFIED_TARGET_LANGUAGE_CODES
    )
    if not url_language_metadata:
        print("Failed to load language metadata. Aborting.")
        return

    # This creates a list of all audio files to be used in the test.
    tasks = []
    for root, _, files in os.walk(BASE_AUDIO_DIRECTORY):
        for filename in files:
            if any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac']):
                video_id_match = re.search(r'([a-zA-Z0-9_-]{11})', filename)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    if video_id in url_language_metadata:
                        tasks.append((os.path.join(root, filename), url_language_metadata[video_id]))

    if not tasks:
        print("No audio files matched with metadata. Aborting.")
        return

    # The test proceeds through each defined load stage.
    all_results = {}
    for stage in LOAD_STAGES:
        stage_summary = run_load_stage(stage, STAGE_DURATION_SECONDS, tasks)
        all_results.update(stage_summary)
        
        # The results are printed to the console after each stage.
        print("\n--- Stage Summary ---")
        print(json.dumps(stage_summary, indent=4))

    # Finally, a comprehensive report is generated and saved as a CSV file.
    results_df = pd.DataFrame.from_dict(all_results, orient='index')
    results_df.to_csv("stress_test_results.csv")
    print("\n--- Stress Test Complete ---")
    print("Results saved to stress_test_results.csv")
    print(results_df)

if __name__ == "__main__":
    # Before running, the script checks if all necessary files and directories are in place.
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"CRITICAL ERROR: Google Cloud credentials file not found at '{CREDENTIALS_PATH}'.")
    elif not os.path.exists(URL_META_JSON_PATH):
        print(f"CRITICAL ERROR: URL metadata file not found at '{URL_META_JSON_PATH}'.")
    elif not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"CRITICAL ERROR: Base audio directory not found at '{BASE_AUDIO_DIRECTORY}'.")
    else:
        pipeline()
