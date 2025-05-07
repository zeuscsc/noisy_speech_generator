import os
import shutil
from pydub import AudioSegment
import glob
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time

# --- Worker function for audio processing ---
def process_single_audio_file(audio_file_path, output_base_dir, chunk_sizes_seconds):
    """
    Processes a single audio file: loads, chunks, and saves it.
    Skips if chunks already exist for all specified sizes for this audio's noisy level.
    """
    try:
        audio_filename = os.path.basename(audio_file_path)
        noisy_level_folder_name = os.path.splitext(audio_filename)[0]
        youtube_video_id = os.path.basename(os.path.dirname(audio_file_path))

        if not youtube_video_id:
            print(f"Could not determine YouTube Video ID for: {audio_file_path} in PID {os.getpid()}. Skipping.")
            return None
        if not noisy_level_folder_name:
            print(f"Could not determine noisy level for: {audio_file_path} in PID {os.getpid()}. Skipping.")
            return None

        # --- Check if already chunked ---
        all_chunks_exist_for_this_noisy_level = True
        if not chunk_sizes_seconds: # Should not happen with current setup but good for robustness
            all_chunks_exist_for_this_noisy_level = False
        else:
            for cs_s in chunk_sizes_seconds:
                # Path: chunked_dataset/{youtube_video_id}/chunk_{chunk_size_s}/{noisy_level_folder_name}/
                target_chunk_dir = os.path.join(output_base_dir, youtube_video_id, f"chunk_{cs_s}", noisy_level_folder_name)
                if not (os.path.isdir(target_chunk_dir) and os.listdir(target_chunk_dir)):
                    all_chunks_exist_for_this_noisy_level = False
                    break
        
        if all_chunks_exist_for_this_noisy_level:
            # print(f"[PID {os.getpid()}] Audio for {youtube_video_id}/{noisy_level_folder_name} already chunked. Skipping audio processing.")
            return youtube_video_id # Return ID for transcript check consistency

        # --- If not all chunks exist, proceed with processing ---
        # print(f"[PID {os.getpid()}] Processing: {audio_file_path} (ID: {youtube_video_id}, Noise: {noisy_level_folder_name})")

        video_id_base_output_dir = os.path.join(output_base_dir, youtube_video_id)
        os.makedirs(video_id_base_output_dir, exist_ok=True)

        try:
            audio = AudioSegment.from_mp3(audio_file_path)
        except Exception as e:
            print(f"Error loading audio file {audio_file_path} in PID {os.getpid()}: {e}. Skipping.")
            return youtube_video_id

        for chunk_size_s in chunk_sizes_seconds:
            # Output: chunked_dataset/{youtube_video_id}/chunk_{chunk_size_s}/
            chunk_size_specific_dir = os.path.join(video_id_base_output_dir, f"chunk_{chunk_size_s}")
            # Output: chunked_dataset/{youtube_video_id}/chunk_{chunk_size_s}/{noisy_level}/
            noisy_level_specific_chunk_output_dir = os.path.join(chunk_size_specific_dir, noisy_level_folder_name)
            os.makedirs(noisy_level_specific_chunk_output_dir, exist_ok=True)

            chunk_length_ms = chunk_size_s * 1000
            for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
                end_ms = start_ms + chunk_length_ms
                chunk = audio[start_ms:end_ms]
                chunk_filename = f"audio_{i}.mp3"
                chunk_filepath = os.path.join(noisy_level_specific_chunk_output_dir, chunk_filename)
                try:
                    chunk.export(chunk_filepath, format="mp3")
                except Exception as e:
                    print(f"Error saving chunk {chunk_filepath} in PID {os.getpid()}: {e}")
        return youtube_video_id
    except Exception as e:
        print(f"Unhandled error processing {audio_file_path} in PID {os.getpid()}: {e}")
        try:
            return os.path.basename(os.path.dirname(audio_file_path)) # Attempt to return ID if path known
        except: #pylint: disable=bare-except
            return None


