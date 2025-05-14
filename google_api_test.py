import os
import traceback
import numpy as np
import librosa
from google.cloud import speech

AUDIO_FILE_PATH = "sampled_testcase/TC-1/chunk_8/0Ejp6yyU5bo_noisy_0_audio_92.mp3"
TARGET_SAMPLE_RATE = 16000
LANGUAGE_CODE = "yue-Hant-HK"

def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """Resamples audio using librosa."""
    if current_sr == target_sr:
        return audio_array
    print(f"Resampling from {current_sr} Hz to {target_sr} Hz...")
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)

    if not audio_array.flags['C_CONTIGUOUS']:
        audio_array = np.ascontiguousarray(audio_array)

    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio

def run_google_api_test():
    """Loads one audio file directly and runs simple sync recognition."""

    print(f"Attempting to load audio file from: {AUDIO_FILE_PATH}")

    try:
        audio_array, original_sampling_rate = librosa.load(AUDIO_FILE_PATH, sr=None, mono=True)

        audio_id = os.path.basename(AUDIO_FILE_PATH)
        print(f"Loaded audio file. ID='{audio_id}', Original SR={original_sampling_rate} Hz")

        if audio_array.size == 0:
            print("Error: Audio array loaded from file is empty.")
            return

    except FileNotFoundError:
        print(f"Error: Audio file not found at '{AUDIO_FILE_PATH}'.")
        return
    except Exception as e:
        print(f"\n******** ERROR LOADING/PREPARING AUDIO FILE ********")
        print(f"Could not load or prepare audio file: {e}")
        print("---------------------------------------------------")
        traceback.print_exc()
        print("***************************************************\n")
        return

    try:
        client = speech.SpeechClient()
        print("Speech client initialized successfully.")
    except Exception as e:
        print("\n******** ERROR INITIALIZING CLIENT ********")
        print(f"Could not initialize Google Speech client: {e}")
        print("Please ensure credentials are set correctly (GOOGLE_APPLICATION_CREDENTIALS).")
        print("------------------------------------------")
        traceback.print_exc()
        print("******************************************\n")
        return

    try:
        print("Preparing audio content for synchronous API call...")
        if original_sampling_rate != TARGET_SAMPLE_RATE:
            audio_array_resampled = resample_audio(audio_array, original_sampling_rate, TARGET_SAMPLE_RATE)
        else:
            audio_array_resampled = audio_array
            if audio_array_resampled.dtype != np.float32:
                audio_array_resampled = audio_array_resampled.astype(np.float32)

        np.clip(audio_array_resampled, -1.0, 1.0, out=audio_array_resampled)
        int16_array = (audio_array_resampled * 32767).astype(np.int16)
        content = int16_array.tobytes()
        print(f"Audio prepared: {len(content)} bytes, Target Rate={TARGET_SAMPLE_RATE} Hz")

    except Exception as e:
        print(f"\n******** ERROR PROCESSING AUDIO ARRAY ********")
        print(f"Could not resample or convert audio: {e}")
        print("-------------------------------------------")
        traceback.print_exc()
        print("*******************************************\n")
        return

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=TARGET_SAMPLE_RATE,
        language_code=LANGUAGE_CODE,
        enable_automatic_punctuation=True,
    )
    audio = speech.RecognitionAudio(content=content)

    print("\nSending request to Google Cloud Speech API...")
    try:
        response = client.recognize(config=config, audio=audio)
        print("API call successful.")

        if not response.results:
            print("\nAPI returned no results (no speech recognized?).")
            return

        print("\n--- Transcription Results ---")
        for result in response.results:
            print(f"Transcript: {result.alternatives[0].transcript}")
            if result.alternatives[0].confidence:
                 print(f"Confidence: {result.alternatives[0].confidence:.4f}")
            else:
                print("Confidence: Not available")
        print("---------------------------\n")

    except Exception as e:
        print(f"\n******** ERROR DURING API CALL ********")
        print(f"API call failed: {e}")
        print("Check your API quota, network connection, and ensure the language code is correct.")
        print("--- Traceback ---")
        traceback.print_exc()
        print("-----------------")
        print("*************************************\n")

if __name__ == "__main__":
    run_google_api_test()