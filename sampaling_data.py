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
                    tags = item.get('tags', [])
                    if not isinstance(tags, list):
                        print(f"Warning: 'tags' for video_id {video_id_to_use} is not a list, using empty list. Found: {tags}")
                        tags = []
                    
                    cleaned_tags = []
                    for tag_item in tags:
                        if isinstance(tag_item, str):
                            stripped_tag = tag_item.strip()
                            if stripped_tag:
                                cleaned_tags.append(stripped_tag)
                        else:
                            print(f"Warning: Non-string item found in tags for video_id {video_id_to_use}: {tag_item}. Skipping this tag item.")
                    
                    metadata_map[video_id_to_use] = {
                        'language': language,
                        'accent': accent,
                        'tags': sorted(list(set(cleaned_tags)))
                    }
                    items_processed_successfully += 1
                else:
                    items_skipped_no_id += 1
            
            if items_skipped_no_id > 0:
                print(f"Info: Skipped {items_skipped_no_id} items from metadata as video_id could not be determined.")
            if items_processed_successfully == 0 and loaded_data and len(loaded_data) > 0:
                print(f"Warning: Processed 0 items successfully from metadata.")
    except FileNotFoundError:
        print(f"ERROR: Metadata file '{metadata_file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Error decoding JSON from '{metadata_file_path}'.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading metadata: {e}")
        return None
    if not metadata_map and items_processed_successfully == 0 and isinstance(loaded_data, list) and len(loaded_data) > 0:
        print(f"Warning: Metadata map is empty after attempting to process {len(loaded_data)} items.")
    return metadata_map

