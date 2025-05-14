import os
import traceback
import numpy as np
import librosa
from google.cloud import speech 


BASE_AUDIO_DIRECTORY = "sampled_testcase"
TARGET_SAMPLE_RATE = 16000



POSSIBLE_LANGUAGE_CODES = ["yue-Hant-HK", "en-US", "cmn-Hans-CN"] 


AUDIO_EXTENSIONS = ['.mp3', '.wav', '.flac', '.aac']


def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    if current_sr == target_sr:
        return audio_array
    print(f"Resampling from {current_sr} Hz to {target_sr} Hz...")
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    if not audio_array.flags['C_CONTIGUOUS']:
        audio_array = np.ascontiguousarray(audio_array)
    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio


def transcribe_audio_file(audio_file_path: str, output_txt_path: str):
    print(f"\nProcessing audio file: {audio_file_path}")
    if not POSSIBLE_LANGUAGE_CODES:
        print("Error: POSSIBLE_LANGUAGE_CODES list is empty. Cannot perform language detection.")
        
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write("Error: POSSIBLE_LANGUAGE_CODES list is empty.\n")
        return
        
    
    primary_language_code = POSSIBLE_LANGUAGE_CODES[0]
    print(f"Attempting language detection with primary '{primary_language_code}' and alternatives: {POSSIBLE_LANGUAGE_CODES}")
    print(f"Target output file: {output_txt_path}")

    try:
        audio_array, original_sampling_rate = librosa.load(audio_file_path, sr=None, mono=True)
        audio_id = os.path.basename(audio_file_path)
        print(f"Loaded audio file. ID='{audio_id}', Original SR={original_sampling_rate} Hz")

        if audio_array.size == 0:
            print(f"Error: Audio array loaded from file '{audio_file_path}' is empty.")
            with open(output_txt_path, 'w', encoding='utf-8') as f:
                f.write("Error: Audio array loaded from file is empty.\n")
            return
    except FileNotFoundError:
        print(f"Error: Audio file not found at '{audio_file_path}'.")
        return
    except Exception as e:
        print(f"\n******** ERROR LOADING/PREPARING AUDIO FILE: {audio_file_path} ********")
        print(f"Could not load or prepare audio file: {e}")
        traceback.print_exc()
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error loading/preparing audio file: {e}\n")
        return

    try:
        client = speech.SpeechClient()
    except Exception as e:
        print("\n******** ERROR INITIALIZING CLIENT ********")
        print(f"Could not initialize Google Speech client: {e}")
        traceback.print_exc()
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error initializing Google Speech client: {e}\n")
        return

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
        print(f"\n******** ERROR PROCESSING AUDIO ARRAY for {audio_file_path} ********")
        print(f"Could not resample or convert audio: {e}")
        traceback.print_exc()
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error processing audio array: {e}\n")
        return

    
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=TARGET_SAMPLE_RATE,
        language_code=primary_language_code,               
        alternative_language_codes=POSSIBLE_LANGUAGE_CODES, 
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True 
    )
    audio = speech.RecognitionAudio(content=content)

    full_transcript = ""
    detected_language_info = ""

    try:
        response = client.recognize(config=config, audio=audio)

        if not response.results:
            print(f"API returned no results for {audio_file_path} (no speech recognized?).")
            full_transcript = "No speech recognized."
        else:
            
            
            for result_idx, result in enumerate(response.results):
                
                
                
                
                lang_for_segment = getattr(result, 'language_code', primary_language_code) 
                if result_idx == 0: 
                     detected_language_info = f"Detected language (best guess for first segment): {lang_for_segment}\n"
                     print(detected_language_info.strip())

                full_transcript += result.alternatives[0].transcript + "\n"
                
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            if detected_language_info:
                f.write(detected_language_info)
            f.write(full_transcript.strip())
        print(f"Transcription saved to {output_txt_path}")

    except Exception as e:
        print(f"\n******** ERROR DURING API CALL for {audio_file_path} ********")
        print(f"API call failed: {e}")
        traceback.print_exc()
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Error during API call: {e}\n")


def process_all_audio_files():
    if not os.path.isdir(BASE_AUDIO_DIRECTORY):
        print(f"Error: Base directory '{BASE_AUDIO_DIRECTORY}' not found.")
        return
    if not POSSIBLE_LANGUAGE_CODES:
        print("Error: POSSIBLE_LANGUAGE_CODES list is empty. Please configure it at the top of the script.")
        return

    print(f"Starting transcription process for directory: {BASE_AUDIO_DIRECTORY}")
    print(f"Languages for detection: Primary '{POSSIBLE_LANGUAGE_CODES[0]}', Alternatives: {POSSIBLE_LANGUAGE_CODES}")
    processed_count = 0
    
    for root, dirs, files in os.walk(BASE_AUDIO_DIRECTORY):
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in AUDIO_EXTENSIONS:
                audio_file_path = os.path.join(root, filename)
                base_name_without_ext = os.path.splitext(filename)[0]
                output_filename = base_name_without_ext + ".google_alt_lang.txt" 
                output_txt_path = os.path.join(root, output_filename)
                os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
                transcribe_audio_file(audio_file_path, output_txt_path)
                processed_count += 1

    print(f"\n--- Processing Complete ---")
    print(f"Total audio files processed: {processed_count}")

if __name__ == "__main__":
    process_all_audio_files()