import os
import random
import shutil
import json
import re
from datetime import datetime
from collections import defaultdict

USE_FIXED_SELECTION = True

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
                    language = (item.get('language') or 'unknown_language').lower() 
                    accent = (item.get('accent') or 'unknown_accent').lower()       
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

def save_processed_files_log(report_items_list, output_file, log_description_str):
    """Saves the list of processed files to a JSON log."""
    print(f"\n--- Saving Processed Files Log to JSON ({log_description_str}) ---")
    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    samples_by_destination_path = {}
    items_with_missing_dest_path = 0
    for item in report_items_list:
        dest_path = item.get('destination_audio_path')
        if dest_path:
            if dest_path in samples_by_destination_path:
                print(f"Warning: Duplicate destination_audio_path found: {dest_path}. Overwriting entry in JSON log.")
            samples_by_destination_path[dest_path] = item
        else:
            placeholder_key = f"MISSING_DEST_PATH_ITEM_{items_with_missing_dest_path}"
            if item.get('original_path'): 
                placeholder_key = f"MISSING_DEST_PATH_FOR_{os.path.basename(item['original_path'])}_{items_with_missing_dest_path}"
            
            if item.get('status', '').startswith('Skipped - Original Path Not Found'):
                print(f"Warning: Item {item.get('original_path', 'Unknown original path')} was skipped but missing 'destination_audio_path'. Storing under generic key.")
            else:
                print(f"Warning: Report item is missing 'destination_audio_path'. Keying with '{placeholder_key}'. Item: {item}")
            samples_by_destination_path[placeholder_key] = item
            items_with_missing_dest_path += 1

    json_data = {
        "log_metadata": {
            "generation_date": current_time_str,
            "log_description": log_description_str,
            "total_samples_in_log_map": len(samples_by_destination_path),
            "original_report_items_count": len(report_items_list)
        },
        "samples_by_destination_path": samples_by_destination_path
    }

    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
        print(f"Log successfully saved to '{output_file}'")
        if items_with_missing_dest_path > 0:
            print(f"Note: {items_with_missing_dest_path} items were logged with missing or placeholder destination_audio_path keys.")
    except IOError as e:
        print(f"Error writing JSON log to '{output_file}': {e}")

def parse_chunk_folder_name_for_times(chunk_folder_name):
    """Extracts start and end times from chunk folder names like '..._HH-MM-SS_HH-MM-SS'."""
    match = re.search(r'_(\d{2}-\d{2}-\d{2}(?:\.\d{3})?)_(\d{2}-\d{2}-\d{2}(?:\.\d{3})?)$', chunk_folder_name)
    if match:
        return match.group(1), match.group(2) 
    return None, None

def scan_all_audio_files(base_dataset_path, video_metadata_map):
    """Scans the base dataset path for all audio files and enriches with metadata."""
    all_discovered_audio_details = []
    if not os.path.isdir(base_dataset_path):
        print(f"Error: Source directory '{base_dataset_path}' not found during scan.")
        return []

    video_id_folders = [d for d in os.listdir(base_dataset_path) if os.path.isdir(os.path.join(base_dataset_path, d))]
    
    for video_id_from_folder in video_id_folders:
        video_id_path = os.path.join(base_dataset_path, video_id_from_folder)
        video_id_key = video_id_from_folder.strip()
        metadata_for_video = video_metadata_map.get(video_id_key, {})
        
        language = metadata_for_video.get('language', 'unknown_language')
        accent = metadata_for_video.get('accent', 'unknown_accent')
        tags = metadata_for_video.get('tags', [])

        potential_chunk_folders = [d for d in os.listdir(video_id_path)
                                   if os.path.isdir(os.path.join(video_id_path, d)) and d.startswith("chunk_")]
        
        for chunk_folder_name in potential_chunk_folders:
            chunk_start_time, chunk_end_time = parse_chunk_folder_name_for_times(chunk_folder_name)
            chunk_folder_path = os.path.join(video_id_path, chunk_folder_name)
            
            noisy_level_folders = [d for d in os.listdir(chunk_folder_path)
                                   if os.path.isdir(os.path.join(chunk_folder_path, d)) and d.startswith("noisy_")]
            
            for noisy_folder_name in noisy_level_folders:
                noisy_folder_path = os.path.join(chunk_folder_path, noisy_folder_name)
                if os.path.isdir(noisy_folder_path):
                    try:
                        files_in_noisy_folder = os.listdir(noisy_folder_path)
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
                                'tags': tags,
                                'language': language,
                                'accent': accent
                            })
    return all_discovered_audio_details

