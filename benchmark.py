import os
import traceback
import time
import numpy as np
import librosa
import pandas as pd
from tqdm import tqdm
from datasets import load_from_disk
from google.cloud import speech
import jiwer # For calculating CER
from datetime import datetime # For timestamps

# --- Configuration ---
DATASET_PATH = "streamed_subset" # Path to your saved Hugging Face dataset
TARGET_SAMPLE_RATE = 16000
LANGUAGE_CODE = "yue-Hant-HK" # Cantonese (Traditional, Hong Kong)

# Set MAX_SAMPLES to an integer (e.g., 100) to test only a subset,
# or None to test all samples. Set to a small number like 10 for initial testing.
MAX_SAMPLES = 10

OUTPUT_CSV_FILE = "google_stt_cantonese_benchmark_results_proxy.csv" # Updated filename

# Set to True to print comparison table for each sample, False to disable
DISPLAY_COMPARISON_TABLE = True

# Ensure you have set the GOOGLE_APPLICATION_CREDENTIALS environment variable
# --- End Configuration ---


def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """Resamples audio using librosa."""
    if current_sr == target_sr:
        if audio_array.dtype != np.float32:
             return audio_array.astype(np.float32)
        return audio_array
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio

def run_benchmark():
    """Loads dataset, runs Google STT, calculates CERs, response time, and proxy accuracy metrics."""

    start_time_script = datetime.now()
    print(f"Script started at: {start_time_script.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Attempting to load dataset from: {DATASET_PATH}")

    # --- Load Dataset ---
    # ... (Dataset loading code remains the same as the previous version) ...
    try:
        if not os.path.exists(DATASET_PATH) or not os.path.isdir(DATASET_PATH):
             raise FileNotFoundError(f"Dataset directory not found or is not a directory at '{DATASET_PATH}'")
        dataset = load_from_disk(DATASET_PATH)
        if len(dataset) == 0:
            print(f"Error: The loaded dataset at '{DATASET_PATH}' is empty.")
            return
        if 'transcript_whisper' not in dataset.features or 'transcript_sensevoice' not in dataset.features:
             print("Warning: Expected fields 'transcript_whisper' or 'transcript_sensevoice' not found.")
        print(f"Dataset loaded successfully. Total samples: {len(dataset)}")
    except FileNotFoundError as e:
        print(f"Error: {e}. Please ensure path is correct.")
        return
    except Exception as e:
        print(f"\n******** ERROR LOADING DATASET ********")
        print(f"Could not load dataset: {e}")
        traceback.print_exc()
        print("*************************************\n")
        return

    # --- Initialize Google Cloud Client ---
    # ... (Client initialization code remains the same) ...
    print("\nInitializing Google Cloud Speech client...")
    try:
        client = speech.SpeechClient()
        print("Speech client initialized successfully.")
    except Exception as e:
        print("\n******** ERROR INITIALIZING CLIENT ********")
        print(f"Could not initialize Google Speech client: {e}")
        traceback.print_exc()
        print("******************************************\n")
        return

    # --- Prepare for Benchmark Loop ---
    results_list = []
    total_samples_to_process = len(dataset)
    if MAX_SAMPLES is not None and MAX_SAMPLES > 0:
        total_samples_to_process = min(MAX_SAMPLES, len(dataset))
        print(f"Processing a maximum of {total_samples_to_process} samples.")

    if DISPLAY_COMPARISON_TABLE:
        print("\nComparison Table Display is ENABLED.")
    else:
         print("\nComparison Table Display is DISABLED.")

    print(f"\nStarting benchmark processing for {total_samples_to_process} samples...")

    # --- Benchmark Loop ---
    for i in tqdm(range(total_samples_to_process), desc="Benchmarking Progress"):
        item = dataset[i]
        audio_id = item.get('id', f'sample_idx_{i}')

        # --- Get Transcripts ---
        transcript_whisper = item.get('transcript_whisper', '') or ""
        transcript_sensevoice = item.get('transcript_sensevoice', '') or ""

        # --- Calculate Whisper vs SenseVoice CER ---
        cer_whisper_vs_sensevoice = jiwer.cer(transcript_whisper, transcript_sensevoice)

        # --- Initialize variables ---
        audio_prep_error = None
        api_error = None
        google_transcript = None
        api_response_time = None
        cer_google_vs_whisper = np.nan
        cer_google_vs_sensevoice = np.nan
        # <<<--- Initialize new proxy metric fields --->>>
        min_cer_google = np.nan
        max_cer_google = np.nan
        # <<<------------------------------------------>>>

        # --- Basic Data Validation & Audio Preparation ---
        # ... (Audio prep logic remains the same) ...
        audio_data = item.get('audio')
        if not audio_data or not isinstance(audio_data, dict) or \
           'array' not in audio_data or 'sampling_rate' not in audio_data:
            audio_prep_error = 'Invalid audio data structure'
        else:
            audio_array = audio_data['array']
            original_sampling_rate = audio_data['sampling_rate']
            if not isinstance(audio_array, np.ndarray):
                try:
                    audio_array = np.array(audio_array, dtype=np.float32)
                except Exception as conv_e:
                     audio_prep_error = f'Failed to convert audio array to numpy: {conv_e}'
            if not audio_prep_error and audio_array.size == 0:
                 audio_prep_error = 'Empty audio array'
            elif not audio_prep_error:
                try:
                    audio_array_resampled = resample_audio(audio_array, original_sampling_rate, TARGET_SAMPLE_RATE)
                    np.clip(audio_array_resampled, -1.0, 1.0, out=audio_array_resampled)
                    int16_array = (audio_array_resampled * 32767).astype(np.int16)
                    content = int16_array.tobytes()
                except Exception as e:
                    audio_prep_error = f'Audio processing/resampling failed: {e}'


        # --- Google STT API Call (if audio prep succeeded) ---
        if not audio_prep_error:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=TARGET_SAMPLE_RATE,
                language_code=LANGUAGE_CODE,
                enable_automatic_punctuation=True,
            )
            audio = speech.RecognitionAudio(content=content)

            try:
                start_time_api = time.perf_counter()
                response = client.recognize(config=config, audio=audio)
                end_time_api = time.perf_counter()
                api_response_time = end_time_api - start_time_api

                if response.results:
                    google_transcript = response.results[0].alternatives[0].transcript.strip()
                else:
                    google_transcript = "" # API succeeded but no speech recognized

                # --- Calculate CERs involving Google STT ---
                cer_google_vs_whisper = jiwer.cer(transcript_whisper, google_transcript)
                cer_google_vs_sensevoice = jiwer.cer(transcript_sensevoice, google_transcript)

                # <<<--- Calculate Min/Max CER for Proxy Metrics --->>>
                min_cer_google = min(cer_google_vs_whisper, cer_google_vs_sensevoice)
                max_cer_google = max(cer_google_vs_whisper, cer_google_vs_sensevoice)
                # <<<----------------------------------------------->>>

            except Exception as e:
                api_error = f'API call failed: {e}'
                # google_transcript remains None, CERs remain NaN

        # Determine final error status
        final_error = audio_prep_error or api_error

        # --- Display Per-Sample Comparison Table (Optional) ---
        if DISPLAY_COMPARISON_TABLE:
            print(f"\n--- Sample Comparison (ID: {audio_id}) ---")
            # ... (Status and transcript printing logic remains the same) ...
            status_msg = "UNKNOWN"
            google_line = "---"
            if final_error:
                status_msg = f"ERROR ({final_error})"
            elif google_transcript is not None:
                status_msg = f"OK (Time: {api_response_time:.3f}s)"
                google_line = google_transcript
            elif not audio_prep_error:
                status_msg = "SKIPPED (Unknown reason?)"

            print(f"Status  : {status_msg}")
            print(f"Google  : {google_line}")
            print(f"Whisper : {transcript_whisper}")
            print(f"SenseV. : {transcript_sensevoice}")

            # Show CERs for context
            gvw_cer_str = f"{cer_google_vs_whisper:.4f}" if not np.isnan(cer_google_vs_whisper) else "N/A"
            gvs_cer_str = f"{cer_google_vs_sensevoice:.4f}" if not np.isnan(cer_google_vs_sensevoice) else "N/A"
            wvs_cer_str = f"{cer_whisper_vs_sensevoice:.4f}" if not np.isnan(cer_whisper_vs_sensevoice) else "N/A"
            min_cer_str = f"{min_cer_google:.4f}" if not np.isnan(min_cer_google) else "N/A"
            max_cer_str = f"{max_cer_google:.4f}" if not np.isnan(max_cer_google) else "N/A"

            print(f"[Ggl vs Wsp CER: {gvw_cer_str}] [Ggl vs SnV CER: {gvs_cer_str}] [Wsp vs SnV CER: {wvs_cer_str}]")
            print(f"[Min Ggl CER: {min_cer_str}] [Max Ggl CER: {max_cer_str}]") # Show min/max
            print(f"---------------------------------------------")
        elif final_error: # Print error summary if table is off
             # ... (Error printing logic remains the same) ...
             if api_error:
                 print(f"\n******** ERROR DURING API CALL (ID: {audio_id}) ********")
                 print(api_error)
                 print("*********************************************************\n")
             elif audio_prep_error:
                 print(f"\nWarning: Skipping sample ID='{audio_id}' due to: {audio_prep_error}")


        # --- Store Results ---
        results_list.append({
            'id': audio_id,
            'error': final_error,
            'google_transcript': google_transcript if not final_error else None,
            'whisper_transcript': transcript_whisper,
            'sensevoice_transcript': transcript_sensevoice,
            'cer_google_vs_whisper': cer_google_vs_whisper, # Will be NaN if google_transcript is None
            'cer_google_vs_sensevoice': cer_google_vs_sensevoice, # Will be NaN if google_transcript is None
            'cer_whisper_vs_sensevoice': cer_whisper_vs_sensevoice,
            'min_cer_google': min_cer_google, # <<< Store min CER >>>
            'max_cer_google': max_cer_google, # <<< Store max CER >>>
            'response_time_s': api_response_time if google_transcript is not None else np.nan
        })
    # --- End Benchmark Loop ---

    # --- Process and Save Results ---
    print("\nBenchmark finished. Processing results...")

    if not results_list:
        print("No results were generated.")
        return

    results_df = pd.DataFrame(results_list)

    # --- Calculate Summary Statistics ---
    google_success_mask = results_df['error'].isna() & results_df['google_transcript'].notna()
    successful_google_results = results_df[google_success_mask].copy()

    num_processed = len(results_df)
    num_successful_api = google_success_mask.sum()
    num_errors = num_processed - num_successful_api

    print("\n--- Overall Benchmark Summary ---")
    print(f"Total Samples Attempted: {num_processed}")
    print(f"Successful Google API Calls: {num_successful_api}")
    print(f"Samples with Errors:     {num_errors}")
    # ... (Optional error breakdown) ...

    # --- Averages based on successful Google API calls ---
    if num_successful_api > 0:
        avg_cer_google_vs_whisper = successful_google_results['cer_google_vs_whisper'].mean()
        avg_cer_google_vs_sensevoice = successful_google_results['cer_google_vs_sensevoice'].mean()
        avg_cer_whisper_sensevoice_subset = successful_google_results['cer_whisper_vs_sensevoice'].mean()
        avg_response_time = successful_google_results['response_time_s'].mean()
        std_dev_response_time = successful_google_results['response_time_s'].std()
        median_response_time = successful_google_results['response_time_s'].median()

        # <<<--- Calculate Proxy Accuracy & Margin --->>>
        avg_min_cer_google = successful_google_results['min_cer_google'].mean()
        avg_max_cer_google = successful_google_results['max_cer_google'].mean()
        pseudo_accuracy = 1.0 - avg_min_cer_google
        reference_disagreement_margin = avg_max_cer_google - avg_min_cer_google
        # <<<---------------------------------------->>>

        print("---------------------------------------------")
        print("Averages based on successful Google API calls:")
        print(f"  Avg CER Google vs Whisper:   {avg_cer_google_vs_whisper:.4f}")
        print(f"  Avg CER Google vs SenseVoice:{avg_cer_google_vs_sensevoice:.4f}")
        print(f"  Avg CER Whisper vs SenseVoice:{avg_cer_whisper_sensevoice_subset:.4f} (for this subset)")
        print("---")
        print(f"  Average API Response Time: {avg_response_time:.4f} seconds")
        print(f"  Median API Response Time:  {median_response_time:.4f} seconds")
        print(f"  Std Dev Response Time:     {std_dev_response_time:.4f} seconds")
        print("--- Proxy Metrics (Relative to References) ---")
        print(f"  Avg Min CER (Google vs Closer Ref): {avg_min_cer_google:.4f}")
        print(f"  Avg Max CER (Google vs Further Ref):{avg_max_cer_google:.4f}")
        print(f"  Pseudo-Accuracy (1 - Avg Min CER):  {pseudo_accuracy:.4f}")
        print(f"  Reference Disagreement Margin:      {reference_disagreement_margin:.4f}")
        print("     (Note: Higher margin means more disagreement between Whisper/SenseVoice relative to Google's output)")
        print("---------------------------------------------")
    else:
         print("---------------------------------------------")
         print("No successful Google API calls to calculate Google-related average statistics.")
         print("---------------------------------------------")

    # --- Average Whisper vs SenseVoice CER over all processed samples ---
    if num_processed > 0:
        avg_cer_whisper_sensevoice_all = results_df['cer_whisper_vs_sensevoice'].mean(skipna=True)
        print(f"Avg CER Whisper vs SenseVoice (All Samples): {avg_cer_whisper_sensevoice_all:.4f}")
        print("---------------------------------------------")
    elif num_successful_api == 0: # If nothing was processed at all
        print("No samples processed to calculate reference CERs.")
        print("---------------------------------------------")

    # --- Save Detailed Results to CSV ---
    try:
        output_dir = os.path.dirname(OUTPUT_CSV_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # Add new columns to float formatting if needed, though default should be fine
        results_df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8', float_format='%.6f')
        print(f"\nDetailed results saved to: {OUTPUT_CSV_FILE}")
    except Exception as e:
        print(f"\nError saving results to CSV '{OUTPUT_CSV_FILE}': {e}")

    end_time_script = datetime.now()
    print(f"\nScript finished at: {end_time_script.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total script execution time: {end_time_script - start_time_script}")


if __name__ == "__main__":
    # Check for credentials before running
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("! Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set.  !")
        print("! The script will likely fail to authenticate with Google Cloud.         !")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        # import sys
        # sys.exit("Exiting due to missing Google credentials.")

    run_benchmark()