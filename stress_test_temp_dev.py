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
import argparse

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
LOAD_STAGES = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
# The duration, in seconds, to run each stage of the stress test.
STAGE_DURATION_SECONDS = 10  # 15 minutes

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

            current_video_id = item.get("video_id")
            if not current_video_id:
                url_str = item.get("url")
                if url_str:
                    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url_str)
                    if match:
                        current_video_id = match.group(1)

            if not current_video_id:
                continue

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
    return librosa.resample(y=audio_array.astype(np.float32), orig_sr=current_sr, target_sr=target_sr)

def transcribe_audio_file(task_details: tuple) -> Dict:
    """
    This is the core function that sends an audio file to the Google STT API and measures performance.
    It's designed to be run in a separate thread for each concurrent call.
    """
    client, audio_file_path, language_code = task_details
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
        # Load audio file and get its duration.
        audio_array, original_sr = librosa.load(audio_file_path, sr=None, mono=True)
        audio_duration = librosa.get_duration(y=audio_array, sr=original_sr)
        if audio_array.size == 0:
            raise ValueError("Loaded audio array is empty.")

        # Resample audio if necessary.
        if original_sr != TARGET_SAMPLE_RATE:
            audio_array = resample_audio(audio_array, original_sr, TARGET_SAMPLE_RATE)

        content = (audio_array * 32767).astype(np.int16).tobytes()

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=TARGET_SAMPLE_RATE,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )
        requests = [speech.StreamingRecognizeRequest(audio_content=content)]

        api_call_start_time = time.time()
        responses = client.streaming_recognize(config=streaming_config, requests=requests)
        results['connection_successful'] = True

        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            
            if not result.is_final and results['ttfb_first_partial'] is None:
                results['ttfb_first_partial'] = time.time() - api_call_start_time
            
            if result.is_final:
                final_transcript_time = time.time()
                processing_time = final_transcript_time - api_call_start_time
                results['latency_to_final'] = processing_time
                results['rtf'] = processing_time / audio_duration if audio_duration > 0 else 0

    except Exception as e:
        results['error'] = f"{type(e).__name__}: {e}"
        # For detailed debugging, you can uncomment the next line
        # traceback.print_exc()


    results['end_time'] = time.time()
    return results

def run_load_stage(stage_concurrency: int, duration: int, tasks: List[Tuple[str, str]], client: speech.SpeechClient) -> Dict:
    """
    Manages a single stage of the load test using a ThreadPoolExecutor.
    """
    print(f"\n--- Starting Stage: {stage_concurrency} Concurrent Calls for {duration} seconds ---")
    stage_results = []
    
    # *** KEY CHANGE: Using ThreadPoolExecutor instead of ProcessPoolExecutor ***
    with concurrent.futures.ThreadPoolExecutor(max_workers=stage_concurrency) as executor:
        start_time = time.time()
        
        # We use a list of futures to manage submitted tasks
        futures = []
        
        # The test runs for the specified duration.
        task_index = 0
        while time.time() - start_time < duration:
            # Prepare a batch of tasks to submit
            # The client is now passed as part of the task details tuple
            task_with_client = (client, tasks[task_index % len(tasks)][0], tasks[task_index % len(tasks)][1])
            futures.append(executor.submit(transcribe_audio_file, task_with_client))
            task_index += 1

            # To avoid submitting an unbounded number of tasks and consuming all memory,
            # we'll wait for tasks to complete if the queue of running/pending tasks gets too large.
            # A simple approach is to manage the number of pending futures.
            if len(futures) >= stage_concurrency * 2:
                # Wait for the oldest future to complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        stage_results.append(future.result())
                    except Exception as e:
                        stage_results.append({'error': str(e)})
                    # Remove the completed future from the list
                    futures.remove(future)
                    break # Break to submit a new task

        # Collect results from any remaining futures after the duration has passed
        for future in concurrent.futures.as_completed(futures):
            try:
                stage_results.append(future.result())
            except Exception as e:
                stage_results.append({'error': str(e)})

    return analyze_stage_results(stage_results, stage_concurrency)

def analyze_stage_results(results: List[Dict], concurrency: int) -> Dict:
    """
    Analyzes the results from a load stage and calculates key performance indicators.
    """
    df = pd.DataFrame([r for r in results if r is not None and r.get('error') is None])
    
    if df.empty:
        error_count = len(results)
        error_rate = 100.0 if results else 0
        print(f"Warning: No successful requests for {concurrency} concurrent calls. Total errors: {error_count}")
        return {f"{concurrency} Calls": {
            'Total Requests Attempted': len(results),
            'Total Successful Transcripts': 0,
            'API Error Rate (%)': error_rate
        }}

    analysis = {
        'Avg. TTFB (First Partial) (ms)': df['ttfb_first_partial'].mean() * 1000,
        'Avg. Latency to Final (ms)': df['latency_to_final'].mean() * 1000,
        'Max Latency to Final (ms)': df['latency_to_final'].max() * 1000,
        'P95 Latency to Final (ms)': df['latency_to_final'].quantile(0.95) * 1000,
        'Avg. Real-Time Factor (RTF)': df['rtf'].mean(),
        'Total Successful Transcripts': len(df),
        'Total Requests Attempted': len(results),
        'API Error Rate (%)': (len(results) - len(df)) / len(results) * 100 if results else 0,
        'Connection Success Rate (%)': df['connection_successful'].mean() * 100
    }
    return {f"{concurrency} Calls": analysis}

def pipeline(concurrency_level: int, duration: int):
    """
    The main function, now accepting concurrency and duration as arguments.
    """
    print(f"--- Starting STT API Stress Test ---")
    print(f"--- Target Concurrency: {concurrency_level}, Duration: {duration} seconds ---")


    url_language_metadata = load_url_metadata(
        URL_META_JSON_PATH,
        LANGUAGE_NAME_TO_STT_CODE_MAP,
        USER_SPECIFIED_TARGET_LANGUAGE_CODES
    )
    if not url_language_metadata:
        print("Failed to load language metadata. Aborting.")
        return

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

    # *** KEY CHANGE: Create the client once before running the tests ***
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
    speech_client = speech.SpeechClient(credentials=credentials)

    all_results = {}
    for stage in LOAD_STAGES:
        stage_summary = run_load_stage(stage, STAGE_DURATION_SECONDS, tasks, speech_client)
        all_results.update(stage_summary)
        
        print("\n--- Stage Summary ---")
        print(json.dumps(stage_summary, indent=4))

    results_df = pd.DataFrame.from_dict(all_results, orient='index')
    results_df.to_csv("stress_test_results.csv")
    print("\n--- Stress Test Complete ---")
    print("Results saved to stress_test_results.csv")
    print(results_df)

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a concurrency test for Google STT API.")
    parser.add_argument('-c', '--concurrency', type=int, required=True, help='Number of concurrent calls to simulate.')
    parser.add_argument('-d', '--duration', type=int, required=True, help='Duration of the test in seconds.')
    args = parser.parse_args()

    if not os.path.exists(CREDENTIALS_PATH):
        print(f"CRITICAL ERROR: Google Cloud credentials file not found at '{CREDENTIALS_PATH}'.")
    elif not os.path.exists(URL_META_JSON_PATH):
        print(f"CRITICAL ERROR: URL metadata file not found at '{URL_META_JSON_PATH}'.")
    elif not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"CRITICAL ERROR: Base audio directory not found at '{BASE_AUDIO_DIRECTORY}'.")
    else:
        pipeline(concurrency_level=args.concurrency, duration=args.duration)