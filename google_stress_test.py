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
from typing import Tuple, List, Dict
import pandas as pd
import argparse # Import for command-line argument parsing

# --- Configuration ---
# Path to your Google Cloud service account key file
CREDENTIALS_PATH = "stt-benchmark-key.json"
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

def load_url_metadata(json_file_path: str, name_to_code_map: dict, target_codes_list: list) -> dict:
    """This function loads language metadata from a JSON file."""
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
    except Exception as e:
        print(f"An unexpected error occurred while loading URL metadata: {e}")
    return video_id_to_lang_code

def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """This function resamples the audio to the target sample rate required by the API."""
    if current_sr == target_sr:
        return audio_array
    return librosa.resample(y=audio_array.astype(np.float32), orig_sr=current_sr, target_sr=target_sr)

def transcribe_audio_task(task_details: tuple) -> Dict:
    """
    Core function that sends pre-processed audio data to the Google STT API.
    This function is now lean and focused only on the network request.
    """
    client, audio_content, language_code, audio_duration = task_details
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
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=TARGET_SAMPLE_RATE,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)
        requests = [speech.StreamingRecognizeRequest(audio_content=audio_content)]
        
        api_call_start_time = time.time()
        responses = client.streaming_recognize(config=streaming_config, requests=requests)
        results['connection_successful'] = True

        for response in responses:
            if not response.results or not response.results[0].alternatives:
                continue
            result = response.results[0]
            if not result.is_final and results['ttfb_first_partial'] is None:
                results['ttfb_first_partial'] = time.time() - api_call_start_time
            if result.is_final:
                final_transcript_time = time.time()
                processing_time = final_transcript_time - api_call_start_time
                results['latency_to_final'] = processing_time
                results['rtf'] = processing_time / audio_duration if audio_duration > 0 else 0
    except Exception as e:
        results['error'] = f"{type(e).__name__}: {e}"

    results['end_time'] = time.time()
    return results

def run_load_stage(stage_concurrency: int, duration: int, tasks: list, client: speech.SpeechClient) -> Dict:
    """Manages a single stage of the load test using a ThreadPoolExecutor."""
    print(f"\n--- Running Stage: {stage_concurrency} Concurrent Calls for {duration} seconds ---")
    stage_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=stage_concurrency) as executor:
        futures = []
        start_time = time.time()
        task_index = 0
        
        # Continuously submit tasks for the specified duration
        while time.time() - start_time < duration:
            # Get pre-processed task data
            audio_content, language_code, audio_duration = tasks[task_index % len(tasks)]
            task_with_client = (client, audio_content, language_code, audio_duration)
            futures.append(executor.submit(transcribe_audio_task, task_with_client))
            task_index += 1

            # Clean up completed futures to manage memory
            if len(futures) >= stage_concurrency * 2:
                for future in concurrent.futures.as_completed(futures[:stage_concurrency]):
                    try:
                        stage_results.append(future.result())
                    except Exception as e:
                        stage_results.append({'error': str(e)})
                    futures.remove(future)
        
        # Collect results from any remaining futures after the duration has passed
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Collecting final results"):
            try:
                stage_results.append(future.result())
            except Exception as e:
                stage_results.append({'error': str(e)})

    return analyze_stage_results(stage_results, stage_concurrency)

def analyze_stage_results(results: List[Dict], concurrency: int) -> Dict:
    """Analyzes the results from a load stage and calculates key performance indicators."""
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
    The main function that orchestrates the entire stress test.
    It now accepts concurrency and duration as arguments.
    """
    print("--- Initializing STT API Stress Test ---")
    
    # 1. Load Metadata
    url_language_metadata = load_url_metadata(
        URL_META_JSON_PATH,
        LANGUAGE_NAME_TO_STT_CODE_MAP,
        USER_SPECIFIED_TARGET_LANGUAGE_CODES
    )
    if not url_language_metadata:
        print("Failed to load language metadata. Aborting.")
        return

    # 2. Match audio files with metadata
    filepath_tasks = []
    for root, _, files in os.walk(BASE_AUDIO_DIRECTORY):
        for filename in files:
            if any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac']):
                video_id_match = re.search(r'([a-zA-Z0-9_-]{11})', filename)
                if video_id_match and video_id_match.group(1) in url_language_metadata:
                    video_id = video_id_match.group(1)
                    filepath_tasks.append((os.path.join(root, filename), url_language_metadata[video_id]))
    
    if not filepath_tasks:
        print("No audio files matched with metadata. Aborting.")
        return

    # 3. CRITICAL STEP: Pre-process all audio files into memory
    print("\n--- Pre-processing all audio files before test ---")
    preprocessed_tasks = []
    for filepath, lang_code in tqdm(filepath_tasks, desc="Processing Audio"):
        try:
            audio_array, original_sr = librosa.load(filepath, sr=None, mono=True)
            audio_duration = librosa.get_duration(y=audio_array, sr=original_sr)
            if original_sr != TARGET_SAMPLE_RATE:
                audio_array = resample_audio(audio_array, original_sr, TARGET_SAMPLE_RATE)
            content = (audio_array * 32767).astype(np.int16).tobytes()
            preprocessed_tasks.append((content, lang_code, audio_duration))
        except Exception as e:
            print(f"Failed to process {filepath}: {e}")

    if not preprocessed_tasks:
        print("No audio files could be pre-processed. Aborting.")
        return

    # 4. Create a single, shared client
    credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
    speech_client = speech.SpeechClient(credentials=credentials)

    # 5. Run the specified test stage
    all_results = {}
    stage_summary = run_load_stage(concurrency_level, duration, preprocessed_tasks, speech_client)
    all_results.update(stage_summary)
    
    print("\n--- Stage Summary ---")
    print(json.dumps(stage_summary, indent=4))

    # 6. Save results to a uniquely named file
    results_df = pd.DataFrame.from_dict(all_results, orient='index')
    output_filename = f"google_stress_test_results_{concurrency_level}_calls.csv"
    results_df.to_csv(output_filename)
    print("\n--- Stress Test Complete ---")
    print(f"Results saved to {output_filename}")
    print(results_df)

if __name__ == "__main__":
    # Add argument parsing to accept concurrency and duration from the command line
    parser = argparse.ArgumentParser(description="Run a concurrency test for Google STT API.")
    parser.add_argument('-c', '--concurrency', type=int, required=True, help='Number of concurrent calls to simulate.')
    parser.add_argument('-d', '--duration', type=int, required=True, help='Duration of the test in seconds.')
    args = parser.parse_args()

    # Check for necessary files before starting
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"CRITICAL ERROR: Google Cloud credentials file not found at '{CREDENTIALS_PATH}'.")
    elif not os.path.exists(URL_META_JSON_PATH):
        print(f"CRITICAL ERROR: URL metadata file not found at '{URL_META_JSON_PATH}'.")
    elif not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"CRITICAL ERROR: Base audio directory not found at '{BASE_AUDIO_DIRECTORY}'.")
    else:
        # Call the pipeline with the parsed arguments
        pipeline(concurrency_level=args.concurrency, duration=args.duration)