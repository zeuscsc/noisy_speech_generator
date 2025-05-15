import os
import traceback
import numpy as np
import librosa
from google.cloud import speech
import concurrent.futures
from tqdm import tqdm
from google.oauth2 import service_account

BASE_AUDIO_DIRECTORY = "sampled_testcase"
TARGET_SAMPLE_RATE = 16000
MAX_WORKERS = 8

POSSIBLE_LANGUAGE_CODES = ["yue-Hant-HK", "en-US", "cmn-Hans-CN"]
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.aac']

def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """Resamples audio using librosa."""
    if current_sr == target_sr:
        return audio_array
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)

    if not audio_array.flags['C_CONTIGUOUS']:
        audio_array = np.ascontiguousarray(audio_array)

    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio

def transcribe_audio_file(audio_file_path_and_output_path: tuple) -> str:
    """
    Loads an audio file, transcribes it using Google STT API with language detection,
    and saves the result to a text file.
    Returns the input audio_file_path upon completion or error for tracking.
    """
    audio_file_path, output_txt_path = audio_file_path_and_output_path

    if not POSSIBLE_LANGUAGE_CODES:
        error_msg = f"Error for {audio_file_path}: POSSIBLE_LANGUAGE_CODES list is empty.\n"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return audio_file_path

    primary_language_code = POSSIBLE_LANGUAGE_CODES[0]

    try:
        audio_array, original_sampling_rate = librosa.load(audio_file_path, sr=None, mono=True)
        if audio_array.size == 0:
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write(f"Error for {audio_file_path}: Audio array loaded from file is empty.\n")
            return audio_file_path
    except FileNotFoundError:
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error for {audio_file_path}: Audio file not found.\n")
        return audio_file_path
    except Exception as e:
        error_msg = f"Error loading/preparing audio file {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return audio_file_path

    try:
        credentials_path = "C:/Users/User/stt-benchmark-key.json" 
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = speech.SpeechClient(credentials=credentials)
    except Exception as e:
        error_msg = f"Error initializing Google Speech client for {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        return audio_file_path

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
        return audio_file_path

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=TARGET_SAMPLE_RATE,
        language_code=primary_language_code,
        alternative_language_codes=POSSIBLE_LANGUAGE_CODES[1:] if len(POSSIBLE_LANGUAGE_CODES) > 1 else [], 
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True
    )
    audio_input = speech.RecognitionAudio(content=content)

    full_transcript = ""
    detected_language_info = ""

    try:
        response = client.recognize(config=config, audio=audio_input)
        if not response.results:
            full_transcript = "No speech recognized."
        else:
            for result_idx, result in enumerate(response.results):
                lang_for_segment = getattr(result, 'language_code', primary_language_code)
                if result_idx == 0: 
                    detected_language_info = f"Detected language (best guess for first segment): {lang_for_segment}\n"
                full_transcript += result.alternatives[0].transcript + "\n"

        with open(output_txt_path, 'w', encoding='utf-8') as f:
            if detected_language_info:
                f.write(detected_language_info)
            f.write(full_transcript.strip())

    except Exception as e:
        error_msg = f"Error during API call for {audio_file_path}: {e}\n{traceback.format_exc()}"
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)

    return audio_file_path

def collect_audio_files(base_dir: str) -> list:
    """
    Walks through the base_dir, finds audio files, and prepares a list of
    (input_path, output_path) tuples.
    """
    tasks = []
    if not os.path.isdir(base_dir):
        print(f"Error: Base directory '{base_dir}' not found.")
        return tasks
    if not POSSIBLE_LANGUAGE_CODES: 
        print("Error: POSSIBLE_LANGUAGE_CODES list is empty. Please configure it.")
        return tasks

    print(f"Scanning for audio files in: {base_dir}")
    all_files_to_scan = []
    for root, _, files in os.walk(base_dir):
        for filename in files:
            all_files_to_scan.append(os.path.join(root, filename))

    
    for audio_file_path in tqdm(all_files_to_scan, desc="Scanning files"):
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext in AUDIO_EXTENSIONS:
            base_name_without_ext = os.path.splitext(os.path.basename(audio_file_path))[0]
            output_filename = base_name_without_ext + ".google.txt"
            output_txt_path = os.path.join(os.path.dirname(audio_file_path), output_filename)

            os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)

            tasks.append((audio_file_path, output_txt_path))
    return tasks

def process_all_audio_files_parallel():
    """
    Collects all audio files and processes them in parallel using Google STT.
    """
    tasks = collect_audio_files(BASE_AUDIO_DIRECTORY)

    if not tasks:
        print("No audio files found or an error occurred during scanning.")
        return

    print(f"\nFound {len(tasks)} audio files to process.")
    effective_max_workers = MAX_WORKERS if MAX_WORKERS and MAX_WORKERS > 0 else os.cpu_count()
    print(f"Using up to {effective_max_workers} worker processes.")

    if not POSSIBLE_LANGUAGE_CODES:
        print("Warning: POSSIBLE_LANGUAGE_CODES is empty. Transcription might use default or fail.")
    else:
        primary_lang = POSSIBLE_LANGUAGE_CODES[0]
        alt_langs = POSSIBLE_LANGUAGE_CODES[1:]
        print(f"Languages for detection: Primary '{primary_lang}', Alternatives: {alt_langs if alt_langs else 'None'}")


    processed_count = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=effective_max_workers) as executor:
        futures = [executor.submit(transcribe_audio_file, task) for task in tasks]

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(tasks), desc="Transcribing audio"):
            try:
                result_path = future.result()
                processed_count += 1
            except Exception as e:
                print(f"A task in the pool failed unexpectedly: {e}")
                processed_count += 1


    print(f"\n--- Processing Complete ---")
    print(f"Total audio files submitted for processing: {processed_count}")
    print(f"Check individual '.google.txt' files for transcription results or errors.")

if __name__ == "__main__":
    process_all_audio_files_parallel()