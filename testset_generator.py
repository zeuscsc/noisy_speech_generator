import os
import random
import shutil
import json
import re
from datetime import datetime
from collections import defaultdict

ENGLISH_NUMBER_WORDS = [
    r'\bzero\b', r'\bone\b', r'\btwo\b', r'\bthree\b', r'\bfour\b', r'\bfive\b',
    r'\bsix\b', r'\bseven\b', r'\beight\b', r'\bnine\b', r'\bten\b',
    r'\beleven\b', r'\btwelve\b', r'\bthirteen\b', r'\bfourteen\b', r'\bfifteen\b',
    r'\bsixteen\b', r'\bseventeen\b', r'\beighteen\b', r'\bnineteen\b',
    r'\btwenty\b', r'\bthirty\b', r'\bforty\b', r'\bfifty\b', r'\bsixty\b',
    r'\bseventy\b', r'\beighty\b', r'\bninety\b',
    r'\bhundred\b', r'\bthousand\b', r'\bmillion\b', r'\bbillion\b'
]

ENGLISH_NUMBER_REGEX = re.compile(r'|'.join(ENGLISH_NUMBER_WORDS), re.IGNORECASE)

COMPREHENSIVE_CHINESE_NUM_CHARS = "零一二三四五六七八九十拾百佰千仟萬万億亿兆兩俩幺壹貳參肆伍陸柒捌玖貮點点元角分厘釐"
CHINESE_NUMBER_REGEX = re.compile(f"[{COMPREHENSIVE_CHINESE_NUM_CHARS}]{{2,}}")

DIGIT_REGEX = re.compile(r'\d+')