# --- Worker function for transcript copying ---
def copy_single_transcript(video_id, base_input_transcript_dir, output_base_dir):
    """
    Copies a transcript file for the given video_id.
    Searches for .whisper.auto.vtt, then any .vtt file.
    """
    try:
        transcript_dir_for_video_id = os.path.join(base_input_transcript_dir, video_id)
        if not os.path.isdir(transcript_dir_for_video_id):
            # This specific message is fine, no need to print if it's a common case of no transcript
            # print(f"Transcript directory not found for {video_id} at {transcript_dir_for_video_id}.")
            return video_id, False # False indicates transcript not found/copied

        found_transcript_filename = None
        # Priority 1: Specific pattern
        for f_name in sorted(os.listdir(transcript_dir_for_video_id)): # sorted for consistent choice if multiple
            if f_name.endswith(".whisper.auto.vtt"):
                found_transcript_filename = f_name
                break
        
        # Priority 2: Any .vtt file
        if not found_transcript_filename:
            for f_name in sorted(os.listdir(transcript_dir_for_video_id)):
                if f_name.endswith(".vtt"):
                    found_transcript_filename = f_name
                    break
        
        # Add more fallbacks here if needed (e.g., .srt, .txt)

        if not found_transcript_filename:
            # print(f"No suitable transcript file (.whisper.auto.vtt or .vtt) found for {video_id} in {transcript_dir_for_video_id}.")
            return video_id, False

        transcript_source_path = os.path.join(transcript_dir_for_video_id, found_transcript_filename)
        
        # Output path: chunked_dataset/{youtube_video_id}/{found_transcript_filename}
        transcript_dest_dir = os.path.join(output_base_dir, video_id)
        os.makedirs(transcript_dest_dir, exist_ok=True)
        transcript_dest_path = os.path.join(transcript_dest_dir, found_transcript_filename)

        # Avoid re-copying if already there (optional, shutil.copy2 might overwrite or error depending on OS and perms)
        if os.path.exists(transcript_dest_path) and os.path.getsize(transcript_dest_path) == os.path.getsize(transcript_source_path):
            # print(f"[Thread] Transcript {found_transcript_filename} already exists for {video_id}. Skipping copy.")
            return video_id, True


        shutil.copy2(transcript_source_path, transcript_dest_path)
        # print(f"[Thread] Copied transcript {found_transcript_filename} for {video_id} to {transcript_dest_path}")
        return video_id, True
    except Exception as e:
        print(f"Error copying transcript for {video_id}: {e}")
        return video_id, False

