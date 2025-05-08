import os
import random
import shutil
import json
import re

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

def extract_youtube_id_from_url(url_string):
    if not url_string or not isinstance(url_string, str):
        return None
    
    match = re.search(
        r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?|shorts|live)\/|.*[?&]v=)|youtu\.be\/|googleusercontent\.com\/youtube\.com\/)([a-zA-Z0-9_-]{11})',
        url_string
    )
    if match:
        return match.group(1) 
    return None

def load_metadata(metadata_file_path="urls.meta.json"):
    metadata_map = {}
    loaded_data = None 

    try:
        with open(metadata_file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f) 
            if not isinstance(loaded_data, list):
                print(f"Warning: Metadata file {metadata_file_path} does not contain a list of items.")
                return {} 

            items_processed_successfully = 0
            items_skipped_no_id = 0

            for item_index, item in enumerate(loaded_data):
                if not isinstance(item, dict):
                    print(f"Warning: Skipping non-dictionary item in metadata at index {item_index}: {item}")
                    continue

                video_id_to_use = None
                
                if 'youtube_video_id' in item and item['youtube_video_id'] and isinstance(item['youtube_video_id'], str):
                    candidate_id = item['youtube_video_id'].strip()
                    if candidate_id: 
                        video_id_to_use = candidate_id

                if not video_id_to_use and 'url' in item and item['url'] and isinstance(item['url'], str):
                    extracted_id = extract_youtube_id_from_url(item['url'])
                    if extracted_id: 
                        video_id_to_use = extracted_id.strip() 
                
                if video_id_to_use:
                    language = item.get('language') or 'unknown_language'
                    accent = item.get('accent') or 'unknown_accent'
                    metadata_map[video_id_to_use] = {'language': language, 'accent': accent}
                    items_processed_successfully += 1
                else:
                    items_skipped_no_id += 1
            
            if items_skipped_no_id > 0:
                print(f"Info: Skipped {items_skipped_no_id} items from metadata as video_id could not be determined (from 'youtube_video_id' field or 'url' field).")
            if items_processed_successfully == 0 and len(loaded_data) > 0:
                print(f"Warning: Processed 0 items successfully from metadata. All items might have issues with video_id field or URL format for ID extraction.")

    except FileNotFoundError:
        print(f"ERROR: Metadata file '{metadata_file_path}' not found. Cannot proceed.")
        return None 
    except json.JSONDecodeError:
        print(f"ERROR: Error decoding JSON from '{metadata_file_path}'. Check its format.")
        return None 
    except Exception as e:
        print(f"An unexpected error occurred while loading metadata: {e}")
        return None
    
    if not metadata_map and items_processed_successfully == 0 and isinstance(loaded_data, list) and len(loaded_data) > 0:
        print(f"Warning: Metadata map is empty after attempting to process {len(loaded_data)} items. Check video ID extraction logic and JSON content.")

    return metadata_map

