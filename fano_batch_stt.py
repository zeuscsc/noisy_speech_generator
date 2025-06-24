import os
import re
import traceback
from urllib.parse import parse_qs, urlparse, urljoin
from urllib.request import pathname2url
import base64
import requests
import concurrent.futures
from tqdm import tqdm
import json
import time
from typing import Tuple, Optional, List, Dict
import pandas as pd
import urllib3

# --- Configuration ---
# Base directory where your audio files are located.
BASE_AUDIO_DIRECTORY = "testset"
# Maximum number of parallel processes for transcription.
MAX_WORKERS = 8
# File extensions to look for.
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.aac']
# Path to the metadata file that maps video IDs to languages.
URL_META_JSON_PATH = "urls.meta.json"
# The API key (Bearer Token) for your FANO STT API.
FANO_API_KEY = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJmYW5vX3NwZWVjaF9kaWFyaXplX3F1b3RhX3N0cmF0ZWd5IjoiZGVmYXVsdCIsImZhbm9fc3BlZWNoX2dlbmVyYXRlX3ZvaWNlcHJpbnRfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfcmVjb2duaXplX3F1b3RhX3N0cmF0ZWd5Ijoic2tpcCIsImZhbm9fc3BlZWNoX3N0cmVhbWluZ19kZXRlY3RfYWN0aXZpdHlfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfc3RyZWFtaW5nX3JlY29nbml6ZV9xdW90YV9zdHJhdGVneSI6ImRlZmF1bHQiLCJmYW5vX3NwZWVjaF9yZXBsYWNlX3BocmFzZXNfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiZmFub19zcGVlY2hfc3ludGhlc2l6ZV9zcGVlY2hfcXVvdGFfc3RyYXRlZ3kiOiJkZWZhdWx0IiwiaWF0IjoxNzQ5MTEzNjAxLCJleHAiOjIwNjQ2ODI4NTAsImF1ZCI6ImZhbm8tc3BlZWNoLWdhdGV3YXkiLCJpc3MiOiJodHRwczovL2F1dGguZmFuby5haSIsInN1YiI6ImZhbm8tc3BlZWNoLWdhdGV3YXkifQ.b90NU8e1zs_HlbvosewJN0_GJpEcb2B7qOvA1rNNj8mGDrOM3j_Y_DKZsKi3S2ZgbekxrewW8nPb5KaZR-mpTq46W5T8MMgdBS6r3kGx__2A6sH-NPOzZiqbEfiFOXR5pHQLG7KucgxPSz0J3B_ZmwhT4T-mcxjnhOMx7ALEbFvBh964nlXDXZw9LGGUUbfZjv_CVVKvVD0dklI5HUxr11a1tvoZeugbzzF1VKdyiSp_lp45unoIPqI-rbZf75qclhufS43xaB8Ye0FYlp7khyE_d5gqG9pLj8uu3m1kjq8BUwJRFfcE-c_k6bYbiLDjY1KHLXqv2JQPW03OF_5Z4w"
# The endpoint URL for your FANO STT API.
FANO_API_URL = 'https://portal-hsbc-voiceinput-gcp.fano.ai/speech/recognize'

# Languages you want to process, using the codes from your metadata.
USER_SPECIFIED_TARGET_LANGUAGE_CODES = ["yue-Hant-HK", "en-US", "cmn-Hans-CN"]

# Maps language names from metadata to the STT codes used in the metadata.
LANGUAGE_NAME_TO_STT_CODE_MAP = {
    "Cantonese": "yue-Hant-HK",
    "English": "en-US",
    "Mandarin": "cmn-Hans-CN"
}

# Maps the metadata STT codes to the codes required by the FANO API.
FANO_API_LANGUAGE_MAP = {
    "yue-Hant-HK": "yue",
    "en-US": "en",
    "cmn-Hans-CN": "cmn"
}

# --- Utility Functions ---

