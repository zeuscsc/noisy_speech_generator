import ffmpeg
import os
import glob
import multiprocessing

# get_media_duration function remains the same
def get_media_duration(file_path):
    """Gets the duration of a media file in seconds using ffprobe."""
    try:
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except ffmpeg.Error as e:
        print(f"Error probing {file_path}: {e.stderr.decode('utf8') if e.stderr else 'Unknown error'}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while probing {file_path}: {e}")
        return None

# combine_audio_with_noise function remains the same
def combine_audio_with_noise(video_path, noise_path, output_path, noise_level_factor, video_duration_seconds):
    """
    Combines audio from a video with background noise from a single specified noise file
    at a given level. This function will be executed by worker processes.
    """
    video_filename_base = os.path.splitext(os.path.basename(video_path))[0]
    noise_filename_display = os.path.splitext(os.path.basename(noise_path))[0] if noise_path else "NoNoise"
    process_id = os.getpid()

    # Ensure the directory for the output_path exists (it should be created in main, but good for robustness if function is called directly)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if os.path.exists(output_path):
        print(f"[PID:{process_id}] Output file {output_path} already exists. Skipping processing in worker. (This should ideally be caught in main)")
        return

    print(f"[PID:{process_id}] Processing: Video '{video_filename_base}', Noise '{noise_filename_display}', Level: {noise_level_factor*100:.0f}%")

    try:
        video_input = ffmpeg.input(video_path)
        video_audio = video_input['a']

        final_audio_stream = video_audio

        if noise_level_factor > 0.0:
            if not noise_path or not os.path.exists(noise_path):
                print(f"[PID:{process_id}] Error: Noise file '{noise_path}' not found for video '{video_filename_base}'. Outputting original audio for this level.")
            else:
                noise_input = ffmpeg.input(noise_path, stream_loop=-1)
                looped_noise_audio = noise_input['a']

                current_speech_weight = "1"

                final_audio_stream = ffmpeg.filter(
                    [video_audio, looped_noise_audio],
                    'amix',
                    inputs=2,
                    duration='first',
                    dropout_transition=0,
                    weights=f"{current_speech_weight} {noise_level_factor}"
                )
        else:
            print(f"[PID:{process_id}] Applying 0% noise for video '{video_filename_base}'. Output will be original audio.")
        stream = ffmpeg.output(
            final_audio_stream,
            output_path,
            acodec='libmp3lame',
            audio_bitrate='192k',
            t=video_duration_seconds
        )

        ffmpeg.run(stream, overwrite_output=True, quiet=True)
        print(f"[PID:{process_id}] Successfully created: {output_path}")

    except ffmpeg.Error as e:
        print(f"[PID:{process_id}] FFmpeg Error for video '{video_filename_base}', noise '{noise_filename_display}', level {noise_level_factor*100:.0f}%:")
        stderr = e.stderr.decode('utf8') if e.stderr else "No stderr output."
        print(f"[PID:{process_id}] Stderr: {stderr}")
    except Exception as e:
        print(f"[PID:{process_id}] Unexpected error with video '{video_filename_base}', noise '{noise_filename_display}', level {noise_level_factor*100:.0f}%: {e}")


def main():
    video_dataset_root = "dataset"
    single_master_noise_file = "final_mixed_audio_limited.mp3"
    # This is the base directory. Subdirectories for each video_id will be created inside this.
    output_audio_dir_base = "output_noisy_audio"
    noise_levels_percentage = [0, 25, 50, 75, 100, 150, 200]

    # This initial creation is for the base directory.
    # Specific subdirectories will be created per video_id.
    os.makedirs(output_audio_dir_base, exist_ok=True)

    if any(level > 0 for level in noise_levels_percentage):
        if not os.path.exists(single_master_noise_file):
            print(f"Error: The master noise file '{single_master_noise_file}' was not found.")
            print("Processing will only generate 0% noise files if 0% is in levels, or no files otherwise.")

    print("Discovering video files...")
    # Assuming video files are in format: dataset/{youtube_video_id}/video.mp4
    video_files = glob.glob(os.path.join(video_dataset_root, "*", "*.mp4"))

    if not video_files:
        print(f"No video files found in '{os.path.join(video_dataset_root, '*', '*.mp4')}'")
        return

    print(f"Found {len(video_files)} video files.")
    # master_noise_id is no longer needed for the new output path format
    # master_noise_id = os.path.splitext(os.path.basename(single_master_noise_file))[0]

    tasks_to_process = []
    skipped_tasks_count = 0
    print("Preparing tasks for parallel execution...")
    for video_file_path in video_files:
        # This assumes the parent directory of the video file is the {youtube_video_id}
        video_id = os.path.basename(os.path.dirname(video_file_path))
        video_duration = get_media_duration(video_file_path)

        if video_duration is None:
            print(f"Skipping video {video_file_path} (in main process) due to error in getting duration.")
            continue

        # ---- MODIFICATION START ----
        # Create the output directory specific to this video_id
        # This will be output_noisy_audio/{youtube_video_id}/
        video_specific_output_dir = os.path.join(output_audio_dir_base, video_id)
        os.makedirs(video_specific_output_dir, exist_ok=True)
        # ---- MODIFICATION END ----

        for level_percent in noise_levels_percentage:
            noise_factor = level_percent / 100.0

            # ---- MODIFICATION START ----
            # New output filename format: noisy_{percent}.mp3
            output_filename = f"noisy_{level_percent}.mp3"
            # New full output path: output_noisy_audio/{youtube_video_id}/noisy_{percent}.mp3
            full_output_path = os.path.join(video_specific_output_dir, output_filename)
            # ---- MODIFICATION END ----

            if os.path.exists(full_output_path):
                print(f"Output file {full_output_path} already exists. Skipping task.")
                skipped_tasks_count += 1
                continue

            current_noise_path_for_task = single_master_noise_file if noise_factor > 0.0 else None

            tasks_to_process.append((
                video_file_path,
                current_noise_path_for_task,
                full_output_path,
                noise_factor,
                video_duration
            ))

    if skipped_tasks_count > 0:
        print(f"Skipped {skipped_tasks_count} tasks because their output files already existed.")

    if not tasks_to_process:
        if skipped_tasks_count > 0:
            print("No new tasks to process (all were skipped or no videos found/valid). Exiting.")
        else:
            print("No tasks to process based on discovered files and settings. Exiting.")
        return

    print(f"Prepared {len(tasks_to_process)} new audio mixing tasks.")

    num_processes = max(1, os.cpu_count() - 1) if os.cpu_count() and os.cpu_count() > 1 else 1
    print(f"Starting parallel processing with {num_processes} worker processes...")

    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(combine_audio_with_noise, tasks_to_process)

    print("\nParallel processing complete.")

if __name__ == "__main__":
    main()