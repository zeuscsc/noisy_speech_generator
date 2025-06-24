import os
import re
import traceback
from urllib.parse import parse_qs, urlparse
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

BASE_AUDIO_DIRECTORY = "testset"
TARGET_SAMPLE_RATE = 16000
MAX_WORKERS = 8

AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.aac']
CREDENTIALS_PATH = "C:/Users/User/stt-benchmark-key.json"
URL_META_JSON_PATH = "urls.meta.json"

USER_SPECIFIED_TARGET_LANGUAGE_CODES = ["yue-Hant-HK", "en-US", "cmn-Hans-CN"]

LANGUAGE_NAME_TO_STT_CODE_MAP = {
    "Cantonese": "yue-Hant-HK",
    "English": "en-US",
    "Mandarin": "cmn-Hans-CN"
}

def load_url_metadata(json_file_path: str, name_to_code_map: dict, target_codes_list: list) -> dict:
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
                print(f"Warning: Skipping item due to missing 'language' in JSON: {item}")
                continue

            current_video_id = item.get("video_id")

            if not current_video_id:
                url_str = item.get("url")
                if url_str:
                    try:
                        parsed_url = urlparse(url_str)
                        hostname = parsed_url.hostname.lower() if parsed_url.hostname else ""
                        path = parsed_url.path
                        
                        is_youtube_url = 'youtube.com' in hostname or 'youtu.be' in hostname or \
                                         'youtube.com' in hostname or \
                                         'youtu.be' in hostname
                        
                        extracted_youtube_id = None
                        if is_youtube_url:
                            if 'youtube.com' in hostname:
                                if '/watch' in path:
                                    params = parse_qs(parsed_url.query)
                                    if 'v' in params and params['v'] and params['v'][0]:
                                        extracted_youtube_id = params['v'][0]
                                elif '/embed/' in path:
                                    path_segment = path.split('/embed/')
                                    if len(path_segment) > 1:
                                        extracted_youtube_id = path_segment[1].split('/')[0].split('?')[0]
                                else: 
                                    for prefix in ['/v/', '/vi/', '/shorts/']:
                                        if prefix in path:
                                            path_segments = path.split(prefix)
                                            if len(path_segments) > 1:
                                                extracted_youtube_id = path_segments[1].split('/')[0].split('?')[0]
                                                break
                            elif 'youtu.be' in hostname:
                                 if path.lstrip('/'):
                                    extracted_youtube_id = path.lstrip('/').split('?')[0]
                            elif 'youtu.be' in hostname:
                                extracted_youtube_id = path.lstrip('/')
                            elif 'youtube.com' in hostname:
                                if '/watch' in path:
                                    params = parse_qs(parsed_url.query)
                                    if 'v' in params and params['v']:
                                        extracted_youtube_id = params['v'][0]
                                elif '/embed/' in path or '/v/' in path or '/vi/' in path or '/shorts/' in path:
                                    for prefix in ['/embed/', '/v/', '/vi/', '/shorts/']:
                                        if prefix in path:
                                            path_segments = path.split(prefix)
                                            if len(path_segments) > 1:
                                                extracted_youtube_id = path_segments[1].split('/')[0].split('?')[0]
                                                break
                            
                            if extracted_youtube_id and re.match(r"^[a-zA-Z0-9_-]{11}$", extracted_youtube_id):
                                current_video_id = extracted_youtube_id
                            elif extracted_youtube_id:
                                print(f"Warning: Extracted '{extracted_youtube_id}' from URL '{url_str}' but it's not a valid 11-character YouTube ID. Skipping.")
                                continue
                            else: 
                                print(f"Warning: URL '{url_str}' looks like YouTube but couldn't extract a video ID. Skipping.")
                                continue
                        else: 
                            derived_id = os.path.basename(url_str)
                            if derived_id:
                                current_video_id = derived_id
                            else:
                                print(f"Warning: Derived empty ID using os.path.basename from non-YouTube URL '{url_str}'. Skipping.")
                                continue
                    except Exception as e:
                        print(f"Warning: Error processing URL '{url_str}' for video ID. Error: {e}. Skipping.")
                        continue
            
            if not current_video_id:
                print(f"Warning: Skipping item due to missing or unobtainable video ID. Item: {item}")
                continue

            stt_language_code = name_to_code_map.get(language_name)
            if not stt_language_code:
                print(f"Warning: Language name '{language_name}' for video ID '{current_video_id}' "
                      f"not found in LANGUAGE_NAME_TO_STT_CODE_MAP. Skipping this entry.")
                continue

            if stt_language_code not in target_codes_list:
                print(f"Warning: Language '{language_name}' (maps to STT code '{stt_language_code}') for video ID '{current_video_id}' "
                      f"is not in USER_SPECIFIED_TARGET_LANGUAGE_CODES. Skipping this entry.")
                continue
            
            video_id_to_lang_code[current_video_id] = stt_language_code

    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {json_file_path}. Please check its format.")
    except Exception as e:
        print(f"An unexpected error occurred while loading URL metadata: {e}\n{traceback.format_exc()}")
    
    if not video_id_to_lang_code:
        print("Warning: No valid language metadata loaded. Transcriptions might fail or be skipped.")
    else:
        print(f"Successfully loaded language metadata for {len(video_id_to_lang_code)} video IDs.")
    return video_id_to_lang_code