def vtt_has_numbers(vtt_file_path, language_hint="unknown"):
    """
    Checks if the VTT file content contains spoken numbers.
    language_hint can be 'english', 'mandarin', 'cantonese' to refine search.
    Returns True if numbers are found, False otherwise.
    """
    if not os.path.isfile(vtt_file_path): 
        return False

    try:
        with open(vtt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read VTT file {vtt_file_path}: {e}")
        return False

    lines = content.splitlines()
    text_lines = []
    for line_idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped == "WEBVTT":
            continue
        if line_stripped.startswith("NOTE"):
            continue
        if "-->" in line_stripped:
            continue
        text_lines.append(line_stripped)

    transcript_text = " ".join(text_lines)
    if not transcript_text.strip():
        return False

    if DIGIT_REGEX.search(transcript_text):
        return True

    lang_lower = language_hint.lower()
    if lang_lower.startswith('english'):
        if ENGLISH_NUMBER_REGEX.search(transcript_text):
            return True
    elif lang_lower in ['mandarin', 'cantonese', 'chinese']: 
        if CHINESE_NUMBER_REGEX.search(transcript_text):
            return True
    return False

def extract_youtube_id_from_url(url_string):
    """Extracts YouTube video ID from various URL formats."""
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

def get_transcript_from_vtt(vtt_file_path):
    """
    Extracts the transcript text from a VTT file, filtering out metadata and timestamps.
    Returns a single string with the transcript or None if an error occurs or file not found.
    """
    if not os.path.isfile(vtt_file_path):
        
        return None
    try:
        with open(vtt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read VTT file {vtt_file_path}: {e}")
        return None

    lines = content.splitlines()
    text_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or \
           line_stripped == "WEBVTT" or \
           line_stripped.startswith("NOTE") or \
           "-->" in line_stripped or \
           line_stripped.startswith("Kind:") or \
           line_stripped.startswith("Language:") or \
           line_stripped.startswith("Region:") or \
           line_stripped.startswith("Style:") or \
           re.match(r"^[\d:.]+$", line_stripped): 
            continue
        
        if line_stripped.startswith("align:") or \
           line_stripped.startswith("line:") or \
           line_stripped.startswith("position:") or \
           line_stripped.startswith("size:") or \
           line_stripped.startswith("vertical:"):
            continue
        
        text_lines.append(line_stripped)
    
    return " ".join(text_lines)

def load_vocabulary_list(vocabulary_file_path):
    """Loads a global vocabulary list from the JSON file (expects a list of strings)."""
    print(f"Attempting to load vocabulary list from: {vocabulary_file_path}")
    if not os.path.isfile(vocabulary_file_path):
        print(f"ERROR: Vocabulary file '{vocabulary_file_path}' not found.")
        return None
    try:
        with open(vocabulary_file_path, 'r', encoding='utf-8') as f:
            vocabulary_data = json.load(f)
        if not isinstance(vocabulary_data, list):
            print(f"ERROR: Vocabulary file '{vocabulary_file_path}' does not contain a list at the root.")
            return None
        
        
        original_count = len(vocabulary_data)
        valid_vocabulary = []
        for item_idx, item in enumerate(vocabulary_data):
            if isinstance(item, str):
                stripped_item = item.strip()
                if stripped_item: 
                    valid_vocabulary.append(stripped_item)
                else:
                    print(f"Warning: Empty string found in vocabulary list at index {item_idx} after stripping. Skipping.")
            else:
                print(f"Warning: Non-string item found in vocabulary list at index {item_idx}: {item}. Skipping this item.")
                
        if len(valid_vocabulary) != original_count:
            print(f"Warning: Some items were filtered from the vocabulary list. Original: {original_count}, Valid: {len(valid_vocabulary)}")

        print(f"Successfully loaded {len(valid_vocabulary)} valid vocabulary terms.")
        return valid_vocabulary
    except json.JSONDecodeError:
        print(f"ERROR: Error decoding JSON from '{vocabulary_file_path}'.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading vocabulary list: {e}")
        return None

def vtt_contains_vocabulary(vtt_file_path, global_vocabulary_list, language_hint="unknown"):
    """
    Checks if the VTT file content contains any word from the global vocabulary list.
    Uses case-insensitive matching. Word boundary usage depends on language_hint.
    """
    if not global_vocabulary_list: 
        return False 

    transcript_text = get_transcript_from_vtt(vtt_file_path)
    if not transcript_text: 
        
        return False 

    lang_lower = language_hint.lower()
    
    
    use_word_boundaries = True
    if lang_lower in ['mandarin', 'cantonese', 'chinese', 'japanese', 'korean']: 
        use_word_boundaries = False

    for vocab_word in global_vocabulary_list:
        if not vocab_word: 
            continue
        
        
        escaped_vocab_word = re.escape(vocab_word)

        if use_word_boundaries:
            pattern = r'\b' + escaped_vocab_word + r'\b'
        else:
            
            
            pattern = escaped_vocab_word
        
        try:
            if re.search(pattern, transcript_text, re.IGNORECASE):
                
                return True
        except re.error as re_e: 
            print(f"Warning: Regex error for vocabulary word '{vocab_word}' with pattern '{pattern}': {re_e}. Skipping this word.")
            continue 
    
    return False

def get_tc5_category_folder(lang_meta, acc_meta):
    """
    Determines the TC5 category folder name based on language and accent.
    Mirrors TC1's categorization for consistency.
    """
    lang_meta = lang_meta.lower()
    acc_meta = acc_meta.lower()

    if lang_meta == 'english':
        if acc_meta == 'uk':
            return "English-UK"
        if acc_meta == 'hk':
            return "English-HK"
        
        return "English-US"
    elif lang_meta == 'cantonese':
        
        
        return "Cantonese-HK"
    elif lang_meta == 'mandarin':
        
        return "Mandarin"
    return None 

def get_tc1_style_language_category(lang_meta, acc_meta):
    """
    Determines the base language category folder name (e.g., "English-US", "Cantonese-HK")
    based on language and accent metadata, consistent with TC1.
    """
    lang_meta_lower = lang_meta.lower()
    acc_meta_lower = acc_meta.lower()

    if lang_meta_lower == 'english':
        if acc_meta_lower == 'uk':
            return "English-UK"
        elif acc_meta_lower == 'hk':
            return "English-HK"
        else:  
            return "English-US"
    elif lang_meta_lower == 'cantonese':
        return "Cantonese-HK" 
    elif lang_meta_lower == 'mandarin':
        return "Mandarin" 
    return None 


def testcase1(base_dataset_path, 
              tc1_output_base_path, 
              metadata_file_path, 
              total_samples_to_select=100,
              log_file_path="sampled_testcases/TC-1/tc1_log.json",
              use_fixed_selection=False):
    """
    Processes audio files for Test Case 1.
    Selects based on language (using get_tc1_style_language_category), 
    and further categorizes into "-Numbers" if VTT contains numbers.
    Only processes 'noisy_0' files for new selections.
    Supports random selection or fixed selection from a log.
    """
    mode_str = "FIXED selection from log" if use_fixed_selection else "RANDOM selection (Noise Level 0, Language & Numbers based)"
    print(f"\n--- Starting Test Case 1: {mode_str} ---")
    

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

    
    tc1_base_lang_folders = ["English-US", "English-UK", "English-HK", "Cantonese-HK", "Mandarin"]
    
    
    active_target_categories_tc1 = []
    for base_cat_name in tc1_base_lang_folders:
        active_target_categories_tc1.append(base_cat_name)
        active_target_categories_tc1.append(f"{base_cat_name}-Numbers")


    if use_fixed_selection:
        if not os.path.exists(log_file_path):
            use_fixed_selection = False
    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List for TC-1 from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict):
                print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{log_file_path}'. Halting fixed selection.")
                return

            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from TC-1 JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict):
                    
                    final_report_data_list.append({
                        'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key,
                        'status': 'Skipped - Invalid Log Entry', 'error_message': f'Spec for {dest_path_key} was not a dictionary.',
                        'processed_timestamp': processed_current_run_timestamp,
                        'language_category': spec_from_log.get('language_category', 'UnknownLogCategory')
                    })
                    continue

                original_path_from_log = spec_from_log.get('original_path')
                
                tc1_processing_category_from_log = spec_from_log.get('language_category') 

                if not original_path_from_log or not tc1_processing_category_from_log:
                    
                    msg = "missing 'original_path'" if not original_path_from_log else "missing 'language_category'"
                    final_report_data_list.append({
                        **spec_from_log, 'original_path': original_path_from_log or 'N/A - Missing in log',
                        'status': f'Skipped - {msg.capitalize()} in Log', 
                        'error_message': f'{msg.capitalize()} for this sample was not found in the JSON log entry.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                
                if tc1_processing_category_from_log not in active_target_categories_tc1:
                    print(f"Warning: Logged language_category '{tc1_processing_category_from_log}' for '{original_path_from_log}' "
                          f"is not one of the active TC1 target categories. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 
                        'status': 'Skipped - Logged Category Not Targeted for TC1',
                        'error_message': f"Logged category '{tc1_processing_category_from_log}' is not in active TC1 targets.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    
                    audio_samples_to_process.append({**found_detail, '_processing_category_path': tc1_processing_category_from_log})
                else:
                    
                    final_report_data_list.append({
                        **spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)',
                        'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, TC-1 log file '{log_file_path}' not found. Halting.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from TC-1 log file '{log_file_path}'. Halting.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading TC-1 log '{log_file_path}': {e}. Halting.")
            return
    else: 
        print(f"Scanning '{base_dataset_path}' to identify audio files for random selection (TC-1)...")
        
        
        noise_level_0_files = [f for f in all_currently_discovered_audio if f['noisy_folder'] == 'noisy_0']

        if not noise_level_0_files:
            print(f"No audio files from 'noisy_0' folders were found in '{base_dataset_path}'. Halting TC-1 random selection.")
            return
        print(f"Discovered {len(noise_level_0_files)} audio files from 'noisy_0' folders for TC-1 categorization.")

        categorized_audios_tc1 = defaultdict(list)
        
        for audio_detail in noise_level_0_files:
            lang_meta = audio_detail['language'] 
            acc_meta = audio_detail['accent']   
            
            base_language_folder = get_tc1_style_language_category(lang_meta, acc_meta)
            
            if base_language_folder: 
                final_assigned_category_tc1 = base_language_folder
                vtt_file_path = os.path.splitext(audio_detail['path'])[0] + ".vtt"
                if vtt_has_numbers(vtt_file_path, language_hint=lang_meta):
                    final_assigned_category_tc1 = f"{base_language_folder}-Numbers"
                
                
                if final_assigned_category_tc1 in active_target_categories_tc1:
                    categorized_audios_tc1[final_assigned_category_tc1].append(audio_detail)
            

        print("\n--- Audio Distribution by Target Category for TC-1 (Noise Level 0) ---")
        for cat_name in active_target_categories_tc1: 
            print(f"Category: {cat_name}, Found files: {len(categorized_audios_tc1[cat_name])}")

        
        actual_categories_with_files_tc1 = [
            cat_name for cat_name in active_target_categories_tc1 if categorized_audios_tc1[cat_name]
        ]

        if not actual_categories_with_files_tc1:
            print("No audio files found matching any active TC-1 criteria after categorization. Halting selection.")
            return

        samples_per_category = total_samples_to_select // len(actual_categories_with_files_tc1) if actual_categories_with_files_tc1 else 0
        if samples_per_category == 0 and total_samples_to_select > 0 and actual_categories_with_files_tc1:
            print(f"Warning: total_samples_to_select ({total_samples_to_select}) for TC-1 is less than the number of active categories with files ({len(actual_categories_with_files_tc1)}). Aiming for at least one sample per active category if possible.")
            samples_per_category = 1 

        print(f"\n--- Selecting Samples for TC-1 (Target per active category: {samples_per_category}) ---")
        
        total_actually_selected = 0
        
        for category_name_tc1 in actual_categories_with_files_tc1: 
            if total_actually_selected >= total_samples_to_select: break
            available_files = categorized_audios_tc1[category_name_tc1]
            num_to_select_for_this_cat = min(samples_per_category, len(available_files), total_samples_to_select - total_actually_selected)
            
            if num_to_select_for_this_cat > 0:
                selected_for_category = random.sample(available_files, num_to_select_for_this_cat)
                for item in selected_for_category:
                    audio_samples_to_process.append({**item, '_processing_category_path': category_name_tc1})
                    if item in available_files: available_files.remove(item) 
                total_actually_selected += len(selected_for_category)
        
        
        if total_actually_selected < total_samples_to_select:
            remaining_quota = total_samples_to_select - total_actually_selected
            all_remaining_eligible_samples_tc1 = []
            shuffled_active_cats_tc1 = list(actual_categories_with_files_tc1)
            random.shuffle(shuffled_active_cats_tc1)
            for category_name_tc1 in shuffled_active_cats_tc1:
                for item in categorized_audios_tc1[category_name_tc1]: 
                     all_remaining_eligible_samples_tc1.append({**item, '_processing_category_path': category_name_tc1})
            
            if all_remaining_eligible_samples_tc1:
                num_to_select_fill_up = min(remaining_quota, len(all_remaining_eligible_samples_tc1))
                if num_to_select_fill_up > 0:
                    random.shuffle(all_remaining_eligible_samples_tc1)
                    fill_up_selected = all_remaining_eligible_samples_tc1[:num_to_select_fill_up]
                    audio_samples_to_process.extend(fill_up_selected) 
                    total_actually_selected += len(fill_up_selected)

        print(f"Total samples selected for TC-1: {total_actually_selected}")
        if total_actually_selected == 0 and total_samples_to_select > 0:
            print("No samples were selected for TC-1 random selection. Halting file operations.")
            return
        elif total_actually_selected == 0 and total_samples_to_select == 0:
            print("Target samples to select for TC-1 is 0. No files will be processed.")
            return


    
    copied_files_count = 0
    if not audio_samples_to_process:
        print("No samples in processing list for TC-1. File operations skipped.")
    else:
        print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected TC-1 samples ---")
    
    processed_copy_keys_tc1 = set() 

    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        
        tc1_target_folder_name = audio_info_with_context['_processing_category_path'] 
        
        
        target_file_directory = os.path.join(tc1_output_base_path, tc1_target_folder_name)
        
        video_id = audio_info_with_context['video_id']
        
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys_tc1:
            continue
        processed_copy_keys_tc1.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'language_category': tc1_target_folder_name, 
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
                    print(f"Warning: Copied audio {target_audio_path} but failed to copy VTT {original_transcript_full_path}: {e_vtt}")
            else:
                report_item['status'] = 'Audio Copied, VTT Not Found'
        except Exception as e_audio:
            report_item['status'] = 'Error Copying Audio'
            report_item['error_message'] = f"Audio copy error: {str(e_audio)}"
            print(f"Error copying audio file {original_audio_full_path} to {target_audio_path}: {e_audio}")
        
        final_report_data_list.append(report_item)


    print("\n--- TC-1 Operation Complete ---")
    print(f"A total of {copied_files_count} audio files (and their VTTs if found) were processed for TC-1.")
    print(f"Selected TC-1 audios and transcripts are saved in subfolders under: '{tc1_output_base_path}'")
    
    if final_report_data_list: 
        log_desc = f"Test Case 1 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)
    return

def testcase2(base_dataset_path,
              tc2_output_base_path,
              metadata_file_path,
              log_file_path="sampled_testcases/TC-2/tc2_log.json",
              use_fixed_selection=False,
              total_samples_for_tc2=100):
    """
    Processes audio files for Test Case 2:
    - Selects files based on specific language & accent combinations from 'noisy_0' folders.
    - Aims to select a total of 'total_samples_for_tc2', distributed among categories.
    - Supports new selection or fixed selection from a log.
    - Copies selected MP3s and their VTTs to the new structure.
    """
    TC2_TARGET_CONDITIONS = [
        {"lang": "cantonese", "acc": "mandarin", "folder_name": "Cantonese_Mandarin_Accent", "description": "Cantonese speech with Mandarin accent"},
        {"lang": "mandarin", "acc": "cantonese", "folder_name": "Mandarin_Cantonese_Accent", "description": "Mandarin speech with Cantonese accent"},
        {"lang": "english", "acc": "south east asian", "folder_name": "English_SouthEastAsian_Accent", "description": "English speech with South East Asian accent"},
        {"lang": "english", "acc": "indian", "folder_name": "English_Indian_Accent", "description": "English speech with Indian accent"},
    ]
    mode_str = "FIXED selection from log" if use_fixed_selection else f"NEW selection (Noise Level 0, Target total samples: {total_samples_for_tc2})"
    print(f"\n--- Starting Test Case 2: {mode_str} ---")
    print(f"Source Dataset: '{base_dataset_path}'")
    print(f"Output Base: '{tc2_output_base_path}'")
    print(f"Metadata File: '{metadata_file_path}'")
    if use_fixed_selection:
        if not os.path.exists(log_file_path):
            use_fixed_selection = False
    if use_fixed_selection:
        print(f"Using Fixed Selection Log: '{log_file_path}'")
    else:
        print(f"Log will be saved to: '{log_file_path}'")

    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting TC-2 due to critical errors in loading video metadata.")
        return

    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audio_samples_to_process = []
    
    all_currently_discovered_audio_full_scan = scan_all_audio_files(base_dataset_path, video_metadata_map)
    if not all_currently_discovered_audio_full_scan and not use_fixed_selection:
        print(f"No audio files were found in '{base_dataset_path}' during initial scan. Halting TC-2.")
        return
    
    
    discovered_audio_map_by_path = {audio['path']: audio for audio in all_currently_discovered_audio_full_scan}

    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List for TC-2 from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict):
                print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{log_file_path}'. Halting fixed selection.")
                return

            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from TC-2 JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict):
                    print(f"Warning: Invalid spec found in TC-2 JSON log for key '{dest_path_key}'. Skipping.")
                    final_report_data_list.append({
                        'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key,
                        'status': 'Skipped - Invalid Log Entry', 'error_message': f'Spec for {dest_path_key} was not a dictionary.',
                        'processed_timestamp': processed_current_run_timestamp, 'tc2_category': spec_from_log.get('tc2_category', 'Unknown')
                    })
                    continue

                original_path_from_log = spec_from_log.get('original_path')
                processing_category_from_log = spec_from_log.get('tc2_category') 

                if not original_path_from_log or not processing_category_from_log:
                    msg = "missing 'original_path'" if not original_path_from_log else "missing 'tc2_category'"
                    print(f"Warning: Sample spec (dest: {dest_path_key}) from TC-2 fixed list is {msg}. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 'original_path': original_path_from_log or 'N/A - Missing in log',
                        'status': f'Skipped - {msg.capitalize()} in Log', 'error_message': f'{msg.capitalize()} for this sample was not found in the JSON log entry.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    audio_samples_to_process.append({**found_detail, '_processing_category_name': processing_category_from_log})
                else:
                    print(f"Warning: Sample original path '{original_path_from_log}' from TC-2 fixed list not found in current dataset scan. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)',
                        'error_message': f"Original audio '{original_path_from_log}' specified in TC-2 fixed list not present in scanned dataset.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, TC-2 log file '{log_file_path}' not found. Halting.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from TC-2 log file '{log_file_path}'. Halting.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading TC-2 log '{log_file_path}': {e}. Halting.")
            return
    else: 
        print(f"\n--- Identifying and Selecting Samples for TC-2 from 'noisy_0' folders based on accent criteria (Target total: {total_samples_for_tc2}) ---")
        
        
        noise_level_0_files = [f for f in all_currently_discovered_audio_full_scan if f['noisy_folder'] == 'noisy_0']

        if not noise_level_0_files:
            print(f"No audio files from 'noisy_0' folders were found in '{base_dataset_path}'. Halting TC-2 random selection.")
            return
        print(f"Discovered {len(noise_level_0_files)} audio files from 'noisy_0' folders for TC-2 categorization.")

        categorized_audios_tc2 = defaultdict(list)

        
        for audio_detail in noise_level_0_files: 
            lang = audio_detail['language'].lower()
            acc = audio_detail['accent'].lower()
            
            for condition in TC2_TARGET_CONDITIONS:
                if lang == condition["lang"] and acc == condition["acc"]:
                    categorized_audios_tc2[condition["folder_name"]].append(audio_detail)
                    break 
        
        print("\n--- Audio Distribution by TC-2 Target Accent Category (from Noise Level 0) ---")
        active_categories_with_files = []
        for condition in TC2_TARGET_CONDITIONS:
            folder_name = condition["folder_name"]
            count = len(categorized_audios_tc2[folder_name])
            print(f"Category: {folder_name} ({condition['description']}), Found files: {count}")
            if count > 0:
                active_categories_with_files.append(folder_name)
        
        if not active_categories_with_files:
            print("No audio files from 'noisy_0' folders found matching any TC-2 criteria. Halting selection.")
            return

        samples_to_aim_per_active_category = total_samples_for_tc2 // len(active_categories_with_files) if active_categories_with_files else 0
        if samples_to_aim_per_active_category == 0 and total_samples_for_tc2 > 0 and active_categories_with_files:
             print(f"Warning: total_samples_for_tc2 ({total_samples_for_tc2}) is less than the number of active categories ({len(active_categories_with_files)}). Aiming for at least one sample per active category if possible.")
             samples_to_aim_per_active_category = 1

        print(f"\n--- Selecting Samples (Target per active category: ~{samples_to_aim_per_active_category}) ---")
        total_actually_selected = 0
        remaining_to_select_overall = total_samples_for_tc2
        temp_selected_for_processing = []

        
        
        for category_name in active_categories_with_files:
            if remaining_to_select_overall <= 0: break
            available_files = categorized_audios_tc2[category_name]
            num_to_select_this_pass = min(samples_to_aim_per_active_category, len(available_files), remaining_to_select_overall)
            
            if num_to_select_this_pass > 0:
                selected_for_category = random.sample(available_files, num_to_select_this_pass)
                for item in selected_for_category:
                    temp_selected_for_processing.append({**item, '_processing_category_name': category_name})
                
                total_actually_selected += len(selected_for_category)
                remaining_to_select_overall -= len(selected_for_category)
                
                for item_to_remove in selected_for_category:
                    if item_to_remove in available_files:
                        available_files.remove(item_to_remove)

        
        
        if remaining_to_select_overall > 0 and total_actually_selected < total_samples_for_tc2:
            print(f"\n--- Attempting to select remaining {remaining_to_select_overall} samples to meet overall target for TC-2 ---")
            
            random.shuffle(active_categories_with_files) 
            for category_name in active_categories_with_files:
                if remaining_to_select_overall <= 0: break
                available_files = categorized_audios_tc2[category_name] 
                num_to_select_fill_up = min(remaining_to_select_overall, len(available_files))

                if num_to_select_fill_up > 0:
                    selected_for_category_fill_up = random.sample(available_files, num_to_select_fill_up)
                    for item in selected_for_category_fill_up:
                          temp_selected_for_processing.append({**item, '_processing_category_name': category_name})
                    
                    total_actually_selected += len(selected_for_category_fill_up)
                    remaining_to_select_overall -= len(selected_for_category_fill_up)
                    for item_to_remove in selected_for_category_fill_up: 
                        if item_to_remove in available_files:
                            available_files.remove(item_to_remove)
        
        audio_samples_to_process = temp_selected_for_processing
        print(f"\nTotal samples finally selected for TC-2 across all categories: {total_actually_selected}")
        if total_actually_selected == 0:
            print("No samples were selected for TC-2. Halting file operations.")
            return

    copied_files_count = 0
    print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected TC-2 samples ---")
    
    processed_copy_keys = set()

    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        processing_category_name = audio_info_with_context['_processing_category_name']
        
        target_file_directory = os.path.join(tc2_output_base_path, processing_category_name)
        
        video_id = audio_info_with_context['video_id']
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys:
            
            continue
        processed_copy_keys.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'tc2_category': processing_category_name, 
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

    print("\n--- TC-2 Operation Complete ---")
    print(f"A total of {copied_files_count} audio files (and their VTTs if found) were processed for TC-2.")
    print(f"Selected TC-2 audios and transcripts are saved in subfolders under: '{tc2_output_base_path}'")
    
    if final_report_data_list:
        log_desc = f"Test Case 2 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)
    return

def testcase3(base_dataset_path,
              tc3_output_base_path,
              metadata_file_path,
              vocabulary_file_path, 
              log_file_path="sampled_testcases/TC-3/tc3_log.json",
              use_fixed_selection=False,
              total_samples_to_select=50):
    """
    Processes audio files for Test Case 3:
    - Selects audio chunks from 'noisy_0' folders.
    - The VTT of the chunk must contain at least one word from the global vocabulary list
      loaded from 'vocabulary_file_path'.
    - Organizes output into language-specific subfolders (English, Cantonese, Mandarin).
      Files with other languages are skipped for new selections.
    - Aims to select 'total_samples_to_select' evenly distributed across target languages.
    - Supports new random selection or fixed selection from a log.
    """
    mode_str = "FIXED selection from log" if use_fixed_selection else f"NEW selection (Noisy 0, Global Vocabulary, Language Folders, Even Distribution, Target: {total_samples_to_select})"
    print(f"\n--- Starting Test Case 3: {mode_str} ---")
    print(f"Source Dataset: '{base_dataset_path}'")
    print(f"Output Base: '{tc3_output_base_path}'")
    print(f"Metadata File: '{metadata_file_path}'")
    print(f"Vocabulary File: '{vocabulary_file_path}'")

    TARGET_LANGUAGE_FOLDERS = { 
        "english": "English",
        "cantonese": "Cantonese",
        "mandarin": "Mandarin"
    }

    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting TC-3 due to critical errors in loading video metadata.")
        return

    global_vocabulary = load_vocabulary_list(vocabulary_file_path)
    if global_vocabulary is None: 
        print("Halting TC-3 due to critical errors in loading the global vocabulary list.")
        return
    if not global_vocabulary and not use_fixed_selection: 
        print("Warning: The loaded global vocabulary list is empty. No samples will be selected for TC-3 new selection.")
        return


    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audio_samples_to_process = []
    
    all_currently_discovered_audio = scan_all_audio_files(base_dataset_path, video_metadata_map)
    if not all_currently_discovered_audio and not use_fixed_selection:
        print(f"No audio files were found in '{base_dataset_path}' during initial scan. Halting TC-3.")
        return
    
    discovered_audio_map_by_path = {audio['path']: audio for audio in all_currently_discovered_audio}
    
    if use_fixed_selection:
        if not os.path.exists(log_file_path):
            use_fixed_selection = False
    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List for TC-3 from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict):
                print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{log_file_path}'. Halting fixed selection.")
                return

            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from TC-3 JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict):
                    final_report_data_list.append({
                        'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key,
                        'status': 'Skipped - Invalid Log Entry', 
                        'error_message': f'Spec for {dest_path_key} was not a dictionary.',
                        'processed_timestamp': processed_current_run_timestamp, 
                        'tc3_category': spec_from_log.get('tc3_category', 'UnknownLogCategory') 
                    })
                    continue

                original_path_from_log = spec_from_log.get('original_path')
                logged_tc3_folder_name = spec_from_log.get('tc3_category') 

                if not original_path_from_log:
                    final_report_data_list.append({
                        **spec_from_log, 'original_path': 'N/A - Missing in log',
                        'status': 'Skipped - Missing Original Path in Log', 
                        'error_message': 'Original path not found in log entry.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                if logged_tc3_folder_name not in TARGET_LANGUAGE_FOLDERS.values():
                    print(f"Warning: Logged tc3_category '{logged_tc3_folder_name}' for '{original_path_from_log}' is not one of the target language folders ({list(TARGET_LANGUAGE_FOLDERS.values())}). Skipping this sample from fixed log.")
                    final_report_data_list.append({
                        **spec_from_log, 
                        'status': 'Skipped - Logged Category Not Targeted',
                        'error_message': f"Logged category '{logged_tc3_folder_name}' is not in {list(TARGET_LANGUAGE_FOLDERS.values())}.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    audio_samples_to_process.append({**found_detail, '_processing_category_path': logged_tc3_folder_name})
                else:
                    final_report_data_list.append({
                        **spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)',
                        'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, TC-3 log file '{log_file_path}' not found. Halting.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from TC-3 log file '{log_file_path}'. Halting.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading TC-3 log '{log_file_path}': {e}. Halting.")
            return

    else: 
        print(f"\n--- Identifying and Selecting Samples for TC-3 (Noisy 0, Global Vocabulary, Even Distribution) ---")
        
        categorized_eligible_audios = defaultdict(list)
        if not global_vocabulary: 
            print("Global vocabulary list is empty. No files will be selected for new selection in TC-3.")
        else:
            for audio_detail in all_currently_discovered_audio:
                if audio_detail['noisy_folder'] == 'noisy_0':
                    lang_meta = audio_detail.get('language', 'unknown').lower()
                    if lang_meta in TARGET_LANGUAGE_FOLDERS: 
                        vtt_file_path = os.path.splitext(audio_detail['path'])[0] + ".vtt"
                        
                        if vtt_contains_vocabulary(vtt_file_path, global_vocabulary, language_hint=lang_meta):
                            language_folder_name = TARGET_LANGUAGE_FOLDERS[lang_meta]
                            categorized_eligible_audios[language_folder_name].append(audio_detail)
        
        active_language_categories_with_files = [
            cat for cat in TARGET_LANGUAGE_FOLDERS.values() if categorized_eligible_audios[cat]
        ]

        if not active_language_categories_with_files:
            print("No audio files found matching TC-3 criteria (target languages with vocabulary). Halting selection.")
            return

        print("\n--- Audio Distribution by Target Language for TC-3 (Eligible Files) ---")
        for lang_folder in TARGET_LANGUAGE_FOLDERS.values(): 
            count = len(categorized_eligible_audios[lang_folder])
            print(f"Language Category: {lang_folder}, Found eligible files: {count}")
        
        total_eligible_count = sum(len(files) for files in categorized_eligible_audios.values())
        if total_eligible_count == 0 : 
            print("No eligible files found across all target languages. Halting selection.")
            return

        samples_to_aim_per_active_category = 0
        if active_language_categories_with_files: 
            samples_to_aim_per_active_category = total_samples_to_select // len(active_language_categories_with_files)
        
        if samples_to_aim_per_active_category == 0 and total_samples_to_select > 0 and active_language_categories_with_files:
            print(f"Warning: total_samples_to_select ({total_samples_to_select}) is less than the number of active language categories ({len(active_language_categories_with_files)}). Aiming for at least one sample per active category if possible.")
            samples_to_aim_per_active_category = 1
        
        print(f"\n--- Selecting Samples (Target per active language category: ~{samples_to_aim_per_active_category}, Overall target: {total_samples_to_select}) ---")
        
        total_actually_selected = 0
        for lang_folder_name in TARGET_LANGUAGE_FOLDERS.values(): 
            if lang_folder_name not in active_language_categories_with_files:
                continue 
            if total_actually_selected >= total_samples_to_select: break

            available_files = categorized_eligible_audios[lang_folder_name]
            num_to_select_this_pass = min(samples_to_aim_per_active_category, len(available_files), total_samples_to_select - total_actually_selected)
            
            if num_to_select_this_pass > 0:
                selected_for_category = random.sample(available_files, num_to_select_this_pass)
                for item in selected_for_category:
                    audio_samples_to_process.append({**item, '_processing_category_path': lang_folder_name})
                    if item in available_files: available_files.remove(item) 
                total_actually_selected += len(selected_for_category)
        
        if total_actually_selected < total_samples_to_select:
            all_remaining_eligible_samples_with_cat = []
            shuffled_active_categories = list(active_language_categories_with_files) 
            random.shuffle(shuffled_active_categories) 

            for lang_folder_name in shuffled_active_categories:
                for item in categorized_eligible_audios[lang_folder_name]: 
                    all_remaining_eligible_samples_with_cat.append(
                        {**item, '_processing_category_path': lang_folder_name}
                    )
            
            if all_remaining_eligible_samples_with_cat:
                num_to_select_fill_up = min(total_samples_to_select - total_actually_selected, len(all_remaining_eligible_samples_with_cat))
                if num_to_select_fill_up > 0:
                    random.shuffle(all_remaining_eligible_samples_with_cat)
                    fill_up_selected_items = all_remaining_eligible_samples_with_cat[:num_to_select_fill_up]
                    audio_samples_to_process.extend(fill_up_selected_items)
                    total_actually_selected += len(fill_up_selected_items)
                    
        print(f"\nTotal samples finally selected for TC-3 across all languages: {total_actually_selected}")
        if total_actually_selected == 0 and total_samples_to_select > 0:
            print("No samples were ultimately selected for TC-3 (e.g., no eligible files or target was 0). Halting file operations.")
            return
        elif total_actually_selected == 0 and total_samples_to_select == 0:
            print("Target samples to select for TC-3 is 0. No files will be processed.")
            return
        elif total_actually_selected < total_samples_to_select:
            print(f"Warning: Selected {total_actually_selected} samples, which is less than the target {total_samples_to_select} due to insufficient eligible files.")


    copied_files_count = 0
    if not audio_samples_to_process: 
        print("No samples in the processing list for TC-3. File operations will be skipped.")
    else:
        print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected TC-3 samples ---")
    
    processed_copy_keys = set() 

    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        language_folder_name = audio_info_with_context['_processing_category_path'] 
        
        target_file_directory = os.path.join(tc3_output_base_path, language_folder_name)
        
        video_id = audio_info_with_context['video_id']
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys:
            continue
        processed_copy_keys.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'tc3_category': language_folder_name, 
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

    print("\n--- TC-3 Operation Complete ---")
    if copied_files_count > 0 or (use_fixed_selection and len(audio_samples_to_process) > 0) : 
        print(f"A total of {copied_files_count} audio files (and their VTTs if found) were newly copied for TC-3.")
        print(f"Selected TC-3 audios and transcripts are saved directly in language-specific folders under: '{tc3_output_base_path}'")
    elif not use_fixed_selection and total_samples_to_select > 0 :
         print(f"No files met all criteria for TC-3 or none were selected from the eligible pool.")


    if final_report_data_list: 
        log_desc = f"Test Case 3 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)
    return

def testcase4():
    return

def testcase5(base_dataset_path,
              tc5_output_base_path,
              metadata_file_path,
              vocabulary_file_path, 
              log_file_path="sampled_testcases/TC-5/tc5_log.json",
              use_fixed_selection=False,
              total_samples_to_select=50):
    """
    Processes audio files for Test Case 5 (Profanity Filter):
    - Selects audio chunks from 'noisy_0' folders.
    - The VTT of the chunk must contain at least one word from the vocabulary list
      (e.g., "vocabulary.profanity.json").
    - Organizes output into subfolders: "English-US", "English-UK", "English-HK", 
      "Cantonese-HK", and "Mandarin".
    - Only audio files matching these language/accent criteria are considered for new selections.
    - Aims to select 'total_samples_to_select' samples in total from these categories.
    - Supports new random selection or fixed selection from a log.
    """
    
    TC5_TARGET_OUTPUT_FOLDERS = ["English-US", "English-UK", "English-HK", "Cantonese-HK", "Mandarin"]
    
    mode_str = "FIXED selection from log" if use_fixed_selection else f"NEW selection (Noisy 0, Profanity Vocab, Target Langs, Target: {total_samples_to_select})"
    print(f"\n--- Starting Test Case 5: {mode_str} ---")
    print(f"Source Dataset: '{base_dataset_path}'")
    print(f"Output Base: '{tc5_output_base_path}'")
    print(f"Metadata File: '{metadata_file_path}'")
    print(f"Vocabulary File (for TC5 - Profanity): '{vocabulary_file_path}'")


    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting TC-5 due to critical errors in loading video metadata.")
        return

    profanity_vocabulary = load_vocabulary_list(vocabulary_file_path)
    if profanity_vocabulary is None: 
        print("Halting TC-5 due to critical errors in loading the profanity vocabulary list.")
        return
    if not profanity_vocabulary and not use_fixed_selection: 
        print("Warning: The loaded profanity vocabulary list for TC-5 is empty. No samples will be selected for TC-5 new selection.")
        return 

    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audio_samples_to_process = []
    
    all_currently_discovered_audio = scan_all_audio_files(base_dataset_path, video_metadata_map)
    if not all_currently_discovered_audio and not use_fixed_selection:
        print(f"No audio files were found in '{base_dataset_path}' during initial scan. Halting TC-5.")
        return
    
    discovered_audio_map_by_path = {audio['path']: audio for audio in all_currently_discovered_audio}
    
    if use_fixed_selection:
        if not os.path.exists(log_file_path):
            use_fixed_selection = False
    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List for TC-5 from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict):
                print(f"Error: Key 'samples_by_destination_path' not found or not a dictionary in '{log_file_path}'. Halting fixed selection.")
                return

            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from TC-5 JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict):
                    final_report_data_list.append({
                        'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key,
                        'status': 'Skipped - Invalid Log Entry', 
                        'error_message': f'Spec for {dest_path_key} was not a dictionary.',
                        'processed_timestamp': processed_current_run_timestamp, 
                        'tc5_category': spec_from_log.get('tc5_category', 'UnknownLogCategory') 
                    })
                    continue

                original_path_from_log = spec_from_log.get('original_path')
                logged_tc5_folder_name = spec_from_log.get('tc5_category')

                if not original_path_from_log:
                    final_report_data_list.append({
                        **spec_from_log, 'original_path': 'N/A - Missing in log',
                        'status': 'Skipped - Missing Original Path in Log', 
                        'error_message': 'Original path not found in log entry.',
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                if logged_tc5_folder_name not in TC5_TARGET_OUTPUT_FOLDERS:
                    print(f"Warning: Logged tc5_category '{logged_tc5_folder_name}' for '{original_path_from_log}' is not one of the current TC-5 target folders: {TC5_TARGET_OUTPUT_FOLDERS}. Skipping.")
                    final_report_data_list.append({
                        **spec_from_log, 
                        'status': 'Skipped - Logged Category Not Targeted for TC5',
                        'error_message': f"Logged category '{logged_tc5_folder_name}' not in {TC5_TARGET_OUTPUT_FOLDERS}.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
                    continue
                
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    lang_meta_detail = found_detail.get('language', 'unknown')
                    acc_meta_detail = found_detail.get('accent', 'unknown_accent')
                    category_from_current_meta = get_tc5_category_folder(lang_meta_detail, acc_meta_detail)

                    if category_from_current_meta != logged_tc5_folder_name:
                        print(f"Warning: For '{original_path_from_log}', logged TC5 category is '{logged_tc5_folder_name}', "
                              f"but current metadata (lang='{lang_meta_detail}', acc='{acc_meta_detail}') maps to '{category_from_current_meta}'. "
                              f"Proceeding with logged category.")
                    
                    audio_samples_to_process.append({**found_detail, '_processing_category_path': logged_tc5_folder_name})
                else:
                    final_report_data_list.append({
                        **spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)',
                        'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.",
                        'processed_timestamp': processed_current_run_timestamp
                    })
        except FileNotFoundError:
            print(f"Error: Fixed selection mode, TC-5 log file '{log_file_path}' not found. Halting.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from TC-5 log file '{log_file_path}'. Halting.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while loading TC-5 log '{log_file_path}': {e}. Halting.")
            return
    else: 
        print(f"\n--- Identifying and Selecting Samples for TC-5 (Noisy 0, Profanity Vocabulary, Target Languages) ---")
        
        eligible_audios_by_category_tc5 = defaultdict(list)
        if not profanity_vocabulary: 
             print("Profanity vocabulary list for TC-5 is empty. No files will be selected.")
        else:
            for audio_detail in all_currently_discovered_audio:
                if audio_detail['noisy_folder'] == 'noisy_0':
                    lang_meta = audio_detail.get('language', 'unknown') 
                    acc_meta = audio_detail.get('accent', 'unknown_accent')
                    
                    assigned_category_folder = get_tc5_category_folder(lang_meta, acc_meta)
                    
                    if assigned_category_folder and assigned_category_folder in TC5_TARGET_OUTPUT_FOLDERS:
                        vtt_file_path = os.path.splitext(audio_detail['path'])[0] + ".vtt"
                        
                        if vtt_contains_vocabulary(vtt_file_path, profanity_vocabulary, language_hint=lang_meta):
                            eligible_audios_by_category_tc5[assigned_category_folder].append(audio_detail)
        
        print("\n--- Audio Distribution by Target Category for TC-5 (Eligible Profanity Files) ---")
        total_eligible_tc5_files = 0
        for folder_name in TC5_TARGET_OUTPUT_FOLDERS:
            count = len(eligible_audios_by_category_tc5[folder_name])
            print(f"Category: {folder_name}, Found eligible profanity files: {count}")
            total_eligible_tc5_files += count

        if total_eligible_tc5_files == 0:
            print(f"No audio files found matching TC-5 criteria (target languages with profanity). Halting selection.")
            return
        
        all_eligible_samples_for_selection_tc5 = []
        for folder_name in TC5_TARGET_OUTPUT_FOLDERS:
            for item in eligible_audios_by_category_tc5[folder_name]:
                all_eligible_samples_for_selection_tc5.append({**item, '_processing_category_path': folder_name})
        
        num_to_select = min(total_samples_to_select, len(all_eligible_samples_for_selection_tc5))
        
        if num_to_select > 0:
            random.shuffle(all_eligible_samples_for_selection_tc5) 
            selected_samples = all_eligible_samples_for_selection_tc5[:num_to_select]
            audio_samples_to_process.extend(selected_samples)
            print(f"Selected {len(selected_samples)} samples for TC-5 across target categories.")
        else:
            print("No samples to select for TC-5 based on current count and target (or empty vocabulary).")
            return 

        if not audio_samples_to_process and total_samples_to_select > 0 :
              print("No samples were ultimately selected for TC-5. Halting file operations.")
              return
        elif not audio_samples_to_process and total_samples_to_select == 0:
              print("Target samples to select for TC-5 is 0. No files will be processed.")
              return


    copied_files_count = 0
    if not audio_samples_to_process: 
        print("No samples in the processing list for TC-5. File operations will be skipped.")
    else:
        print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected TC-5 samples ---")
    
    processed_copy_keys = set() 

    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        target_category_folder_name = audio_info_with_context['_processing_category_path'] 
        
        target_file_directory = os.path.join(tc5_output_base_path, target_category_folder_name)
        
        video_id = audio_info_with_context['video_id']
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys:
            continue
        processed_copy_keys.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'tc5_category': target_category_folder_name, 
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

    print("\n--- TC-5 Operation Complete ---")
    if copied_files_count > 0 or (use_fixed_selection and len(audio_samples_to_process) > 0) : 
        print(f"A total of {copied_files_count} audio files (and their VTTs if found) were newly copied for TC-5.")
        print(f"Selected TC-5 audios and transcripts are saved in language-specific subfolders under: '{tc5_output_base_path}'")
    elif not use_fixed_selection and total_samples_to_select > 0 :
         print(f"No files met all criteria for TC-5 or none were selected from the eligible pool.")


    if final_report_data_list: 
        log_desc = f"Test Case 5 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)
    return

def testcase6():
    return

def testcase7(base_dataset_path,
              tc7_output_base_path,
              metadata_file_path,
              log_file_path="sampled_testcases/TC-7/tc7_log.json",
              use_fixed_selection=False,
              total_samples_to_select=200): 
    """
    Processes audio files for Test Case 7 (Noisy Audio with Language/Numbers):
    - Selects audio chunks from specified noisy folders (25, 50, 75, 100).
    - Categorizes by language (English-US/UK/HK, Cantonese-HK, Mandarin) 
      and presence of numbers in VTT, similar to TC1.
    - Output structure: TC-7/[LangCategoryWithNumbers]/[NoiseLevelFolder]/[filename.mp3]
    - Aims to select 'total_samples_to_select' evenly distributed across all final categories.
    """
    
    NOISE_LEVELS_TO_PROCESS_TC7 = ["noisy_25", "noisy_50", "noisy_75", "noisy_100"]
    BASE_LANGUAGE_CATEGORIES_TC7 = ["English-US", "English-UK", "English-HK", "Cantonese-HK", "Mandarin"]

    mode_str = "FIXED selection from log" if use_fixed_selection else \
               f"NEW selection (Noisy Levels {NOISE_LEVELS_TO_PROCESS_TC7}, Lang/Numbers, Target: {total_samples_to_select})"
    print(f"\n--- Starting Test Case 7: {mode_str} ---")
    print(f"Source Dataset: '{base_dataset_path}'")
    print(f"Output Base: '{tc7_output_base_path}'")
    print(f"Metadata File: '{metadata_file_path}'")
    if use_fixed_selection:
        if not os.path.exists(log_file_path):
            use_fixed_selection = False
    if use_fixed_selection:
        print(f"Using Fixed Selection Log: '{log_file_path}'")
    else:
        print(f"Log will be saved to: '{log_file_path}'")

    video_metadata_map = load_metadata(metadata_file_path)
    if video_metadata_map is None:
        print("Halting TC-7 due to critical errors in loading video metadata.")
        return

    final_report_data_list = []
    processed_current_run_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    audio_samples_to_process = []
    
    all_currently_discovered_audio = scan_all_audio_files(base_dataset_path, video_metadata_map)
    if not all_currently_discovered_audio and not use_fixed_selection:
        print(f"No audio files were found in '{base_dataset_path}' during initial scan. Halting TC-7.")
        return
    
    discovered_audio_map_by_path = {audio['path']: audio for audio in all_currently_discovered_audio}

    
    
    active_target_processing_categories_tc7 = []
    for base_lang_cat in BASE_LANGUAGE_CATEGORIES_TC7:
        for noise_level_folder in NOISE_LEVELS_TO_PROCESS_TC7:
            active_target_processing_categories_tc7.append(f"{base_lang_cat}/{noise_level_folder}")
            active_target_processing_categories_tc7.append(f"{base_lang_cat}-Numbers/{noise_level_folder}")
    
    if use_fixed_selection:
        print(f"\n--- Loading Fixed Sample List for TC-7 from '{log_file_path}' ---")
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                data_from_json = json.load(f)
            specs_map_from_json = data_from_json.get("samples_by_destination_path")
            if not isinstance(specs_map_from_json, dict): #...
                return
            print(f"Successfully loaded {len(specs_map_from_json)} sample specifications from TC-7 JSON log.")
            for dest_path_key, spec_from_log in specs_map_from_json.items():
                if not isinstance(spec_from_log, dict): #...
                    final_report_data_list.append({'original_path': 'N/A - Invalid spec in log', 'destination_audio_path': dest_path_key, 'status': 'Skipped - Invalid Log Entry', 'error_message': f'Spec for {dest_path_key} was not a dictionary.', 'processed_timestamp': processed_current_run_timestamp, 'tc7_processing_category': spec_from_log.get('tc7_processing_category', 'UnknownLogCategory') })
                    continue
                original_path_from_log = spec_from_log.get('original_path')
                
                tc7_processing_cat_from_log = spec_from_log.get('tc7_processing_category') 
                if not original_path_from_log or not tc7_processing_cat_from_log: #...
                    msg = "missing 'original_path'" if not original_path_from_log else "missing 'tc7_processing_category'"
                    final_report_data_list.append({**spec_from_log, 'original_path': original_path_from_log or 'N/A - Missing in log', 'status': f'Skipped - {msg.capitalize()} in Log', 'error_message': f'{msg.capitalize()} for this sample was not found in the JSON log entry.','processed_timestamp': processed_current_run_timestamp})
                    continue
                if tc7_processing_cat_from_log not in active_target_processing_categories_tc7:
                    print(f"Warning: Logged tc7_processing_category '{tc7_processing_cat_from_log}' for '{original_path_from_log}' is not a valid TC-7 target category. Skipping.")
                    final_report_data_list.append({**spec_from_log, 'status': 'Skipped - Logged Category Not Targeted for TC7', 'error_message': f"Logged category '{tc7_processing_cat_from_log}' is not in active TC7 targets.", 'processed_timestamp': processed_current_run_timestamp})
                    continue
                found_detail = discovered_audio_map_by_path.get(original_path_from_log)
                if found_detail:
                    
                    
                    
                    audio_samples_to_process.append({**found_detail, '_processing_category_path': tc7_processing_cat_from_log})
                else: #...
                    final_report_data_list.append({**spec_from_log, 'status': 'Skipped - Original Path Not Found in Source (current scan)', 'error_message': f"Original audio '{original_path_from_log}' specified in fixed list not present in scanned dataset.", 'processed_timestamp': processed_current_run_timestamp})
        except FileNotFoundError: #...
            return
        except json.JSONDecodeError: #...
            return
        except Exception as e: #...
            return
    else: 
        print(f"\n--- Identifying and Selecting Samples for TC-7 (Target Noisy Levels, Language/Numbers) ---")
        categorized_audios_tc7 = defaultdict(list)
        
        
        noisy_files_for_tc7 = [f for f in all_currently_discovered_audio if f['noisy_folder'] in NOISE_LEVELS_TO_PROCESS_TC7]
        if not noisy_files_for_tc7:
            print(f"No audio files found in the target noisy folders: {NOISE_LEVELS_TO_PROCESS_TC7}. Halting TC-7 selection.")
            return
        print(f"Discovered {len(noisy_files_for_tc7)} audio files from target noisy folders for TC-7 categorization.")

        for audio_detail in noisy_files_for_tc7:
            lang_meta = audio_detail['language']
            acc_meta = audio_detail['accent']
            current_noisy_folder = audio_detail['noisy_folder'] 
            
            base_lang_folder_tc7 = get_tc1_style_language_category(lang_meta, acc_meta)
            
            if base_lang_folder_tc7: 
                lang_and_numbers_cat_tc7 = base_lang_folder_tc7
                vtt_file_path = os.path.splitext(audio_detail['path'])[0] + ".vtt"
                if vtt_has_numbers(vtt_file_path, language_hint=lang_meta):
                    lang_and_numbers_cat_tc7 = f"{base_lang_folder_tc7}-Numbers"
                
                
                final_processing_cat_for_file = f"{lang_and_numbers_cat_tc7}/{current_noisy_folder}"
                
                if final_processing_cat_for_file in active_target_processing_categories_tc7:
                    categorized_audios_tc7[final_processing_cat_for_file].append(audio_detail)

        print("\n--- Audio Distribution by Final Processing Category for TC-7 ---")
        actual_final_categories_with_files_tc7 = []
        for final_cat_path in active_target_processing_categories_tc7:
            count = len(categorized_audios_tc7[final_cat_path])
            if count > 0:
                print(f"Category: {final_cat_path}, Found files: {count}")
                actual_final_categories_with_files_tc7.append(final_cat_path)
        
        if not actual_final_categories_with_files_tc7:
            print("No audio files found matching any active TC-7 criteria after categorization. Halting selection.")
            return

        samples_per_final_category = total_samples_to_select // len(actual_final_categories_with_files_tc7) if actual_final_categories_with_files_tc7 else 0
        if samples_per_final_category == 0 and total_samples_to_select > 0 and actual_final_categories_with_files_tc7: #...
            samples_per_final_category = 1
        
        print(f"\n--- Selecting Samples for TC-7 (Target per final category: ~{samples_per_final_category}) ---")
        total_actually_selected = 0
        
        for final_cat_path_tc7 in actual_final_categories_with_files_tc7:
            if total_actually_selected >= total_samples_to_select: break
            available_files = categorized_audios_tc7[final_cat_path_tc7]
            num_to_select_this_pass = min(samples_per_final_category, len(available_files), total_samples_to_select - total_actually_selected)
            if num_to_select_this_pass > 0:
                selected_for_category = random.sample(available_files, num_to_select_this_pass)
                for item in selected_for_category:
                    audio_samples_to_process.append({**item, '_processing_category_path': final_cat_path_tc7})
                    if item in available_files: available_files.remove(item)
                total_actually_selected += len(selected_for_category)
        
        
        if total_actually_selected < total_samples_to_select: #...
            remaining_quota = total_samples_to_select - total_actually_selected
            all_remaining_eligible_samples_tc7 = []
            shuffled_active_final_cats_tc7 = list(actual_final_categories_with_files_tc7)
            random.shuffle(shuffled_active_final_cats_tc7)
            for final_cat_path_tc7 in shuffled_active_final_cats_tc7:
                for item in categorized_audios_tc7[final_cat_path_tc7]:
                     all_remaining_eligible_samples_tc7.append({**item, '_processing_category_path': final_cat_path_tc7})
            if all_remaining_eligible_samples_tc7:
                num_to_select_fill_up = min(remaining_quota, len(all_remaining_eligible_samples_tc7))
                if num_to_select_fill_up > 0:
                    random.shuffle(all_remaining_eligible_samples_tc7)
                    fill_up_selected = all_remaining_eligible_samples_tc7[:num_to_select_fill_up]
                    audio_samples_to_process.extend(fill_up_selected)
                    total_actually_selected += len(fill_up_selected)

        print(f"Total samples selected for TC-7: {total_actually_selected}")
        if total_actually_selected == 0 and total_samples_to_select > 0: #...
            return
        elif total_actually_selected == 0 and total_samples_to_select == 0: #...
            return

    
    copied_files_count = 0
    if not audio_samples_to_process:
        print("No samples in processing list for TC-7. File operations skipped.")
    else:
        print(f"\n--- Commencing File Operations for {len(audio_samples_to_process)} selected TC-7 samples ---")
    
    processed_copy_keys_tc7 = set()
    for audio_info_with_context in audio_samples_to_process:
        original_audio_full_path = audio_info_with_context['path']
        
        tc7_full_processing_path = audio_info_with_context['_processing_category_path'] 
        
        
        
        target_file_directory = os.path.join(tc7_output_base_path, tc7_full_processing_path)
        
        video_id = audio_info_with_context['video_id']
        noisy_folder_ctx = audio_info_with_context['noisy_folder'] 
        original_audio_source_filename = audio_info_with_context['original_filename']
        dest_audio_filename = f"{video_id}_{noisy_folder_ctx}_{original_audio_source_filename}"
        target_audio_path = os.path.join(target_file_directory, dest_audio_filename)

        copy_key = (original_audio_full_path, target_audio_path)
        if copy_key in processed_copy_keys_tc7: continue
        processed_copy_keys_tc7.add(copy_key)

        report_item = {
            'original_path': original_audio_full_path,
            'video_id': video_id,
            'tc7_processing_category': tc7_full_processing_path, 
            'language_metadata': audio_info_with_context['language'],
            'accent_metadata': audio_info_with_context['accent'],
            'noisy_folder_source': noisy_folder_ctx, 
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
        except OSError as e: #...
            report_item['status'] = 'Skipped - Directory Creation Error'; report_item['error_message'] = f"Failed to create target directory: {e}"; final_report_data_list.append(report_item); continue
        try:
            if not os.path.exists(original_audio_full_path): raise FileNotFoundError(f"Source audio file not found: {original_audio_full_path}")
            shutil.copy2(original_audio_full_path, target_audio_path); copied_files_count +=1; report_item['status'] = 'Audio Copied'
            original_audio_dir = os.path.dirname(original_audio_full_path); expected_source_vtt_filename = os.path.splitext(original_audio_source_filename)[0] + ".vtt"; original_transcript_full_path = os.path.join(original_audio_dir, expected_source_vtt_filename)
            if os.path.isfile(original_transcript_full_path):
                target_transcript_path = os.path.splitext(target_audio_path)[0] + ".vtt"; report_item['destination_transcript_path'] = target_transcript_path
                try: shutil.copy2(original_transcript_full_path, target_transcript_path); report_item['status'] = 'Audio and VTT Copied'
                except Exception as e_vtt: report_item['status'] = 'Audio Copied, VTT Error'; report_item['error_message'] = f"VTT copy error: {str(e_vtt)}"
            else: report_item['status'] = 'Audio Copied, VTT Not Found'
        except Exception as e_audio: report_item['status'] = 'Error Copying Audio'; report_item['error_message'] = f"Audio copy error: {str(e_audio)}"
        final_report_data_list.append(report_item)

    print("\n--- TC-7 Operation Complete ---")
    if copied_files_count > 0 or (use_fixed_selection and len(audio_samples_to_process) > 0) : 
        print(f"A total of {copied_files_count} audio files (and their VTTs if found) were newly copied for TC-7.")
    elif not use_fixed_selection and total_samples_to_select > 0 :
         print(f"No files met all criteria for TC-7 or none were selected from the eligible pool.")
    if final_report_data_list: 
        log_desc = f"Test Case 7 Selection ({mode_str})"
        save_processed_files_log(final_report_data_list, log_file_path, log_desc)
    return

def pipeline():
    base_dataset = "chunked_dataset"
    metadata_file = "urls.meta.json" 
    hsbc_vocabulary_json_path = "vocabulary.hsbc.json" 
    profanity_vocabulary_json_path = "vocabulary.profanity.json"
    output_root = "testset"

    
    os.makedirs(output_root, exist_ok=True)

    
    tc1_output_path = os.path.join(output_root, "TC-1")
    tc1_log = os.path.join(tc1_output_path, "tc1_selection_log.json") 
    print(f"Pipeline starting TC-1. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    testcase1(
        base_dataset_path=base_dataset,
        tc1_output_base_path=tc1_output_path,
        metadata_file_path=metadata_file,
        total_samples_to_select=100, 
        log_file_path=tc1_log,
        use_fixed_selection=True 
    )

    
    tc2_output_path = os.path.join(output_root, "TC-2")
    tc2_log = os.path.join(tc2_output_path, "tc2_selection_log.json")
    print(f"Pipeline starting TC-2. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    testcase2(
        base_dataset_path=base_dataset,
        tc2_output_base_path=tc2_output_path,
        metadata_file_path=metadata_file,
        log_file_path=tc2_log,
        use_fixed_selection=True, 
        total_samples_for_tc2=100 
    )

    
    tc3_output_path = os.path.join(output_root, "TC-3")
    tc3_log = os.path.join(tc3_output_path, "tc3_selection_log.json")
    print(f"Pipeline starting TC-3. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    testcase3(
        base_dataset_path=base_dataset,
        tc3_output_base_path=tc3_output_path,
        metadata_file_path=metadata_file,
        vocabulary_file_path=hsbc_vocabulary_json_path, 
        log_file_path=tc3_log,
        use_fixed_selection=True, 
        total_samples_to_select=100 
    )
    

    tc5_output_path = os.path.join(output_root, "TC-5")
    tc5_log = os.path.join(tc5_output_path, "tc5_selection_log.json")
    print(f"Pipeline starting TC-5. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    testcase5(
        base_dataset_path=base_dataset,
        tc5_output_base_path=tc5_output_path,
        metadata_file_path=metadata_file,
        vocabulary_file_path=profanity_vocabulary_json_path, 
        log_file_path=tc5_log,
        use_fixed_selection=True, 
        total_samples_to_select=100 
    )
    print(f"\nPipeline finished. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


    tc7_output_path = os.path.join(output_root, "TC-7")
    tc7_log = os.path.join(tc7_output_path, "tc7_selection_log.json")
    print(f"Pipeline starting TC-7. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    testcase7(
        base_dataset_path=base_dataset,
        tc7_output_base_path=tc7_output_path,
        metadata_file_path=metadata_file,
        log_file_path=tc7_log,
        use_fixed_selection=True, 
        total_samples_to_select=200
    )

    print(f"\nPipeline finished. Current date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return

if __name__ == "__main__":
    pipeline()
