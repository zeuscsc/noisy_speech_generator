import os
import random
import shutil

def find_transcript_file(video_id_level_path, video_id):
    if not os.path.isdir(video_id_level_path):
        return None

    files_in_dir = [f for f in os.listdir(video_id_level_path) if os.path.isfile(os.path.join(video_id_level_path, f))]

    exact_match_pattern = f"{video_id}.whisper.auto.vtt"
    if exact_match_pattern in files_in_dir:
        return os.path.join(video_id_level_path, exact_match_pattern)

    potential_files = []
    for fname in files_in_dir:
        if fname.startswith(video_id) and ".whisper" in fname and fname.endswith(".vtt"):
            potential_files.append(fname)
    if potential_files:
        return os.path.join(video_id_level_path, sorted(potential_files)[0])

    potential_files = []
    for fname in files_in_dir:
        if fname.startswith(video_id) and fname.endswith(".vtt"):
            potential_files.append(fname)
    if potential_files:
        return os.path.join(video_id_level_path, sorted(potential_files)[0])

    potential_files = []
    common_text_extensions = (".vtt", ".srt", ".txt")
    for fname in files_in_dir:
        if fname.startswith(video_id) and ".whisper" in fname and fname.endswith(common_text_extensions):
            potential_files.append(fname)
    if potential_files:
        for ext_priority in common_text_extensions:
            for pfname in sorted(potential_files):
                if pfname.endswith(ext_priority):
                    return os.path.join(video_id_level_path, pfname)
        return os.path.join(video_id_level_path, sorted(potential_files)[0]) 

    potential_files = []
    for fname in files_in_dir:
        if fname.startswith(video_id) and fname.endswith(".srt"):
            potential_files.append(fname)
    if potential_files:
        return os.path.join(video_id_level_path, sorted(potential_files)[0])

    potential_files = []
    for fname in files_in_dir:
        if fname.startswith(video_id) and fname.endswith(".txt"):
            potential_files.append(fname)
    if potential_files:
        return os.path.join(video_id_level_path, sorted(potential_files)[0])
        
    return None

