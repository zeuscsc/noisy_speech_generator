import glob
import os
from pydub import AudioSegment

def overlay_audio_tracks(folder_path,
                         output_filename="combined_audio.mp3",
                         load_first_n_seconds=None): 
    """
    Finds all MP3 files in a given folder structure, loads only an initial
    segment of each (if specified), determines the shortest audio track among
    the loaded segments, and overlays all tracks (trimmed to that shortest
    length) into a single output file.

    Args:
        folder_path (str): The root path to search for audio files.
        output_filename (str): The name of the output combined audio file.
        load_first_n_seconds (int, optional): The number of seconds to load
                                             from the beginning of each audio file.
                                             If None, loads the entire file (original behavior).
    """
    search_pattern = os.path.join(folder_path, '**', '*.mp3')
    audio_files = glob.glob(os.path.normpath(search_pattern), recursive=True)


    if not audio_files:
        print(f"No MP3 files found matching pattern: {search_pattern}")
        return

    print(f"Found {len(audio_files)} MP3 files.")
    for f_path_check in audio_files:
        print(f"  - Detected: {f_path_check}")


    min_duration_ms = float('inf')
    loaded_segments = []

    print(f"\nLoading audio files...")
    if load_first_n_seconds:
        print(f"Will load only the first {load_first_n_seconds} seconds of each track.")

    for f_path in audio_files:
        try:
            if load_first_n_seconds is not None:
                audio = AudioSegment.from_file(f_path, format="mp3", duration=load_first_n_seconds)
            else:
                audio = AudioSegment.from_file(f_path, format="mp3") 
            
            loaded_segments.append(audio)
            if len(audio) < min_duration_ms:
                min_duration_ms = len(audio)
            print(f"Loaded: {os.path.basename(f_path)}, Loaded Duration: {len(audio) / 1000.0:.2f}s")
        except Exception as e:
            print(f"Could not process file {f_path}: {e}")
            continue

    if not loaded_segments:
        print("No audio files could be loaded successfully.")
        return

    if min_duration_ms == float('inf') or min_duration_ms == 0:
        print("Could not determine a valid minimum duration (perhaps no valid audio files or all loaded segments are empty?).")
        print(f"Min duration was: {min_duration_ms}")
        return

    print(f"\nShortest effective track duration for overlay: {min_duration_ms / 1000.0:.2f} seconds.")
    print("Overlaying tracks (trimmed to this shortest effective duration)...")

    combined_audio = loaded_segments[0][:min_duration_ms]

    for i in range(1, len(loaded_segments)):
        segment_to_overlay = loaded_segments[i][:min_duration_ms]
        combined_audio = combined_audio.overlay(segment_to_overlay)
        print(f"Overlayed track {i+1}/{len(loaded_segments)}")

    try:
        combined_audio.export(output_filename, format="mp3")
        print(f"\nSuccessfully combined audio saved as: {output_filename}")
    except Exception as e:
        print(f"Error exporting combined audio: {e}")

if __name__ == "__main__":
    dataset_folder = os.path.abspath(r"dataset_background_noise")
    output_file = "final_mixed_audio_limited.mp3"
    initial_load_duration = 30 * 60
    print(f"Processing audio from folder: {dataset_folder}")
    if not os.path.isdir(dataset_folder):
        print(f"ERROR: The specified folder does not exist: {dataset_folder}")
        print("Please check the 'dataset_folder' variable in the script.")
    else:
        if initial_load_duration:
            print(f"Limiting initial load of each file to {initial_load_duration} seconds.")
        else:
            print("Attempting to load full duration of each file.")
        overlay_audio_tracks(dataset_folder, output_file, load_first_n_seconds=initial_load_duration)