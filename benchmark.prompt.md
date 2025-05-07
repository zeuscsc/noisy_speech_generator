I would like to create a brenchmark test for Google STT with Cantonese Speech Audio dataset.
I will need to test it accuracy and response speed. For accuracy you can reference from the dataset:transcript_whisper and transcript_sensevoice.

Here is what i have for loading the audios from dataset and pass it to Google STT and it works.
I would like you to help me finish the brenchmark test codes.
import os
import traceback
import numpy as np
import librosa
from datasets import load_from_disk
from google.cloud import speech


DATASET_PATH = "streamed_subset"
TARGET_SAMPLE_RATE = 16000
LANGUAGE_CODE = "yue-Hant-HK"


def resample_audio(audio_array: np.ndarray, current_sr: int, target_sr: int) -> np.ndarray:
    """Resamples audio using librosa."""
    if current_sr == target_sr:
        return audio_array
    print(f"Resampling from {current_sr} Hz to {target_sr} Hz...")
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)

    resampled_audio = librosa.resample(audio_array, orig_sr=current_sr, target_sr=target_sr)
    return resampled_audio

def run_simple_test_from_dataset():
    """Loads one sample from dataset and runs simple sync recognition."""

    print(f"Attempting to load dataset from: {DATASET_PATH}")

    try:
        dataset = load_from_disk(DATASET_PATH)
        if len(dataset) == 0:
            print("Error: The loaded dataset is empty.")
            return
        item = dataset[0]
        audio_id = item.get('id', 'sample_idx_0')
        print(f"Loaded dataset. Using first sample: ID='{audio_id}'")

        audio_data = item.get('audio')
        if not audio_data or not isinstance(audio_data, dict) or \
           'array' not in audio_data or 'sampling_rate' not in audio_data:
            print("Error: First dataset sample has missing or invalid audio data structure.")
            return

        audio_array = audio_data['array']
        original_sampling_rate = audio_data['sampling_rate']

        if not isinstance(audio_array, np.ndarray):
            audio_array = np.array(audio_array)

        if audio_array.size == 0:
            print("Error: Audio array in the first sample is empty.")
            return

    except FileNotFoundError:
        print(f"Error: Dataset directory not found at '{DATASET_PATH}'.")
        return
    except Exception as e:
        print(f"\n******** ERROR LOADING/PREPARING DATASET ITEM ********")
        print(f"Could not load or prepare dataset item: {e}")
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
            print(f"Confidence: {result.alternatives[0].confidence:.4f}")
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
    run_simple_test_from_dataset()