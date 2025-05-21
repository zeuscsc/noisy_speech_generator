import os
import random
import shutil
import json
import re
from datetime import datetime

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
    """Loads video metadata (tags, language, etc.) from the JSON file."""
    video_metadata_map = {}
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
                    
                    video_metadata_map[video_id_to_use] = {
                        'language': language,
                        'accent': accent,
                        'tags': sorted(list(set(cleaned_tags)))
                    }
                    items_processed_successfully += 1
                else:
                    items_skipped_no_id += 1
            
            if items_skipped_no_id > 0:
                print(f"Info: Skipped {items_skipped_no_id} items from metadata as video_id could not be determined.")
            if items_processed_successfully == 0 and loaded_data:
                print(f"Warning: Processed 0 video metadata items successfully from {len(loaded_data)} entries.")
                
    except FileNotFoundError:
        print(f"ERROR: Metadata file '{metadata_file_path}' not found.")
        return None 
    except json.JSONDecodeError:
        print(f"ERROR: Error decoding JSON from '{metadata_file_path}'.")
        return None 
    except Exception as e:
        print(f"An unexpected error occurred while loading metadata: {e}")
        return None

    if not video_metadata_map and items_processed_successfully == 0 and isinstance(loaded_data, list) and len(loaded_data) > 0:
        print(f"Warning: Video metadata map is empty after attempting to process {len(loaded_data)} items.")
    
    return video_metadata_map

def save_testcase_list_json(report_items_list, output_file, selection_mode_str):
    """Saves the list of processed test cases to a JSON file,
    using destination_audio_path as the key for each sample."""
    print(f"\n--- Saving Test Case List to JSON ---")
    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    samples_by_destination_path = {}
    items_with_missing_dest_path = 0
    for item in report_items_list:
        dest_path = item.get('destination_audio_path')
        if dest_path:
            if dest_path in samples_by_destination_path:
                print(f"Warning: Duplicate destination_audio_path found in report items: {dest_path}. Overwriting entry in JSON log.")
            samples_by_destination_path[dest_path] = item
        else:
            
            
            
            
            
            placeholder_key = f"MISSING_DEST_PATH_ITEM_{items_with_missing_dest_path}"
            if item.get('original_path'): 
                placeholder_key = f"MISSING_DEST_PATH_FOR_{os.path.basename(item['original_path'])}_{items_with_missing_dest_path}"

            
            
            
            
            if item.get('status', '').startswith('Skipped - Original Path Not Found'):
                 
                 
                 
                 print(f"Warning: Item {item.get('original_path', 'Unknown original path')} was skipped but seems to be missing 'destination_audio_path' for JSON keying. Storing under generic key.")
                 samples_by_destination_path[placeholder_key] = item

            else:
                 print(f"Warning: Report item is missing 'destination_audio_path'. Keying with '{placeholder_key}'. Item: {item}")
                 samples_by_destination_path[placeholder_key] = item
            items_with_missing_dest_path += 1


    json_data = {
        "report_metadata": {
            "generation_date": current_time_str,
            "total_samples_in_log_map": len(samples_by_destination_path),
            "selection_mode_for_this_run": selection_mode_str,
            "original_report_items_count": len(report_items_list)
        },
        "samples_by_destination_path": samples_by_destination_path
    }

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
        print(f"Test case list successfully saved to '{output_file}'")
        if items_with_missing_dest_path > 0:
            print(f"Note: {items_with_missing_dest_path} items were logged with missing or placeholder destination_audio_path keys.")
    except IOError as e:
        print(f"Error writing JSON test case list to '{output_file}': {e}")

def parse_chunk_folder_name_for_times(chunk_folder_name):
    """Extracts start and end times from chunk folder names like '..._HH-MM-SS_HH-MM-SS'."""
    match = re.search(r'_(\d{2}-\d{2}-\d{2}(?:\.\d{3})?)_(\d{2}-\d{2}-\d{2}(?:\.\d{3})?)$', chunk_folder_name)
    if match:
        return match.group(1), match.group(2) 
    return None, None