def analyze_and_extract_audios(base_dataset_path, new_dataset_folder_path, metadata_file_path="urls.meta.json", min_samples_per_chunk_group=5):
    source_dataset_dir = base_dataset_path
    output_dataset_dir = new_dataset_folder_path

    video_metadata_map = load_metadata(metadata_file_path)

    if video_metadata_map is None:
        print("Halting script due to errors in loading metadata.")
        return
    if not video_metadata_map:
        print("Warning: Metadata map is empty after loading. All items might be classified as unknown if no matches are found in filesystem.")

    audio_files_by_lang_accent_chunk = {}
    found_any_metadata_match = False 

    print(f"Scanning '{source_dataset_dir}' to identify audio files and categorize by language, accent, and chunk type...")

    if not os.path.isdir(source_dataset_dir):
        print(f"Error: Source directory '{source_dataset_dir}' not found.")
        return

    video_id_folders = [d for d in os.listdir(source_dataset_dir) if os.path.isdir(os.path.join(source_dataset_dir, d))]

    for video_id_from_folder in video_id_folders:
        video_id_path = os.path.join(source_dataset_dir, video_id_from_folder)
        video_id_key = video_id_from_folder.strip() 

        current_language = 'unknown_language'
        current_accent = 'unknown_accent'
        metadata = video_metadata_map.get(video_id_key)

        if metadata:
            lang_from_meta = metadata.get('language')
            acc_from_meta = metadata.get('accent')

            if lang_from_meta and lang_from_meta.strip(): 
                current_language = lang_from_meta.strip()
            if acc_from_meta and acc_from_meta.strip(): 
                current_accent = acc_from_meta.strip()
            
            if (current_language != 'unknown_language' and current_language) or \
               (current_accent != 'unknown_accent' and current_accent):
                found_any_metadata_match = True
        
        potential_chunk_folders = [d for d in os.listdir(video_id_path) 
                                   if os.path.isdir(os.path.join(video_id_path, d)) and d.startswith("chunk_")]
        
        for chunk_folder_name in potential_chunk_folders:
            chunk_folder_path = os.path.join(video_id_path, chunk_folder_name)
            noisy_level_folders = [d for d in os.listdir(chunk_folder_path) 
                                   if os.path.isdir(os.path.join(chunk_folder_path, d)) and d.startswith("noisy_")]
            
            for noisy_folder_name in noisy_level_folders:
                noisy_folder_path = os.path.join(chunk_folder_path, noisy_folder_name)
                
                for filename in os.listdir(noisy_folder_path):
                    if filename.startswith("audio_") and filename.endswith(".mp3"):
                        audio_full_path = os.path.join(noisy_folder_path, filename)
                        
                        audio_files_by_lang_accent_chunk.setdefault(current_language, {})\
                            .setdefault(current_accent, {})\
                            .setdefault(chunk_folder_name, [])\
                            .append({
                                'path': audio_full_path,
                                'video_id': video_id_key,
                                'noisy_folder': noisy_folder_name,
                                'filename': filename
                            })

    if not audio_files_by_lang_accent_chunk:
        print(f"No audio files were found or categorized from '{source_dataset_dir}'.")
        return

    print("\n--- Discovered Audio Distribution by Language, Accent, and Chunk Type ---")
    for lang, accents in sorted(audio_files_by_lang_accent_chunk.items()):
        print(f"Language: {lang}")
        for acc, chunks in sorted(accents.items()):
            print(f"  Accent: {acc}")
            for chunk_type, files in sorted(chunks.items()):
                noise_counts = {}
                for f_info in files:
                    noise_counts[f_info['noisy_folder']] = noise_counts.get(f_info['noisy_folder'], 0) + 1
                noise_detail = ", ".join([f"{nl}: {count}" for nl, count in sorted(noise_counts.items())])
                print(f"    Chunk Type: {chunk_type} (Total: {len(files)} audio files. Noise levels: {noise_detail if noise_detail else 'N/A'})")


    try:
        os.makedirs(output_dataset_dir, exist_ok=True)
        print(f"\nEnsured base output directory exists: '{output_dataset_dir}'")
    except OSError as e:
        print(f"Error: Could not create base output directory {output_dataset_dir}: {e}")
        return

    print("\n--- Selecting and Copying Audio Files and Transcripts ---")
    
    total_audio_copied = 0

    for language, accents in sorted(audio_files_by_lang_accent_chunk.items()):
        for accent, chunk_categories_data in sorted(accents.items()):
            print(f"\nProcessing Language: {language}, Accent: {accent}...")
            if not chunk_categories_data:
                print(f"   No chunk data found for {language}/{accent}. Skipping.")
                continue

            for chunk_category, all_audios_for_specific_group in sorted(chunk_categories_data.items()):
                print(f"  Processing chunk category: {chunk_category}...")
                if not all_audios_for_specific_group:
                    print(f"     No audio files were found for '{chunk_category}' in {language}/{accent}. Skipping.")
                    continue

                selected_audios_for_copying = []
                selected_audio_paths = set()

                audios_by_noise_level = {}
                for audio_info_item in all_audios_for_specific_group: 
                    noise_level_key = audio_info_item['noisy_folder']
                    audios_by_noise_level.setdefault(noise_level_key, []).append(audio_info_item)

                distinct_noise_levels = sorted(list(audios_by_noise_level.keys()))
                actual_noise_levels_sampled_from = 0
                for noise_level in distinct_noise_levels:
                    if audios_by_noise_level[noise_level]: 
                        chosen_audio = random.choice(audios_by_noise_level[noise_level])
                        if chosen_audio['path'] not in selected_audio_paths:
                            selected_audios_for_copying.append(chosen_audio)
                            selected_audio_paths.add(chosen_audio['path'])
                            actual_noise_levels_sampled_from +=1
                
                num_currently_selected = len(selected_audios_for_copying)
                remaining_needed_for_target = min_samples_per_chunk_group - num_currently_selected

                if remaining_needed_for_target > 0:
                    additional_candidate_pool = []
                    for audio_info_item in all_audios_for_specific_group: 
                        if audio_info_item['path'] not in selected_audio_paths:
                            additional_candidate_pool.append(audio_info_item)
                    
                    random.shuffle(additional_candidate_pool) 
                    num_to_add = min(remaining_needed_for_target, len(additional_candidate_pool))
                    
                    for i in range(num_to_add):
                        audio_to_add = additional_candidate_pool[i]
                        selected_audios_for_copying.append(audio_to_add)
                
                print(f"     Selected {len(selected_audios_for_copying)} audio files (target: {min_samples_per_chunk_group}, from {actual_noise_levels_sampled_from} distinct noise levels) for '{chunk_category}' in {language}/{accent}.")

                copied_audio_count_for_this_group = 0
                for audio_info in selected_audios_for_copying: 
                    original_audio_path = audio_info['path']
                    video_id_from_audio = audio_info['video_id'] 
                    noisy_folder = audio_info['noisy_folder']
                    original_audio_filename = audio_info['filename']

                    target_file_directory = os.path.join(output_dataset_dir, language, accent, chunk_category)
                    try:
                        os.makedirs(target_file_directory, exist_ok=True)
                    except OSError as e:
                        print(f"       Error: Could not create target directory {target_file_directory}: {e}")
                        continue

                    dest_audio_filename = f"{video_id_from_audio}_{noisy_folder}_{original_audio_filename}"
                    target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

                    try:
                        shutil.copy2(original_audio_path, target_audio_path)
                        copied_audio_count_for_this_group += 1
                        total_audio_copied += 1
                    except Exception as e:
                        print(f"       Error copying audio {original_audio_path} to {target_audio_path}: {e}")
                        continue 
                    
                    original_audio_dir = os.path.dirname(original_audio_path)
                    audio_basename_no_ext = os.path.splitext(original_audio_filename)[0]
                    expected_transcript_suffix = f"_{audio_basename_no_ext}.vtt" 
                    copied_transcripts_for_this_audio = 0

                    if os.path.isdir(original_audio_dir):
                        for potential_transcript_file in os.listdir(original_audio_dir):
                            if potential_transcript_file.endswith(expected_transcript_suffix) and \
                               os.path.isfile(os.path.join(original_audio_dir, potential_transcript_file)):
                                original_transcript_full_path = os.path.join(original_audio_dir, potential_transcript_file)
                                dest_transcript_filename = f"{video_id_from_audio}_{noisy_folder}_{potential_transcript_file}"
                                target_transcript_path = os.path.join(target_file_directory, dest_transcript_filename)
                                if not os.path.exists(target_transcript_path):
                                    try:
                                        shutil.copy2(original_transcript_full_path, target_transcript_path)
                                        copied_transcripts_for_this_audio += 1
                                    except Exception as e:
                                        print(f"       Error copying transcript {original_transcript_full_path} to {target_transcript_path}: {e}")
                    if copied_transcripts_for_this_audio == 0:
                        print(f"       Warning: No VTT transcripts found for audio file '{original_audio_path}' matching pattern *{expected_transcript_suffix} in {original_audio_dir}.")
                
                print(f"     Finished processing for '{chunk_category}' in {language}/{accent}. Copied {copied_audio_count_for_this_group} audios and their associated transcripts.")
    
    if not found_any_metadata_match and video_metadata_map and any(m.get('language', 'unknown_language') != 'unknown_language' or m.get('accent', 'unknown_accent') != 'unknown_accent' for m in video_metadata_map.values()):
        print("\nWARNING: No matches were found between video IDs from the filesystem and IDs in the metadata file that yielded specific language/accent information, OR all metadata entries were 'unknown'.")
        print("This might mean all files are sorted into 'unknown_language'/'unknown_accent'.")
        print("Please ensure that the folder names in your 'chunked_dataset' (e.g., 'YOUTUBEID1')")
        print("exactly match the values in the 'youtube_video_id' field of your 'urls.meta.json' file,")
        print("and that the metadata file contains specific language/accent information.")
        print("Check for differences in case, extra characters, or missing entries. Also, ensure IDs are stripped of whitespace.")

    print("\n--- Operation Complete ---")
    print(f"A total of {total_audio_copied} audio files and their transcripts have been selected.")
    print(f"Selected audios and transcripts are saved in: '{output_dataset_dir}' (organized by language/accent/chunk_size, with each noise level represented where possible)")

def pipeline():
    chunked_dataset_path = "chunked_dataset" 
    new_dataset_path = "sampled_dataset" 
    metadata_json_file = "urls.meta.json"
    min_samples_to_select = 5 
    analyze_and_extract_audios(chunked_dataset_path, new_dataset_path, metadata_json_file, min_samples_per_chunk_group=min_samples_to_select)

if __name__ == "__main__":
    pipeline()