def load_url_metadata(json_file_path: str, name_to_code_map: dict, target_codes_list: list) -> dict:
    """Loads and validates language metadata from a JSON file."""
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
                    try:
                        parsed_url = urlparse(url_str)
                        hostname = parsed_url.hostname.lower() if parsed_url.hostname else ""
                        if 'youtube.com' in hostname or 'youtu.be' in hostname:
                            if 'v' in parse_qs(parsed_url.query):
                                current_video_id = parse_qs(parsed_url.query)['v'][0]
                            else:
                                # Simplified extractor for other YouTube URL formats
                                match = re.search(r"(?:v=|\/|shorts\/|embed\/)([a-zA-Z0-9_-]{11})", url_str)
                                if match:
                                    current_video_id = match.group(1)
                    except Exception as e:
                        print(f"Warning: Could not parse video ID from URL {url_str}. Error: {e}")
                        continue
            
            if not current_video_id:
                continue
            
            stt_language_code = name_to_code_map.get(language_name)
            if stt_language_code in target_codes_list:
                video_id_to_lang_code[current_video_id] = stt_language_code

    except Exception as e:
        print(f"An error occurred while loading URL metadata: {e}\n{traceback.format_exc()}")
    
    print(f"Successfully loaded language metadata for {len(video_id_to_lang_code)} video IDs.")
    return video_id_to_lang_code


def transcribe_audio_file(task_details: tuple) -> Tuple[str, Optional[float]]:
    """Transcribes a single audio file using the FANO API by sending its base64 content."""
    audio_file_path, output_txt_path, output_json_path, specific_language_code = task_details
    api_call_duration: Optional[float] = None
    
    # Disable SSL warnings from requests
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    api_language_code = FANO_API_LANGUAGE_MAP.get(specific_language_code)

    if not api_language_code:
        error_msg = f"Error for {audio_file_path}: Language code '{specific_language_code}' not supported by FANO API.\n"
        try:
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except Exception as e_write:
            print(f"Critical: Failed to write error to {output_txt_path}. Error: {e_write}")
        return output_txt_path, api_call_duration

    try:
        # Read the audio file, encode it to base64, and decode to a string
        with open(audio_file_path, 'rb') as audio_file:
            audio_content = audio_file.read()
            base64_audio_bytes = base64.b64encode(audio_content)
            base64_audio_string = base64_audio_bytes.decode('utf-8')
    except FileNotFoundError:
        error_msg = f"Error preparing audio file {audio_file_path}: File not found.\n"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, api_call_duration
    except Exception as e:
        error_msg = f"Error preparing audio file {audio_file_path} for API call: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, api_call_duration

    # Prepare the request for the FANO API
    headers = {
        'accept': 'application/json',
        'Authorization': FANO_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        "config": {
            "languageCode": api_language_code
        },
        "audio": {
            "content": base64_audio_string
        }
    }

    full_transcript = ""
    
    try:
        start_time = time.monotonic()
        # In a real scenario, you might need to configure proxies or handle certificates
        response = requests.post(FANO_API_URL, headers=headers, json=data, verify=False)
        end_time = time.monotonic()
        api_call_duration = end_time - start_time

        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        response_json = response.json()

        # Save the full JSON response
        try:
            with open(output_json_path, 'w', encoding='utf-8') as json_f:
                json.dump(response_json, json_f, ensure_ascii=False, indent=4)
        except Exception as e_json:
             print(f"Warning: Failed to save JSON response for {audio_file_path}. Error: {e_json}")

        # Process the JSON response to extract the transcript
        if response_json.get('results'):
            for result in response_json['results']:
                if result.get('alternatives') and result['alternatives'][0].get('transcript'):
                    full_transcript += result['alternatives'][0]['transcript'] + "\n"
        
        if not full_transcript:
            full_transcript = "No speech recognized."

        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_transcript.strip())
        return output_txt_path, api_call_duration

    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred for {audio_file_path}: {http_err}\nResponse: {response.text}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, None
    except Exception as e:
        error_msg = f"Error during API call for {audio_file_path} (Lang: {api_language_code}): {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, None