# --- Main processing function ---
def create_chunked_dataset_parallel(base_input_audio_dir, base_input_transcript_dir, output_base_dir, num_audio_processes=None, num_transcript_threads=None):
    start_time = time.time()

    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir, exist_ok=True)
        print(f"Created base output directory: {output_base_dir}")

    chunk_sizes_seconds = [8, 30, 60]

    audio_files = glob.glob(os.path.join(base_input_audio_dir, "*", "*.mp3"))
    if not audio_files:
        print(f"No MP3 files found in subdirectories of {base_input_audio_dir}. Exiting.")
        return

    print(f"Found {len(audio_files)} audio files to potentially process.")

    print(f"\n--- Starting Parallel Audio Chunking (using up to {num_audio_processes or os.cpu_count()} processes) ---")
    audio_worker_func = partial(process_single_audio_file,
                                output_base_dir=output_base_dir,
                                chunk_sizes_seconds=chunk_sizes_seconds)

    processed_video_ids_for_transcripts = set()
    audio_processing_results = [] # To store (file_path, success_boolean_or_None)
    
    with multiprocessing.Pool(processes=num_audio_processes) as pool:
        # Each call to audio_worker_func returns a youtube_video_id (str) or None
        results_video_ids = pool.map(audio_worker_func, audio_files)

    skipped_audio_count = 0
    actually_processed_audio_count = 0 # Files for which chunking was attempted (not skipped)
    
    for i, video_id_result in enumerate(results_video_ids):
        original_audio_file = audio_files[i]
        if video_id_result:
            processed_video_ids_for_transcripts.add(video_id_result)
            # Check if it was skipped by checking original logic for skipping
            # This is a bit of a re-check, ideally worker returns more info
            # For now, assume if ID is returned, it was either processed or intended for transcript check
            # Let's refine this logic. The worker returns ID even if skipped.
            # We need a way to distinguish skipped from processed.
            # The print log from worker is the main indicator now.
            # A simple count: if an ID is returned, we consider it "handled" for audio part.
        # The current logic doesn't easily distinguish skipped from processed from worker's return alone.
        # The print "(already chunked)" from the worker indicates skipped files.
        # We'll rely on the set `processed_video_ids_for_transcripts` for transcript step.
        
    # A more accurate count of processed vs skipped would involve changing worker return value
    # or re-evaluating the skip condition here.
    # For now, the number of unique IDs is `len(processed_video_ids_for_transcripts)`.

    print(f"--- Finished Audio Chunking Phase ---")
    print(f"Collected {len(processed_video_ids_for_transcripts)} unique video IDs for transcript processing based on audio file discovery.")

    if not processed_video_ids_for_transcripts:
        print("No video IDs eligible for transcript processing. Skipping transcript copying.")
    elif not os.path.exists(base_input_transcript_dir):
        print(f"Transcript directory {base_input_transcript_dir} does not exist. Skipping transcript copying.")
    else:
        print(f"\n--- Starting Parallel Transcript Copying (using up to {num_transcript_threads or (os.cpu_count() * 2)} threads) for {len(processed_video_ids_for_transcripts)} unique video IDs ---")
        transcript_worker_func = partial(copy_single_transcript,
                                         base_input_transcript_dir=base_input_transcript_dir,
                                         output_base_dir=output_base_dir)

        successful_copies = 0
        failed_or_missing_copies = 0
        with ThreadPoolExecutor(max_workers=num_transcript_threads) as executor:
            future_results = [executor.submit(transcript_worker_func, video_id) for video_id in processed_video_ids_for_transcripts]
            for future in future_results:
                _video_id, success = future.result() # result() will block until future is done
                if success:
                    successful_copies += 1
                else:
                    failed_or_missing_copies += 1
        
        print(f"--- Finished Transcript Copying ---")
        print(f"Successfully copied {successful_copies} transcripts.")
        if failed_or_missing_copies > 0:
            print(f"Failed to copy or transcript not found for {failed_or_missing_copies} video IDs.")

    end_time = time.time()
    print(f"\n--- Total Processing Complete in {end_time - start_time:.2f} seconds ---")


# --- Configuration ---
current_working_directory = os.getcwd()
input_audio_directory = os.path.join(current_working_directory, "output_noisy_audio")
input_transcript_directory = os.path.join(current_working_directory, "dataset")
output_chunked_directory = os.path.join(current_working_directory, "chunked_dataset")


# --- Run the process ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

    NUM_AUDIO_PROCESSES = None 
    NUM_TRANSCRIPT_THREADS = None 

    print(f"Starting dataset processing at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input Audio Directory: {input_audio_directory}")
    print(f"Input Transcript Directory: {input_transcript_directory}")
    print(f"Output Chunked Directory: {output_chunked_directory}")

    if not os.path.isdir(input_audio_directory):
        print(f"ERROR: Input audio directory not found: {input_audio_directory}")
        exit()
    if not os.path.isdir(input_transcript_directory): # Still check, as it's expected by the transcript copy part
        print(f"WARNING: Input transcript directory not found: {input_transcript_directory}. Transcript copying will be skipped for all files.")
        # Allow to continue for audio-only processing if desired, but current logic will just print "skipping"
        # For full skip, the create_chunked_dataset_parallel would need modification or a flag.

    create_chunked_dataset_parallel(
        input_audio_directory,
        input_transcript_directory,
        output_chunked_directory,
        num_audio_processes=NUM_AUDIO_PROCESSES,
        num_transcript_threads=NUM_TRANSCRIPT_THREADS
    )