def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    if current_sr == target_sr:
        return audio_array
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    if not audio_array.flags['C_CONTIGUOUS']:
        audio_array = np.ascontiguousarray(audio_array)
    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio

def transcribe_audio_file(task_details: tuple) -> Tuple[str, Optional[float]]:
    audio_file_path, output_txt_path, specific_language_code = task_details
    api_call_duration: Optional[float] = None

    if not specific_language_code:
        error_msg = f"Error for {audio_file_path}: No specific language code provided for transcription.\n"
        try:
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except Exception as e_write:
            print(f"Critical: Failed to write error to {output_txt_path} for {audio_file_path}. Error: {e_write}")
        return output_txt_path, api_call_duration

    try:
        audio_array, original_sampling_rate = librosa.load(audio_file_path, sr=None, mono=True)
        if audio_array.size == 0:
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Error for {audio_file_path}: Audio array loaded from file is empty.\n")
            return output_txt_path, api_call_duration
    except FileNotFoundError:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error for {audio_file_path}: Audio file not found.\n")
        return output_txt_path, api_call_duration
    except Exception as e:
        error_msg = f"Error loading/preparing audio file {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, api_call_duration

    try:
        if not os.path.exists(CREDENTIALS_PATH):
            error_msg = f"Error initializing Google Speech client for {audio_file_path}: Credentials file not found at {CREDENTIALS_PATH}\n"
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(error_msg)
            return output_txt_path, api_call_duration
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        client = speech.SpeechClient(credentials=credentials)
    except Exception as e:
        error_msg = f"Error initializing Google Speech client for {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, api_call_duration

    try:
        if original_sampling_rate != TARGET_SAMPLE_RATE:
            audio_array_resampled = resample_audio(audio_array, original_sampling_rate, TARGET_SAMPLE_RATE)
        else:
            audio_array_resampled = audio_array
        
        if audio_array_resampled.dtype != np.float32:
            audio_array_resampled = audio_array_resampled.astype(np.float32)

        np.clip(audio_array_resampled, -1.0, 1.0, out=audio_array_resampled)
        int16_array = (audio_array_resampled * 32767).astype(np.int16)
        content = int16_array.tobytes()
    except Exception as e:
        error_msg = f"Error processing audio array for {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, api_call_duration

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=TARGET_SAMPLE_RATE,
        language_code=specific_language_code,
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True
    )
    audio_input = speech.RecognitionAudio(content=content)

    full_transcript = ""
    language_info = f"Specified language for transcription: {specific_language_code}\n"

    try:
        start_time = time.monotonic()
        response = client.recognize(config=config, audio=audio_input)
        end_time = time.monotonic()
        api_call_duration = end_time - start_time

        if not response.results:
            full_transcript = "No speech recognized."
        else:
            for result_idx, result in enumerate(response.results):
                if result_idx == 0 and hasattr(result, 'language_code') and result.language_code != specific_language_code:
                    language_info += f"API used language code: {result.language_code} (differs from specified {specific_language_code})\n"
                elif result_idx == 0 and hasattr(result, 'language_code'):
                    language_info += f"API confirmed using language code: {result.language_code}\n"
                full_transcript += result.alternatives[0].transcript + "\n"
        
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(full_transcript.strip())
        return output_txt_path, api_call_duration

    except Exception as e:
        error_msg = f"Error during API call for {audio_file_path} (Lang: {specific_language_code}): {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return output_txt_path, None