def collect_audio_files(base_dir: str, video_id_to_lang_map: Dict[str, str]) -> List[Tuple[str, str, str, str]]:
    """Collects audio files and prepares the transcription tasks."""
    tasks: List[Tuple[str, str, str, str]] = []
    if not os.path.isdir(base_dir):
        print(f"Error: Base directory '{base_dir}' not found.")
        return tasks
    
    print(f"Scanning for audio files in: {base_dir}")
    all_files_to_scan = [os.path.join(root, filename) for root, _, files in os.walk(base_dir) for filename in files]
    
    for audio_file_path in tqdm(all_files_to_scan, desc="Matching files with metadata"):
        if os.path.splitext(audio_file_path)[1].lower() in AUDIO_EXTENSIONS:
            base_name_from_file = os.path.splitext(os.path.basename(audio_file_path))[0]
            
            # Extract the 11-character YouTube-like ID from the filename
            match = re.search(r"([a-zA-Z0-9_-]{11})", base_name_from_file)
            if not match:
                continue

            extracted_video_id = match.group(1)
            specific_language_code = video_id_to_lang_map.get(extracted_video_id)

            if specific_language_code:
                output_dir = os.path.dirname(audio_file_path)
                output_txt_filename = base_name_from_file + ".fano.txt"
                output_json_filename = base_name_from_file + ".fano.json"
                output_txt_path = os.path.join(output_dir, output_txt_filename)
                output_json_path = os.path.join(output_dir, output_json_filename)
                
                tasks.append((audio_file_path, output_txt_path, output_json_path, specific_language_code))
                
    if not tasks:
        print("No audio files matched with language metadata or found after filtering.")
    return tasks

def pipeline():
    """Main function to run the transcription pipeline."""
    print("--- Starting Transcription Process (FANO API) ---")
    print(f"Target STT Languages: {', '.join(USER_SPECIFIED_TARGET_LANGUAGE_CODES)}")
    
    url_language_metadata = load_url_metadata(
        URL_META_JSON_PATH,
        LANGUAGE_NAME_TO_STT_CODE_MAP,
        USER_SPECIFIED_TARGET_LANGUAGE_CODES
    )

    if not url_language_metadata:
        print("Failed to load any valid language metadata. Aborting.")
        return

    tasks = collect_audio_files(BASE_AUDIO_DIRECTORY, url_language_metadata)

    if not tasks:
        print("No audio files found or matched with metadata for processing.")
        return

    print(f"\nFound {len(tasks)} audio files to process.")
    effective_max_workers = min(MAX_WORKERS, os.cpu_count() or 1)
    print(f"Using up to {effective_max_workers} worker processes.")

    api_call_durations_list = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=effective_max_workers) as executor:
        futures = [executor.submit(transcribe_audio_file, task) for task in tasks]
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(tasks), desc="Transcribing audio"):
            try:
                output_path, duration = future.result()
                api_call_durations_list.append({'output_path': output_path, 'duration_seconds': duration})
            except Exception as e:
                print(f"A task in the pool failed: {e}\n{traceback.format_exc()}")

    print(f"\n--- Processing Complete ---")
    print(f"Check individual '.fano.json' and '.fano.txt' files in '{BASE_AUDIO_DIRECTORY}' subdirectories.")

    duration_csv_path = "fano_api_call_durations.csv"
    if api_call_durations_list:
        try:
            df = pd.DataFrame(api_call_durations_list)
            df = df.sort_values(by='output_path')
            df.to_csv(duration_csv_path, index=False, encoding='utf-8')
            print(f"API call durations saved to: {duration_csv_path}")
        except Exception as e:
            print(f"Error saving API call durations to CSV: {e}")
    else:
        print("No API call durations were recorded.")

if __name__ == "__main__":
    if not os.path.exists(URL_META_JSON_PATH):
        print(f"CRITICAL ERROR: URL metadata file not found at '{URL_META_JSON_PATH}'.")
    elif not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"CRITICAL ERROR: Base audio directory not found at '{BASE_AUDIO_DIRECTORY}'.")
    else:
        pipeline()