def analyze_and_extract_audios(base_dataset_path, 
                                new_dataset_folder_path, 
                                metadata_file_path="urls.meta.json", 
                                min_samples_per_chunk_group=5,
                                use_random_selection=True,
                                testcase_list_json_file="sampled_testcases_list.json"):
    source_dataset_dir = base_dataset_path
    output_dataset_dir = new_dataset_folder_path

    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting script due to critical errors in loading video metadata from urls.meta.json.")
        return

    all_discovered_audio_details = []
    print(f"Scanning '{source_dataset_dir}' (absolute: '{os.path.abspath(source_dataset_dir)}') to identify audio files...")
    if not os.path.isdir(source_dataset_dir):
        print(f"Error: Source directory '{source_dataset_dir}' not found.")
        return

    video_id_folders = [d for d in os.listdir(source_dataset_dir) if os.path.isdir(os.path.join(source_dataset_dir, d))]
    if not video_id_folders:
        print(f"INFO: No subdirectories (potential video_id_folders) found under '{source_dataset_dir}'.")

    for video_id_from_folder in video_id_folders:
        video_id_path = os.path.join(source_dataset_dir, video_id_from_folder)
        video_id_key = video_id_from_folder.strip()
        metadata_for_video = video_metadata_map.get(video_id_key, {}) 
        current_file_tags = metadata_for_video.get('tags', [])


        potential_chunk_folders = [d for d in os.listdir(video_id_path)
                                        if os.path.isdir(os.path.join(video_id_path, d)) and d.startswith("chunk_")]
        
        for chunk_folder_name in potential_chunk_folders:
            chunk_start_time, chunk_end_time = parse_chunk_folder_name_for_times(chunk_folder_name)
            chunk_folder_path = os.path.join(video_id_path, chunk_folder_name)
            noisy_level_folders = [d for d in os.listdir(chunk_folder_path)
                                        if os.path.isdir(os.path.join(chunk_folder_path, d)) and d.startswith("noisy_")]
            
            for noisy_folder_name in noisy_level_folders:
                noisy_folder_path = os.path.join(chunk_folder_path, noisy_folder_name)
                try: files_in_noisy_folder = os.listdir(noisy_folder_path)
                except OSError as e:
                    print(f"Warning: Could not list contents of '{noisy_folder_path}': {e}"); continue
                
                for original_filename in files_in_noisy_folder:
                    if original_filename.endswith(".mp3"):
                        match_conceptual = re.search(r'(audio_\d+\.mp3)$', original_filename, re.IGNORECASE) 
                        conceptual_filename = match_conceptual.group(1) if match_conceptual else original_filename
                        
                        audio_full_path = os.path.join(noisy_folder_path, original_filename)
                        all_discovered_audio_details.append({
                            'path': audio_full_path,
                            'video_id': video_id_key,
                            'noisy_folder': noisy_folder_name,
                            'filename': conceptual_filename, 
                            'original_filename': original_filename,
                            'chunk_type': chunk_folder_name,
                            'chunk_start_time_str': chunk_start_time,
                            'chunk_end_time_str': chunk_end_time,
                            'tags': current_file_tags 
                        })

    if not all_discovered_audio_details:
        print(f"No audio files matching the expected pattern were found in '{source_dataset_dir}'. Halting.")
        return

    try:
        os.makedirs(output_dataset_dir, exist_ok=True)
        print(f"\nEnsured base output directory exists: '{output_dataset_dir}'")
    except OSError as e:
        print(f"Error: Could not create base output directory {output_dataset_dir}: {e}"); return

    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    selection_mode_str = "RANDOM" if use_random_selection else "FIXED"
    
    audio_samples_to_process = [] 

    if use_random_selection:
        print("\n--- Selecting Audio Files (Random Selection) ---")
        unique_tags_overall = set()
        audios_by_tag_and_chunk = {} 
        for audio_detail in all_discovered_audio_details:
            if not audio_detail['tags']: 
                pass
            for tag in audio_detail['tags']: 
                unique_tags_overall.add(tag)
                audios_by_tag_and_chunk.setdefault(tag, {}).setdefault(audio_detail['chunk_type'], []).append(audio_detail)

        print("\n--- Discovered Audio Distribution by Tag and Chunk Type (prior to selection) ---")
        if not unique_tags_overall:
            print("No specific tags found associated with any discovered audio files based on metadata.")
        for tag_name_dist in sorted(list(unique_tags_overall)):
            print(f"Tag: {tag_name_dist}")
            if tag_name_dist in audios_by_tag_and_chunk:
                for chunk_type_dist, files_list_dist in sorted(audios_by_tag_and_chunk[tag_name_dist].items()):
                    noise_counts = {}
                    for f_info in files_list_dist: noise_counts[f_info['noisy_folder']] = noise_counts.get(f_info['noisy_folder'], 0) + 1
                    noise_detail = ", ".join([f"{nl}: {count}" for nl, count in sorted(noise_counts.items())])
                    print(f"    Chunk Type: {chunk_type_dist} (Total source files: {len(files_list_dist)}. Noise levels: {noise_detail if noise_detail else 'N/A'})")
            else:
                print(f"    No audio files found for this tag (This message indicates an issue if tag was in unique_tags_overall).")
        
        if not unique_tags_overall and len(all_discovered_audio_details) > 0:
            print("\nWARNING: Audio files were discovered, but no specific tags were associated with them from metadata. No random selection by tag possible.")

        for tag_name in sorted(list(unique_tags_overall)): 
            print(f"\nProcessing for Tag: {tag_name}...")
            if tag_name not in audios_by_tag_and_chunk: 
                continue 

            chunk_categories_data_for_tag = audios_by_tag_and_chunk[tag_name]
            for chunk_category, all_audios_for_this_tag_and_chunk in sorted(chunk_categories_data_for_tag.items()):
                print(f"    Processing chunk category: {chunk_category} for Tag '{tag_name}'...")
                if not all_audios_for_this_tag_and_chunk:
                    print(f"      No audio files were found for '{chunk_category}' under Tag '{tag_name}'. Skipping.")
                    continue

                selected_for_this_group = []
                selected_paths_in_this_group = set() 

                audios_by_noise_level = {} 
                for audio_info_item in all_audios_for_this_tag_and_chunk:
                    audios_by_noise_level.setdefault(audio_info_item['noisy_folder'], []).append(audio_info_item)

                actual_noise_levels_sampled_from = 0
                for noise_level in sorted(list(audios_by_noise_level.keys())): 
                    if audios_by_noise_level[noise_level]: 
                        chosen_audio = random.choice(audios_by_noise_level[noise_level])
                        if chosen_audio['path'] not in selected_paths_in_this_group: 
                            selected_for_this_group.append(chosen_audio)
                            selected_paths_in_this_group.add(chosen_audio['path'])
                            actual_noise_levels_sampled_from += 1
                
                remaining_needed = min_samples_per_chunk_group - len(selected_for_this_group)
                if remaining_needed > 0:
                    additional_candidates = [
                        item for item in all_audios_for_this_tag_and_chunk if item['path'] not in selected_paths_in_this_group
                    ]
                    random.shuffle(additional_candidates)
                    selected_for_this_group.extend(additional_candidates[:remaining_needed])
                
                if selected_for_this_group:
                    print(f"      Selected {len(selected_for_this_group)} audio files (target: {min_samples_per_chunk_group}, from {actual_noise_levels_sampled_from} distinct noise levels initially) for '{chunk_category}' under Tag '{tag_name}'.")
                    for item_to_add in selected_for_this_group:
                        audio_samples_to_process.append({**item_to_add, '_current_processing_tag': tag_name})
                else:
                    print(f"      No audio files were selected for '{chunk_category}' under Tag '{tag_name}'.")


    else: 
        print(f"\n--- Loading Fixed Sample List from '{testcase_list_json_file}' ---")
        try:
            with open(testcase_list_json_file, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")

            if isinstance(specs_map_from_json, dict):
                print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from JSON file.")
                
                
                discovered_audio_map_by_path = {audio['path']: audio for audio in all_discovered_audio_details}

                for dest_path_key, spec_from_log in specs_map_from_json.items():
                    if not isinstance(spec_from_log, dict):
                        print(f"Warning: Invalid spec found in JSON log for key '{dest_path_key}'. Skipping.")
                        final_report_data_list.append({
                            'original_path': 'N/A - Invalid spec in log',
                            'destination_audio_path': dest_path_key,
                            'status': 'Skipped - Invalid Log Entry',
                            'error_message': f'Spec for destination key {dest_path_key} was not a dictionary.',
                            'processed_timestamp': processed_current_run_timestamp
                        })
                        continue

                    original_path_from_log = spec_from_log.get('original_path')

                    if not original_path_from_log:
                        print(f"Warning: Sample spec (intended for dest: {dest_path_key}) from fixed list is missing 'original_path'. Skipping.")
                        final_report_data_list.append({
                            **spec_from_log, 
                            'original_path': 'N/A - Missing in log',
                            'destination_audio_path': dest_path_key, 
                            'status': 'Skipped - Original Path Missing in Log',
                            'error_message': 'Original path for this sample was not found in the JSON log entry.',
                            'processed_timestamp': processed_current_run_timestamp
                        })
                        continue
                        
                    found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                    
                    if found_detail:
                        
                        
                        
                        

                        processing_tag_for_fixed_item = spec_from_log.get('processing_tag_context')
                        if not processing_tag_for_fixed_item:
                            
                            tags_for_fixed_item = found_detail.get('tags', [])
                            processing_tag_for_fixed_item = tags_for_fixed_item[0] if tags_for_fixed_item else 'untagged_fixed_fallback'
                            print(f"Warning: 'processing_tag_context' missing for {original_path_from_log} in log. Using fallback: {processing_tag_for_fixed_item}")
                        
                        audio_samples_to_process.append({**found_detail, '_current_processing_tag': processing_tag_for_fixed_item})
                    else:
                        print(f"Warning: Sample with original path '{original_path_from_log}' (intended for dest: '{dest_path_key}') from fixed list not found in current dataset scan. Skipping.")
                        
                        final_report_data_list.append({
                            **spec_from_log, 
                            'status': 'Skipped - Original Path Not Found in Source (current scan)',
                            'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.",
                            'processed_timestamp': processed_current_run_timestamp
                            
                        })
            else:
                
                legacy_samples_list = data_from_json.get("samples")
                if isinstance(legacy_samples_list, list) and legacy_samples_list:
                    print(f"Warning: JSON file '{testcase_list_json_file}' seems to be in an old list format. Attempting legacy load. Please re-generate the list for new format.")
                    
                    
                    print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{testcase_list_json_file}'. Halting fixed selection.")
                    return

                else:
                    print(f"Error: JSON file '{testcase_list_json_file}' does not contain a valid 'samples_by_destination_path' dictionary.")
                    return
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, test case JSON file '{testcase_list_json_file}' not found.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{testcase_list_json_file}'.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading '{testcase_list_json_file}': {e}")
            return

    total_copy_operations = 0
    print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} potential processing entries ---")
    
    processed_paths_this_run = set() 

    for audio_info_with_context in audio_samples_to_process: 
        audio_info = {key: value for key, value in audio_info_with_context.items() if key != '_current_processing_tag'}
        current_processing_tag = audio_info_with_context.get('_current_processing_tag') 

        original_audio_full_path = audio_info['path']
        video_id = audio_info['video_id']
        chunk_type = audio_info['chunk_type'] 
        noisy_folder = audio_info['noisy_folder']
        original_audio_source_filename = audio_info['original_filename']
        
        if not current_processing_tag:
                current_processing_tag = audio_info.get('tags',[None])[0] or 'untagged_processing'


        target_file_directory = os.path.join(output_dataset_dir, current_processing_tag, chunk_type)
        
        dest_audio_filename = f"{video_id}_{noisy_folder}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        processing_key = (original_audio_full_path, target_audio_path)
        if processing_key in processed_paths_this_run:
            continue
        processed_paths_this_run.add(processing_key)

        try:
            os.makedirs(target_file_directory, exist_ok=True)
        except OSError as e:
            print(f"  Error creating directory {target_file_directory}: {e}. Skipping sample {original_audio_full_path}")
            final_report_data_list.append({
                'original_path': original_audio_full_path, 'video_id': video_id, 'noisy_folder': noisy_folder,
                'conceptual_filename': audio_info['filename'], 'original_filename': original_audio_source_filename,
                'chunk_type': chunk_type, 'chunk_start_time_str': audio_info.get('chunk_start_time_str'),
                'chunk_end_time_str': audio_info.get('chunk_end_time_str'), 'tags': audio_info.get('tags', []), 
                'processing_tag_context': current_processing_tag, 'destination_audio_path': target_audio_path, 
                'destination_transcript_path': None, 'status': 'Skipped - Directory Creation Error',
                'error_message': f"Failed to create target directory: {e}",
                'processed_timestamp': processed_current_run_timestamp
            })
            continue
        
        report_item = {
            'original_path': original_audio_full_path, 'video_id': video_id, 'noisy_folder': noisy_folder,
            'conceptual_filename': audio_info['filename'], 'original_filename': original_audio_source_filename,
            'chunk_type': chunk_type, 'chunk_start_time_str': audio_info.get('chunk_start_time_str'),
            'chunk_end_time_str': audio_info.get('chunk_end_time_str'), 'tags': audio_info.get('tags', []), 
            'processing_tag_context': current_processing_tag, 
            'destination_audio_path': target_audio_path, 'destination_transcript_path': None,
            'status': 'Pending Copy', 'error_message': None, 'processed_timestamp': processed_current_run_timestamp
        }

        try:
            shutil.copy2(original_audio_full_path, target_audio_path)
            total_copy_operations += 1
            report_item['status'] = 'Audio Copied'
            
            original_audio_dir = os.path.dirname(original_audio_full_path)
            expected_source_vtt_filename = os.path.splitext(original_audio_source_filename)[0] + ".vtt"
            original_transcript_full_path = os.path.join(original_audio_dir, expected_source_vtt_filename)
            
            if os.path.isfile(original_transcript_full_path):
                target_transcript_path = os.path.splitext(target_audio_path)[0] + ".vtt"
                report_item['destination_transcript_path'] = target_transcript_path
                try:
                    shutil.copy2(original_transcript_full_path, target_transcript_path)
                    report_item['status'] = 'Audio and VTT Copied'
                except Exception as e_vtt:
                    report_item['status'] = 'Audio Copied, VTT Error'
                    report_item['error_message'] = f"VTT copy error: {str(e_vtt)}"
            else:
                report_item['status'] = 'Audio Copied, VTT Not Found'
        except Exception as e_audio:
            report_item['status'] = 'Error Copying Audio'
            report_item['error_message'] = f"Audio copy error: {str(e_audio)}"
        
        final_report_data_list.append(report_item)

    print("\n--- Operation Complete ---")
    print(f"A total of {total_copy_operations} audio files were copied/updated.")
    print(f"Selected audios and transcripts are saved in: '{output_dataset_dir}'")
    
    save_testcase_list_json(final_report_data_list, testcase_list_json_file, selection_mode_str)

def pipeline():
    chunked_dataset_path = "chunked_dataset_with_ground_truth" 
    new_dataset_path = "sampled_testcase" 
    metadata_json_file = "urls.meta.json" 
    min_samples_to_select_if_random = 10 
    test_cases_json_filename = "sampled_testcases_list.json"

    USE_RANDOM_SELECTION = True 
    
    selection_mode_str_display = "RANDOM selection" if USE_RANDOM_SELECTION else f"FIXED list selection from '{test_cases_json_filename}'"
    print(f"Pipeline starting with {selection_mode_str_display}.")
    print(f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    analyze_and_extract_audios(
        base_dataset_path=chunked_dataset_path, 
        new_dataset_folder_path=new_dataset_path, 
        metadata_file_path=metadata_json_file, 
        min_samples_per_chunk_group=min_samples_to_select_if_random,
        use_random_selection=USE_RANDOM_SELECTION,
        testcase_list_json_file=test_cases_json_filename
    )

if __name__ == "__main__":
    pipeline()