def analyze_and_extract_audios(base_dataset_path, new_dataset_folder_path, metadata_file_path="urls.meta.json", min_samples_per_chunk_group=5):
    source_dataset_dir = base_dataset_path
    output_dataset_dir = new_dataset_folder_path

    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting script due to errors in loading metadata.")
        return

    all_discovered_audio_details = []
    print(f"Scanning '{source_dataset_dir}' to identify audio files and their associated tags...")

    if not os.path.isdir(source_dataset_dir):
        print(f"Error: Source directory '{source_dataset_dir}' not found.")
        return

    video_id_folders = [d for d in os.listdir(source_dataset_dir) if os.path.isdir(os.path.join(source_dataset_dir, d))]
    for video_id_from_folder in video_id_folders:
        video_id_path = os.path.join(source_dataset_dir, video_id_from_folder)
        video_id_key = video_id_from_folder.strip()
        metadata_for_video = video_metadata_map.get(video_id_key)
        current_file_tags = metadata_for_video.get('tags', []) if metadata_for_video else []

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
                        all_discovered_audio_details.append({
                            'path': audio_full_path,
                            'video_id': video_id_key,
                            'noisy_folder': noisy_folder_name,
                            'filename': filename,
                            'chunk_type': chunk_folder_name,
                            'tags': current_file_tags 
                        })

    if not all_discovered_audio_details:
        print(f"No audio files were found in '{source_dataset_dir}'.")
        return

    unique_tags_overall = set()
    audios_by_tag_and_chunk = {}
    for audio_detail in all_discovered_audio_details:
        for tag in audio_detail['tags']: 
            unique_tags_overall.add(tag)
            audios_by_tag_and_chunk.setdefault(tag, {}).setdefault(audio_detail['chunk_type'], []).append(audio_detail)

    print("\n--- Discovered Audio Distribution by Tag and Chunk Type (prior to selection) ---")
    if not unique_tags_overall:
        print("No specific tags found associated with any audio files based on metadata.")
    for tag_name in sorted(list(unique_tags_overall)):
        print(f"Tag: {tag_name}")
        if tag_name in audios_by_tag_and_chunk:
            for chunk_type, files_list in sorted(audios_by_tag_and_chunk[tag_name].items()):
                noise_counts = {f_info['noisy_folder']: 0 for f_info in files_list}
                for f_info in files_list:
                    noise_counts[f_info['noisy_folder']] += 1
                noise_detail = ", ".join([f"{nl}: {count}" for nl, count in sorted(noise_counts.items())])
                print(f"   Chunk Type: {chunk_type} (Total source files for this tag/chunk: {len(files_list)}. Noise levels: {noise_detail if noise_detail else 'N/A'})")
        else:
             print(f"   No audio files found for this tag.")


    try:
        os.makedirs(output_dataset_dir, exist_ok=True)
        print(f"\nEnsured base output directory exists: '{output_dataset_dir}'")
    except OSError as e:
        print(f"Error: Could not create base output directory {output_dataset_dir}: {e}")
        return

    print("\n--- Selecting and Copying Audio Files and Transcripts ---")
    total_copy_operations = 0
    found_any_tags_for_copying = bool(unique_tags_overall)

    for tag_name in sorted(list(unique_tags_overall)):
        print(f"\nProcessing for Tag: {tag_name}...")
        if tag_name not in audios_by_tag_and_chunk:
            continue 

        chunk_categories_data_for_tag = audios_by_tag_and_chunk[tag_name]
        for chunk_category, all_audios_for_this_tag_and_chunk in sorted(chunk_categories_data_for_tag.items()):
            print(f"   Processing chunk category: {chunk_category} for Tag '{tag_name}'...")
            if not all_audios_for_this_tag_and_chunk:
                print(f"     No audio files were found for '{chunk_category}' under Tag '{tag_name}'. Skipping.")
                continue

            selected_audios_for_copying = []
            selected_audio_paths_in_this_pass = set() 

            audios_by_noise_level = {}
            for audio_info_item in all_audios_for_this_tag_and_chunk:
                audios_by_noise_level.setdefault(audio_info_item['noisy_folder'], []).append(audio_info_item)

            actual_noise_levels_sampled_from = 0
            for noise_level in sorted(list(audios_by_noise_level.keys())):
                if audios_by_noise_level[noise_level]:
                    chosen_audio = random.choice(audios_by_noise_level[noise_level])
                    if chosen_audio['path'] not in selected_audio_paths_in_this_pass:
                        selected_audios_for_copying.append(chosen_audio)
                        selected_audio_paths_in_this_pass.add(chosen_audio['path'])
                        actual_noise_levels_sampled_from += 1
            
            remaining_needed = min_samples_per_chunk_group - len(selected_audios_for_copying)
            if remaining_needed > 0:
                additional_candidates = [
                    item for item in all_audios_for_this_tag_and_chunk if item['path'] not in selected_audio_paths_in_this_pass
                ]
                random.shuffle(additional_candidates)
                selected_audios_for_copying.extend(additional_candidates[:remaining_needed])
            
            print(f"     Selected {len(selected_audios_for_copying)} audio files (target: {min_samples_per_chunk_group}, from {actual_noise_levels_sampled_from} distinct noise levels initially) for '{chunk_category}' under Tag '{tag_name}'.")

            copied_in_this_group_pass = 0
            for audio_info in selected_audios_for_copying:
                original_audio_path = audio_info['path']
                target_file_directory = os.path.join(output_dataset_dir, tag_name, chunk_category)
                os.makedirs(target_file_directory, exist_ok=True)

                dest_audio_filename = f"{audio_info['video_id']}_{audio_info['noisy_folder']}_{audio_info['filename']}"
                target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

                try:
                    if not os.path.exists(target_audio_path): 
                        shutil.copy2(original_audio_path, target_audio_path)
                        total_copy_operations += 1
                        copied_in_this_group_pass += 1
                    else:
                        pass 

                    original_audio_dir = os.path.dirname(original_audio_path)
                    audio_basename_no_ext = os.path.splitext(audio_info['filename'])[0]
                    
                    transcript_copied_for_this_audio = False
                    if os.path.isdir(original_audio_dir):
                        for pt_filename in os.listdir(original_audio_dir):
                            expected_transcript_suffix_pattern = f"_{os.path.splitext(audio_info['filename'])[0]}.vtt"

                            if pt_filename.endswith(expected_transcript_suffix_pattern) and \
                               os.path.isfile(os.path.join(original_audio_dir, pt_filename)):
                                original_transcript_full_path = os.path.join(original_audio_dir, pt_filename)
                                dest_transcript_filename = f"{audio_info['video_id']}_{audio_info['noisy_folder']}_{pt_filename}"
                                target_transcript_path = os.path.join(target_file_directory, dest_transcript_filename)
                                if not os.path.exists(target_transcript_path):
                                    try:
                                        shutil.copy2(original_transcript_full_path, target_transcript_path)
                                        transcript_copied_for_this_audio = True
                                    except Exception as e:
                                        print(f"       Error copying transcript {original_transcript_full_path} to {target_transcript_path}: {e}")
                                break 

                    if os.path.exists(target_audio_path) and not transcript_copied_for_this_audio:
                        if not any(f.endswith(".vtt") and f.startswith(f"{audio_info['video_id']}_{audio_info['noisy_folder']}_{os.path.splitext(audio_info['filename'])[0]}") for f in os.listdir(target_file_directory)):
                             print(f"       Warning: No VTT transcript found/copied for audio '{target_audio_path}' (expected pattern based on '...{expected_transcript_suffix_pattern}').")


                except Exception as e:
                    print(f"       Error during copy operation for {original_audio_path}: {e}")
            
            print(f"     Finished processing for '{chunk_category}' under Tag '{tag_name}'. Performed {copied_in_this_group_pass} new audio copy operations in this pass.")

    if not found_any_tags_for_copying:
        print("\nWARNING: No specific tags were found associated with any audio files from the metadata after initial scan.")
        print("This means no files were copied because the process relies on tags for directory creation.")
        print("Please ensure that: \n1. The 'urls.meta.json' file contains a 'tags' field (as a list of non-empty strings) for relevant items. \n2. Video IDs in the filesystem match those in the metadata that have tags.")

    print("\n--- Operation Complete ---")
    print(f"A total of {total_copy_operations} audio file copy operations were performed across all tags and categories.")
    print(f"Selected audios and transcripts are saved in: '{output_dataset_dir}' (organized by individual Tag/chunk_size)")

def pipeline():
    chunked_dataset_path = "chunked_dataset"
    new_dataset_path = "sampled_testcase" 
    metadata_json_file = "urls.meta.json"
    min_samples_to_select = 5 
    analyze_and_extract_audios(chunked_dataset_path, new_dataset_path, metadata_json_file, min_samples_per_chunk_group=min_samples_to_select)

if __name__ == "__main__":
    pipeline()