def analyze_and_extract_audios(base_dataset_path, new_dataset_folder_path):
    source_dataset_dir = base_dataset_path
    output_dataset_dir = new_dataset_folder_path

    chunk_categories = set()
    audio_files_by_category = {}

    print(f"Scanning '{source_dataset_dir}' to identify chunk categories and audio files...")

    if not os.path.isdir(source_dataset_dir):
        print(f"Error: Source directory '{source_dataset_dir}' not found.")
        return

    video_id_folders = [d for d in os.listdir(source_dataset_dir) if os.path.isdir(os.path.join(source_dataset_dir, d))]

    for video_id in video_id_folders:
        video_id_path = os.path.join(source_dataset_dir, video_id)
        
        potential_chunk_folders = [d for d in os.listdir(video_id_path) 
                                     if os.path.isdir(os.path.join(video_id_path, d)) and d.startswith("chunk_")]
        
        for chunk_folder_name in potential_chunk_folders:
            chunk_categories.add(chunk_folder_name)
            if chunk_folder_name not in audio_files_by_category:
                audio_files_by_category[chunk_folder_name] = []
            
            chunk_folder_path = os.path.join(video_id_path, chunk_folder_name)
            noisy_level_folders = [d for d in os.listdir(chunk_folder_path) 
                                     if os.path.isdir(os.path.join(chunk_folder_path, d)) and d.startswith("noisy_")] # Assuming your noisy folders also start with "noisy_"
            
            for noisy_folder_name in noisy_level_folders:
                noisy_folder_path = os.path.join(chunk_folder_path, noisy_folder_name)
                
                for filename in os.listdir(noisy_folder_path):
                    if filename.startswith("audio_") and filename.endswith(".mp3"):
                        audio_full_path = os.path.join(noisy_folder_path, filename)
                        audio_files_by_category[chunk_folder_name].append({
                            'path': audio_full_path,
                            'video_id': video_id,
                            'noisy_folder': noisy_folder_name,
                            'filename': filename
                        })

    if not chunk_categories:
        print(f"No chunk categories (subdirectories starting with 'chunk_') found in '{source_dataset_dir}'.")
        return

    print("\n--- Discovered Chunk Types (Sizes) ---")
    sorted_categories = sorted(list(chunk_categories))
    for category in sorted_categories:
        count = len(audio_files_by_category.get(category, []))
        print(f"- Type: {category} (Found {count} audio files)")

    try:
        os.makedirs(output_dataset_dir, exist_ok=True)
        print(f"\nEnsured base output directory exists: '{output_dataset_dir}'")
    except OSError as e:
        print(f"Error: Could not create base output directory {output_dataset_dir}: {e}")
        return

    for category in sorted_categories:
        try:
            os.makedirs(os.path.join(output_dataset_dir, category), exist_ok=True)
        except OSError as e:
            print(f"Error: Could not create subdirectory for {category}: {e}")
            continue

    print("\n--- Selecting and Copying Audio Files and Transcripts ---")
    files_to_select_per_category = 50

    for category in sorted_categories:
        print(f"\nProcessing category: {category}...")
        target_category_dir = os.path.join(output_dataset_dir, category)
        
        all_audios_for_category = audio_files_by_category.get(category, [])
        
        if not all_audios_for_category:
            print(f"   No audio files were found for '{category}'. Skipping.")
            continue

        if len(all_audios_for_category) >= files_to_select_per_category:
            selected_audios = random.sample(all_audios_for_category, files_to_select_per_category)
            print(f"   Randomly selected {files_to_select_per_category} audio files for '{category}'.")
        else:
            selected_audios = all_audios_for_category
            print(f"   Warning: Only {len(all_audios_for_category)} audio files available for '{category}'. Selecting all of them.")

        copied_audio_count = 0
        for audio_info in selected_audios:
            original_audio_path = audio_info['path']
            video_id = audio_info['video_id']
            noisy_folder = audio_info['noisy_folder']
            original_audio_filename = audio_info['filename']

            dest_audio_filename = f"{video_id}_{noisy_folder}_{original_audio_filename}"
            target_audio_path = os.path.join(target_category_dir, dest_audio_filename)

            try:
                shutil.copy2(original_audio_path, target_audio_path)
                copied_audio_count += 1
            except Exception as e:
                print(f"     Error copying audio {original_audio_path} to {target_audio_path}: {e}")
                continue 
            
            original_audio_dir = os.path.dirname(original_audio_path)
            audio_basename_no_ext = os.path.splitext(original_audio_filename)[0] # e.g., "audio_0"
            
            copied_transcripts_for_this_audio = 0
            # Expected suffix for transcript files, e.g., "_audio_0.vtt"
            expected_transcript_suffix = f"_{audio_basename_no_ext}.vtt" 

            for potential_transcript_file in os.listdir(original_audio_dir):
                if potential_transcript_file.endswith(expected_transcript_suffix) and \
                   os.path.isfile(os.path.join(original_audio_dir, potential_transcript_file)):
                    
                    original_transcript_full_path = os.path.join(original_audio_dir, potential_transcript_file)
                    
                    # Construct new destination transcript filename
                    # It will be: {video_id}_{noisy_folder}_{original_transcript_filename_from_chunk_dir}
                    # e.g. {video_id}_{noisy_folder}_OriginalVTTBaseName_audio_0.vtt
                    dest_transcript_filename = f"{video_id}_{noisy_folder}_{potential_transcript_file}"
                    target_transcript_path = os.path.join(target_category_dir, dest_transcript_filename)

                    if not os.path.exists(target_transcript_path):
                        try:
                            shutil.copy2(original_transcript_full_path, target_transcript_path)
                            copied_transcripts_for_this_audio += 1
                        except Exception as e:
                            print(f"     Error copying transcript {original_transcript_full_path} to {target_transcript_path}: {e}")
            
            if copied_transcripts_for_this_audio == 0:
                print(f"     Warning: No VTT transcripts found for audio file '{original_audio_path}' matching pattern *{expected_transcript_suffix}.")
        
        print(f"   Finished processing for '{category}'. Copied {copied_audio_count} audios and their associated transcripts (if found and copied).")

    print("\n--- Operation Complete ---")
    print(f"Selected audios and transcripts are saved in: '{output_dataset_dir}'")

def pipeline():
    chunked_dataset_path = "chunked_dataset" 
    new_dataset_path = "sampled_dataset" 
    analyze_and_extract_audios(chunked_dataset_path, new_dataset_path)

if __name__ == "__main__":
    pipeline()