def collect_audio_files(base_dir: str, video_id_to_lang_map: Dict[str, str]) -> List[Tuple[str, str, str]]:
    tasks: List[Tuple[str, str, str]] = []
    if not os.path.isdir(base_dir):
        print(f"Error: Base directory '{base_dir}' not found.")
        return tasks
    
    if not video_id_to_lang_map:
        print("Warning: Language metadata map is empty. Files may be skipped if they rely on this map.")

    print(f"Scanning for audio files in: {base_dir}")
    all_files_to_scan = []
    for root, _, files in os.walk(base_dir):
        for filename in files:
            all_files_to_scan.append(os.path.join(root, filename))
    
    for audio_file_path in tqdm(all_files_to_scan, desc="Matching files with metadata"):
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext in AUDIO_EXTENSIONS:
            base_name_from_file = os.path.splitext(os.path.basename(audio_file_path))[0]
            
            extracted_video_id_for_lookup = None
            match = re.search(r"([a-zA-Z0-9_-]{11})", base_name_from_file)
            if match:
                extracted_video_id_for_lookup = match.group(1)
            
            if not extracted_video_id_for_lookup:
                print(f"Info: Could not extract an 11-character video ID pattern from filename base '{base_name_from_file}' (from file '{os.path.basename(audio_file_path)}'). This file will be skipped if metadata relies on 11-char IDs.")
                continue

            specific_language_code = video_id_to_lang_map.get(extracted_video_id_for_lookup)

            if not specific_language_code:
                print(f"Info: No language metadata found in map for extracted video ID '{extracted_video_id_for_lookup}' (from file '{os.path.basename(audio_file_path)}'). Skipping this file.")
                continue 

            output_filename = base_name_from_file + ".google.txt"
            output_dir = os.path.dirname(audio_file_path)
            output_txt_path = os.path.join(output_dir, output_filename)
            
            tasks.append((audio_file_path, output_txt_path, specific_language_code))
            
    if not tasks:
        print("No audio files matched with language metadata or found after filtering.")
    return tasks

def pipeline():
    print("--- Starting Transcription Process ---")
    print(f"Target STT Languages: {', '.join(USER_SPECIFIED_TARGET_LANGUAGE_CODES)}")
    print(f"Attempting to load language metadata from: {URL_META_JSON_PATH}")

    url_language_metadata = load_url_metadata(
        URL_META_JSON_PATH,
        LANGUAGE_NAME_TO_STT_CODE_MAP,
        USER_SPECIFIED_TARGET_LANGUAGE_CODES
    )

    if not url_language_metadata:
        print("Failed to load any valid language metadata. Aborting transcription process.")
        return

    tasks = collect_audio_files(BASE_AUDIO_DIRECTORY, url_language_metadata)

    if not tasks:
        print("No audio files found or matched with metadata for processing.")
        return

    print(f"\nFound {len(tasks)} audio files matched with language metadata to process.")
    effective_max_workers = MAX_WORKERS if MAX_WORKERS and MAX_WORKERS > 0 else (os.cpu_count() or 1)
    print(f"Using up to {effective_max_workers} worker processes.")

    processed_count = 0
    api_call_durations_list = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=effective_max_workers) as executor:
        futures = [executor.submit(transcribe_audio_file, task) for task in tasks]
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(tasks), desc="Transcribing audio"):
            try:
                output_path, duration = future.result()
                if duration is not None:
                    api_call_durations_list.append({'output_path': output_path, 'duration_seconds': duration})
                else:
                    api_call_durations_list.append({'output_path': output_path, 'duration_seconds': None})
                processed_count += 1
            except Exception as e:
                print(f"A task in the pool encountered an error during execution or result retrieval: {e}\n{traceback.format_exc()}")
                processed_count += 1 
                
    print(f"\n--- Processing Complete ---")
    print(f"Total audio files submitted for processing: {processed_count} (out of {len(tasks)} matched files)")
    print(f"Check individual '.google.txt' files in '{BASE_AUDIO_DIRECTORY}' subdirectories for transcription results or errors.")

    duration_csv_path = "google_api_call_durations.csv"
    if api_call_durations_list:
        try:
            df = pd.DataFrame(api_call_durations_list)
            df = df.sort_values(by='output_path')
            df.to_csv(duration_csv_path, index=False, encoding='utf-8')
            print(f"API call durations successfully saved to: {duration_csv_path}")
        except Exception as e:
            print(f"Error saving API call durations to CSV: {e}\n{traceback.format_exc()}")
    else:
        print("No API call durations were recorded to save.")

if __name__ == "__main__":
    if not os.path.exists(CREDENTIALS_PATH):
         print(f"CRITICAL ERROR: Google Cloud credentials file not found at '{CREDENTIALS_PATH}'.")
         print("Please set the correct path for CREDENTIALS_PATH or use GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    elif not os.path.exists(URL_META_JSON_PATH):
        print(f"CRITICAL ERROR: URL metadata file not found at '{URL_META_JSON_PATH}'.")
        print("Please ensure the metadata file exists at the specified path.")
    elif not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"CRITICAL ERROR: Base audio directory not found at '{BASE_AUDIO_DIRECTORY}'.")
        print("Please ensure the audio directory exists.")
    else:
        pipeline()