def testcase1(base_dataset_path, 
              tc1_output_base_path, 
              metadata_file_path, 
              total_samples_to_select=100,
              log_file_path="sampled_testcases/TC-1/tc1_log.json",
              use_fixed_selection=False):
    """
    Processes audio files for Test Case 1.
    Supports random selection (noise level 0, language-based) or fixed selection from a log.
    """
    mode_str = "FIXED selection from log" if use_fixed_selection else "RANDOM selection (Noise Level 0, Language-based)"
    print(f"\n--- Starting Test Case 1: {mode_str} ---")
    print(f"Source Dataset: '{base_dataset_path}'")
    print(f"Output Base: '{tc1_output_base_path}'")
    print(f"Metadata File: '{metadata_file_path}'")
    if use_fixed_selection:
        print(f"Using Fixed Selection Log: '{log_file_path}'")
    else:
        print(f"Target Total Samples (Random): {total_samples_to_select}")
        print(f"Log will be saved to: '{log_file_path}'")


    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting TC-1 due to critical errors in loading video metadata.")
        return

    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audio_samples_to_process = []
    
    all_currently_discovered_audio = scan_all_audio_files(base_dataset_path, video_metadata_map)
    if not all_currently_discovered_audio and not use_fixed_selection:
        print(f"No audio files were found in '{base_dataset_path}' during initial scan for random selection. Halting TC-1.")
        return
    
    discovered_audio_map_by_path = {audio['path']: audio for audio in all_currently_discovered_audio}

    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict):
                print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{log_file_path}'. Halting fixed selection.")
                return

            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict):
                    print(f"Warning: Invalid spec found in JSON log for key '{dest_path_key}'. Skipping.")
                    final_report_data_list.append({
                        'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key,
                        'status': 'Skipped - Invalid Log Entry', 'error_message': f'Spec for {dest_path_key} was not a dictionary.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue

                original_path_from_log = spec_from_log.get('original_path')
                processing_category_from_log = spec_from_log.get('language_category')

                if not original_path_from_log or not processing_category_from_log:
                    msg = "missing 'original_path'" if not original_path_from_log else "missing 'language_category'"
                    print(f"Warning: Sample spec (dest: {dest_path_key}) from fixed list is {msg}. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 'original_path': original_path_from_log or 'N/A - Missing in log',
                        'status': f'Skipped - {msg.capitalize()} in Log', 'error_message': f'{msg.capitalize()} for this sample was not found in the JSON log entry.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    audio_samples_to_process.append({**found_detail, '_processing_category': processing_category_from_log})
                else:
                    print(f"Warning: Sample with original path '{original_path_from_log}' from fixed list not found in current dataset scan. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)',
                        'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, test case JSON file '{log_file_path}' not found. Halting.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{log_file_path}'. Halting.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading '{log_file_path}': {e}. Halting.")
            return
    else: 
        print(f"Scanning '{base_dataset_path}' to identify audio files for random selection...")
        
        noise_level_0_files = [f for f in all_currently_discovered_audio if f['noisy_folder'] == 'noisy_0']

        if not noise_level_0_files:
            print(f"No audio files from 'noisy_0' folders were found in '{base_dataset_path}'. Halting TC-1 random selection.")
            return
        print(f"Discovered {len(noise_level_0_files)} audio files from 'noisy_0' folders for categorization.")

        categorized_audios = defaultdict(list)
        target_language_categories = ["English-US", "English-UK", "Cantonese-HK", "Mandarin"]

        for audio_detail in noise_level_0_files:
            lang = audio_detail['language']
            acc = audio_detail['accent']
            category = None

            if lang == 'english':
                if acc == 'uk':
                    category = "English-UK"
                else: 
                    category = "English-US"
            elif lang == 'cantonese':
                category = "Cantonese-HK"
            elif lang == 'mandarin':
                category = "Mandarin"
            
            if category:
                categorized_audios[category].append(audio_detail)

        print("\n--- Audio Distribution by Target Language Category (Noise Level 0) ---")
        for cat in target_language_categories:
            print(f"Category: {cat}, Found files: {len(categorized_audios[cat])}")

        if not target_language_categories:
            print("Error: No target language categories defined for selection.")
            return

        samples_per_category = total_samples_to_select // len(target_language_categories) if target_language_categories else 0
        if samples_per_category == 0 and total_samples_to_select > 0 and target_language_categories :
            print(f"Warning: total_samples_to_select ({total_samples_to_select}) is less than the number of categories ({len(target_language_categories)}). Aiming for at least one sample per category if possible.")
            samples_per_category = 1

        print(f"\n--- Selecting Samples (Target per category: {samples_per_category}) ---")
        
        total_actually_selected = 0
        for category in target_language_categories:
            available_files = categorized_audios[category]
            if not available_files:
                print(f"No files available for category: {category}. Skipping.")
                continue

            num_to_select = min(samples_per_category, len(available_files))
            if num_to_select > 0:
                selected_for_category = random.sample(available_files, num_to_select)
                for item in selected_for_category:
                    audio_samples_to_process.append({**item, '_processing_category': category})
                print(f"Selected {len(selected_for_category)} samples for category: {category}")
                total_actually_selected += len(selected_for_category)
            else:
                print(f"Not enough samples or target is 0 for category: {category}. Selected 0.")
        
        print(f"Total samples selected across all categories: {total_actually_selected}")
        if total_actually_selected == 0:
            print("No samples were selected for random selection. Halting TC-1 file operations.")
            return

    copied_files_count = 0
    print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected samples ---")
    
    processed_copy_keys = set()

    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        processing_category = audio_info_with_context['_processing_category']
        
        target_file_directory = os.path.join(tc1_output_base_path, processing_category)
        
        video_id = audio_info_with_context['video_id']
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys:
            print(f"Info: Skipped duplicate processing for {original_audio_full_path} to {target_audio_path}")
            continue
        processed_copy_keys.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'language_category': processing_category,
            'language_metadata': audio_info_with_context['language'],
            'accent_metadata': audio_info_with_context['accent'],
            'noisy_folder': noisy_folder_ctx,
            'conceptual_filename': audio_info_with_context['filename'],
            'original_filename': original_audio_source_filename,
            'chunk_type': audio_info_with_context['chunk_type'],
            'destination_audio_path': target_audio_path,
            'destination_transcript_path': None,
            'status': 'Pending Copy',
            'error_message': None,
            'processed_timestamp': processed_current_run_timestamp
        }

        try:
            os.makedirs(target_file_directory, exist_ok=True)
        except OSError as e:
            print(f"Error creating directory {target_file_directory}: {e}. Skipping sample {original_audio_full_path}")
            report_item['status'] = 'Skipped - Directory Creation Error'
            report_item['error_message'] = f"Failed to create target directory: {e}"
            final_report_data_list.append(report_item)
            continue
        
        try:
            if not os.path.exists(original_audio_full_path):
                raise FileNotFoundError(f"Source audio file not found: {original_audio_full_path}")

            shutil.copy2(original_audio_full_path, target_audio_path)
            copied_files_count +=1
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

    print("\n--- TC-1 Operation Complete ---")
    print(f"A total of {copied_files_count} audio files (and their VTTs if found) were processed.")
    print(f"Selected audios and transcripts are saved in subfolders under: '{tc1_output_base_path}'")
    
    if final_report_data_list:
        log_desc = f"Test Case 1 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)

def testcase2():
    return
def testcase3():
    return
def testcase4():
    return
def testcase5():
    return
def testcase6():
    return
def testcase7():
    return

def pipeline():
    base_dataset = "chunked_dataset_with_ground_truth"
    metadata_file = "urls.meta.json"
    output_root = "testset"

    tc1_output_path = os.path.join(output_root, "TC-1")
    tc1_log = os.path.join(tc1_output_path, "tc1_selection_log.json")

    print(f"Pipeline starting. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    testcase1(
        base_dataset_path=base_dataset,
        tc1_output_base_path=tc1_output_path,
        metadata_file_path=metadata_file,
        total_samples_to_select=100, 
        log_file_path=tc1_log,
        use_fixed_selection=USE_FIXED_SELECTION
    )
    return

if __name__ == "__main__":
    pipeline()