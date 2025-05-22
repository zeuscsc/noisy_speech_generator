import os
import re
import pandas as pd
from tqdm import tqdm
from speechbrain.utils.metric_stats import ErrorRateStats
import cn2an
from numerizer import numerize 
from collections import Counter
import logging
import json 


ENG_DIGIT_KMB_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*([KMB])\b", re.IGNORECASE)
DIGIT_REGEX = re.compile(r'\d+(?:\.\d+)?')

CH_NUM_CHARS_ONLY = "零一二三四五六七八九十拾百佰千仟萬万億亿兆兩俩幺壹貳參肆伍陸柒捌玖貮點点"
CHINESE_NUMBER_CANDIDATE_REGEX = re.compile(rf"[{CH_NUM_CHARS_ONLY}\d.]+")


PUNCT_WESTERN_STR = r"!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~" 
PUNCT_CJK_STR = r"＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
ALL_PUNCTUATION_CHARS = set(PUNCT_WESTERN_STR + PUNCT_CJK_STR)


def parse_vtt(file_path):
    """
    Parses a VTT file and extracts the concatenated transcript text.
    Normalizes whitespace to single spaces.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logging.warning(f"Could not read VTT file {file_path}: {e}")
        return ""

    content_lines = []
    captions_started = False
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped == "WEBVTT":
            captions_started = True
            continue
        if not captions_started:
            continue
        if line_stripped.startswith("NOTE"):
            continue
        if "-->" in line_stripped:  
            continue
        content_lines.append(line_stripped)
    
    full_text = " ".join(content_lines)
    return re.sub(r'\s+', ' ', full_text).strip()

def get_vtt_segments(file_path):
    """
    Parses a VTT file and returns a list of individual caption/segment texts.
    Used for Test Case 4 (Segmentation Accuracy).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logging.warning(f"Could not read VTT file {file_path} for segments: {e}")
        return []

    segment_texts = []
    captions_started = False
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped == "WEBVTT":
            captions_started = True
            continue
        if not captions_started:
            continue
        if line_stripped.startswith("NOTE"):
            continue
        if "-->" in line_stripped:  
            continue
        
        segment_texts.append(line_stripped)
    return segment_texts

def parse_txt(file_path):
    """
    Reads a text file and returns its content.
    Normalizes whitespace to single spaces.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return re.sub(r'\s+', ' ', content).strip()
    except Exception as e:
        logging.warning(f"Could not read TXT file {file_path}: {e}")
        return ""


def get_tokens_for_wer(text, language_code):
    """
    Prepares text for WER calculation.
    - Chinese (zh): Removes CJK/Western punctuation, no spaces, tokenizes by character.
    - English (en): Lowercases, removes punctuation (keeps apostrophes within words), splits by space.
    """
    
    if language_code.startswith("zh"):
        translator = str.maketrans('', '', PUNCT_WESTERN_STR + PUNCT_CJK_STR)
        text_no_punct = text.translate(translator)
        text_no_space = re.sub(r'\s+', '', text_no_punct)
        return list(text_no_space)
    elif language_code.startswith("en"):
        text = text.lower()
        
        
        punct_to_remove_en = PUNCT_WESTERN_STR.replace("'", "") + PUNCT_CJK_STR 
        translator = str.maketrans('', '', punct_to_remove_en)
        text_no_punct = text.translate(translator)
        text_normalized_space = re.sub(r'\s+', ' ', text_no_punct).strip()
        return text_normalized_space.split()
    else: 
        text = text.lower() 
        punct_to_remove_other = PUNCT_WESTERN_STR.replace("'", "") + PUNCT_CJK_STR
        translator = str.maketrans('', '', punct_to_remove_other)
        text_no_punct = text.translate(translator)
        text_normalized_space = re.sub(r'\s+', ' ', text_no_punct).strip()
        return text_normalized_space.split()


def extract_and_normalize_numbers(text, language_code):
    """
    Extracts and normalizes numbers from text.
    Returns a list of number strings (e.g., "1000", "2.5", "5000").
    """
    normalized_numbers = []
    if not text:
        return []

    text = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    if language_code.startswith("en"):
        def replace_kmb(match_obj):
            val_str, unit = match_obj.groups()
            val = float(val_str)
            multiplier = 1
            if unit.upper() == 'K': multiplier = 1000
            elif unit.upper() == 'M': multiplier = 1000000
            elif unit.upper() == 'B': multiplier = 1000000000
            result_val = val * multiplier
            return str(int(result_val)) if result_val == int(result_val) else str(result_val)
        text_after_kmb = ENG_DIGIT_KMB_REGEX.sub(replace_kmb, text)
        try:
            text_after_numerizer = numerize(text_after_kmb)
        except Exception as e:
            logging.info(f"Numerizer failed for text segment (falling back): '{text_after_kmb}'. Error: {e}")
            text_after_numerizer = text_after_kmb
        for match in DIGIT_REGEX.finditer(text_after_numerizer):
            num_str = match.group(0)
            try: 
                num_val = float(num_str)
                normalized_numbers.append(str(int(num_val)) if num_val == int(num_val) else str(num_val))
            except ValueError:
                logging.info(f"Could not convert '{num_str}' to float after processing: {text_after_numerizer}")
    elif language_code.startswith("zh"):
        potential_num_strings = CHINESE_NUMBER_CANDIDATE_REGEX.findall(text)
        for s in potential_num_strings:
            try:
                val = cn2an.cn2an(s, "smart") 
                if isinstance(val, float) and val == int(val):
                    normalized_numbers.append(str(int(val)))
                elif isinstance(val, (float, int)):
                    normalized_numbers.append(str(val))
            except ValueError:
                
                
                
                
                pass 
    return normalized_numbers

def calculate_number_accuracy(gt_numbers, pred_numbers):
    """
    Calculates accuracy of predicted numbers against ground truth numbers.
    """
    if not gt_numbers:
        return 1.0 if not pred_numbers else 0.0 
    
    gt_counts = Counter(gt_numbers)
    pred_counts = Counter(pred_numbers)
    
    correct_matches = 0
    for num_val, count_in_gt in gt_counts.items():
        correct_matches += min(count_in_gt, pred_counts.get(num_val, 0))
        
    accuracy = correct_matches / len(gt_numbers) if len(gt_numbers) > 0 else (1.0 if not pred_numbers else 0.0)
    return accuracy


def calculate_vocabulary_accuracy(gt_text, pred_text, vocabulary_list, vtt_stem, stt_method):
    """
    Calculates accuracy of predicted vocabulary items against ground truth.
    """
    if not vocabulary_list:
        logging.warning(f"Vocabulary list is empty for {vtt_stem} (STT: {stt_method}). Vocab accuracy will be N/A.")
        return "N/A", [], []

    vocabs_in_gt = []
    vocabs_in_gt_and_pred = []

    logging.info(f"--- Vocabulary Check for {vtt_stem} (STT: {stt_method}) ---")
    logging.info(f"      Ground Truth Text (snippet): '{gt_text[:100]}...'")
    logging.info(f"      Prediction Text (snippet): '{pred_text[:100]}...'")
    logging.info(f"      Vocabulary List contains {len(vocabulary_list)} items.")

    for vocab_item in vocabulary_list:
        vocab_item_str = str(vocab_item) 
        
        gt_has_vocab = vocab_item_str.lower() in gt_text.lower()
        
        if gt_has_vocab:
            vocabs_in_gt.append(vocab_item_str)
            pred_has_vocab = vocab_item_str.lower() in pred_text.lower()
            if pred_has_vocab:
                vocabs_in_gt_and_pred.append(vocab_item_str)
                logging.info(f"      Vocab: '{vocab_item_str}' | Found in GT: YES | Found in Pred: YES")
            else:
                logging.info(f"      Vocab: '{vocab_item_str}' | Found in GT: YES | Found in Pred: NO")
        
        
        
        

    if not vocabs_in_gt:
        logging.info(f"      No vocabulary from the provided list found in Ground Truth for {vtt_stem} ({stt_method}). Vocabulary accuracy is N/A.")
        logging.info(f"--- End Vocabulary Check for {vtt_stem} ({stt_method}) ---")
        return "N/A", [], []

    accuracy = len(vocabs_in_gt_and_pred) / len(vocabs_in_gt)
    logging.info(f"      Summary for {vtt_stem} ({stt_method}): Vocab items from list in GT: {len(vocabs_in_gt)}. Matched in Pred: {len(vocabs_in_gt_and_pred)}. Accuracy: {accuracy:.4f}")
    logging.info(f"--- End Vocabulary Check for {vtt_stem} ({stt_method}) ---")
    return accuracy, vocabs_in_gt, vocabs_in_gt_and_pred


def calculate_segmentation_accuracy(gt_segments, pred_text):
    """
    Calculates segmentation accuracy based on VTT segments and predicted text.
    A segment boundary is considered correctly predicted if a space or punctuation
    exists in the prediction text after the corresponding GT segment's content.
    This is a simplified heuristic.
    """
    if not gt_segments:
        logging.warning("GT segments list is empty. Cannot calculate segmentation accuracy.")
        return 0.0 if pred_text else 1.0 

    num_gt_boundaries = len(gt_segments) - 1

    if num_gt_boundaries <= 0:
        logging.info(f"Only {len(gt_segments)} GT segment(s). No boundaries to check for segmentation. Accuracy is N/A.")
        return "N/A"

    correctly_separated_boundaries = 0
    current_pred_char_idx = 0 

    
    for i in range(num_gt_boundaries):
        gt_segment_to_map = gt_segments[i]
        
        
        
        gt_content_chars_count = 0
        for char_gt in gt_segment_to_map:
            if not char_gt.isspace() and char_gt not in ALL_PUNCTUATION_CHARS:
                gt_content_chars_count += 1
        
        
        
        if gt_content_chars_count == 0:
            logging.debug(f"GT segment '{gt_segment_to_map}' (index {i}) has 0 content characters. Skipping this boundary check for pred mapping.")
            
            
            
            continue


        
        pred_content_chars_found = 0
        
        mapped_gt_segment_end_idx_in_pred = -1 
        
        temp_scan_idx = current_pred_char_idx
        while temp_scan_idx < len(pred_text) and pred_content_chars_found < gt_content_chars_count:
            char_pred = pred_text[temp_scan_idx]
            
            if not char_pred.isspace() and char_pred not in ALL_PUNCTUATION_CHARS:
                pred_content_chars_found += 1
            
            
            if pred_content_chars_found == gt_content_chars_count: 
                mapped_gt_segment_end_idx_in_pred = temp_scan_idx
                break
            temp_scan_idx += 1
        
        
        if pred_content_chars_found < gt_content_chars_count or mapped_gt_segment_end_idx_in_pred == -1:
            logging.debug(f"Prediction text ended or insufficient content found while trying to map GT segment '{gt_segment_to_map}'.")
            current_pred_char_idx = len(pred_text) 
            continue 

        
        separator_check_idx = mapped_gt_segment_end_idx_in_pred + 1

        if separator_check_idx < len(pred_text):
            potential_separator_char = pred_text[separator_check_idx]
            
            if potential_separator_char.isspace() or potential_separator_char in ALL_PUNCTUATION_CHARS:
                correctly_separated_boundaries += 1
                logging.debug(f"Boundary after GT '{gt_segment_to_map}' correctly separated in pred by '{potential_separator_char}'.")
                current_pred_char_idx = separator_check_idx + 1 
            else:
                logging.debug(f"Boundary after GT '{gt_segment_to_map}' NOT separated. Found '{potential_separator_char}' in pred.")
                current_pred_char_idx = separator_check_idx 
        else:
            
            
            logging.debug(f"Prediction ended exactly after mapping GT segment '{gt_segment_to_map}'. No separator found.")
            current_pred_char_idx = len(pred_text)

    if num_gt_boundaries == 0 : 
        return "N/A"
    accuracy = correctly_separated_boundaries / num_gt_boundaries
    return accuracy


def _process_test_case_generic(base_test_set_dir, tc_folder_name, 
                                    calculate_numbers_flag,
                                    calculate_vocabulary_flag,
                                    vocabulary_list_path=None):
    """
    Generic function to process a test case folder (TC-1, TC-2, TC-3, TC-7).
    Calculates metrics based on flags.
    """
    results_data = []
    tc_path = os.path.join(base_test_set_dir, tc_folder_name)

    if not os.path.isdir(tc_path):
        logging.error(f"Test case folder not found: {tc_path}")
        return pd.DataFrame()

    loaded_vocabulary = []
    if calculate_vocabulary_flag and vocabulary_list_path:
        try:
            with open(vocabulary_list_path, 'r', encoding='utf-8') as f_vocab:
                loaded_vocabulary = json.load(f_vocab)
            if not isinstance(loaded_vocabulary, list) or not all(isinstance(item, str) for item in loaded_vocabulary):
                logging.error(f"Vocabulary file {vocabulary_list_path} is not a list of strings. Disabling vocabulary processing for {tc_folder_name}.")
                loaded_vocabulary = []
            else:
                logging.info(f"Successfully loaded {len(loaded_vocabulary)} vocabulary items from {vocabulary_list_path} for {tc_folder_name}.")
        except Exception as e:
            logging.error(f"Could not load or parse vocabulary file {vocabulary_list_path}: {e}. Disabling vocabulary processing for {tc_folder_name}.")
            loaded_vocabulary = []

    files_to_process_meta = []
    
    for lang_folder_name in os.listdir(tc_path):
        lang_full_path = os.path.join(tc_path, lang_folder_name)
        if not os.path.isdir(lang_full_path):
            logging.info(f"Skipping non-directory item: {lang_full_path} in {tc_folder_name}")
            continue

        paths_to_scan_for_files = []
        if tc_folder_name == "TC-7": 
            logging.info(f"Scanning language folder for TC-7: {lang_full_path}")
            for noise_folder_name in os.listdir(lang_full_path): 
                noise_full_path = os.path.join(lang_full_path, noise_folder_name)
                if os.path.isdir(noise_full_path):
                    match = re.search(r"noisy_(\d+)", noise_folder_name, re.IGNORECASE)
                    current_noise_level = f"{match.group(1)}%" if match else "Unknown"
                    paths_to_scan_for_files.append({
                        "path": noise_full_path, 
                        "noise": current_noise_level, 
                        "base_lang_folder": lang_folder_name, 
                        "display_lang_sub_folder": os.path.join(lang_folder_name, noise_folder_name) 
                    })
        else: 
            logging.info(f"Scanning language folder: {lang_full_path} for {tc_folder_name}")
            paths_to_scan_for_files.append({
                "path": lang_full_path, 
                "noise": "N/A", 
                "base_lang_folder": lang_folder_name,
                "display_lang_sub_folder": lang_folder_name 
            })
        
        
        for scan_target in paths_to_scan_for_files:
            current_scan_path = scan_target["path"]
            for item_name in os.listdir(current_scan_path):
                if item_name.endswith(".vtt"): 
                    vtt_path = os.path.join(current_scan_path, item_name)
                    vtt_stem, _ = os.path.splitext(item_name) 
                    
                    for pred_item_name in os.listdir(current_scan_path):
                        
                        if pred_item_name.startswith(vtt_stem + ".") and pred_item_name.endswith(".txt"):
                            files_to_process_meta.append({
                                "vtt_path": vtt_path,
                                "pred_filename": pred_item_name,
                                "base_lang_folder": scan_target["base_lang_folder"],
                                "display_lang_sub_folder": scan_target["display_lang_sub_folder"],
                                "current_scan_path": current_scan_path,
                                "vtt_stem": vtt_stem,
                                "noise_level": scan_target["noise"]
                            })
    
    for file_meta in tqdm(files_to_process_meta, desc=f"Processing {tc_folder_name}"):
        vtt_path = file_meta["vtt_path"]
        pred_item_name = file_meta["pred_filename"]
        base_lang_folder = file_meta["base_lang_folder"] 
        display_lang_sub_folder = file_meta["display_lang_sub_folder"] 
        current_scan_path = file_meta["current_scan_path"]
        vtt_stem = file_meta["vtt_stem"]
        noise_level_percent = file_meta["noise_level"]

        
        lang_parts = base_lang_folder.split('-') 
        lang_short_code = lang_parts[0].lower() 
        language_code_for_processing = "en" 
        if lang_short_code in ["cantonese", "mandarin"]: language_code_for_processing = "zh"
        elif lang_short_code == "english": language_code_for_processing = "en"
        else: language_code_for_processing = lang_short_code 

        gt_text = parse_vtt(vtt_path)
        pred_txt_path = os.path.join(current_scan_path, pred_item_name)
        pred_text = parse_txt(pred_txt_path)
        
        
        stt_method = "unknown"
        expected_prefix = vtt_stem + "." 
        if pred_item_name.startswith(expected_prefix) and pred_item_name.endswith(".txt"):
            method_part = pred_item_name[len(expected_prefix):-len(".txt")]
            stt_method = method_part
        
        if not stt_method or stt_method == "unknown":
            logging.warning(f"Could not determine STT method for '{pred_item_name}' (VTT stem: '{vtt_stem}') in {current_scan_path}. Skipping.")
            continue

        wer_raw, wrr_raw, num_acc_raw, voc_acc_raw = None, None, None, None
        gt_numbers_extracted, pred_numbers_extracted = [], []
        gt_vocabs_found, pred_vocabs_matched = [], []
        folder_type_output = "General" 

        
        
        if tc_folder_name == "TC-1" and calculate_numbers_flag and base_lang_folder.endswith("-Numbers"):
            folder_type_output = "Numbers"
            if not gt_text: logging.warning(f"Empty GT for VTT: {vtt_path} in Numbers folder.")
            gt_numbers_extracted = extract_and_normalize_numbers(gt_text, language_code_for_processing)
            pred_numbers_extracted = extract_and_normalize_numbers(pred_text, language_code_for_processing)
            num_acc_raw = calculate_number_accuracy(gt_numbers_extracted, pred_numbers_extracted)
        
        
        elif tc_folder_name == "TC-7":
            folder_type_output = "NoiseTest"
            if not gt_text: logging.warning(f"Empty GT text for VTT: {vtt_path} (TC-7). WER/WRR will be affected.")
            gt_tokens = get_tokens_for_wer(gt_text, language_code_for_processing)
            pred_tokens = get_tokens_for_wer(pred_text, language_code_for_processing)
            if not gt_text and not gt_tokens: logging.info(f"GT text for {vtt_stem} ({vtt_path}) was empty or yielded no tokens.")
            
            if gt_tokens: 
                wer_tracker = ErrorRateStats()
                wer_tracker.append(ids=[vtt_stem + "_" + stt_method], predict=[pred_tokens], target=[gt_tokens])
                stats = wer_tracker.summarize() 
                wer_raw = stats.get('error_rate') 
                if wer_raw is None: wer_raw = stats.get('WER') 

                
                
                
                
                
                
                
                H, N_ref = stats.get('hits'), stats.get('num_ref_tokens')
                
                if H is None and hasattr(wer_tracker, 'hits'): H = wer_tracker.hits
                if N_ref is None and hasattr(wer_tracker, 'ref_tokens'): N_ref = wer_tracker.ref_tokens
                
                if H is not None and N_ref is not None:
                    if N_ref > 0: wrr_raw = H / N_ref
                    elif N_ref == 0: wrr_raw = 1.0 if not pred_tokens else 0.0 
                elif wer_raw is not None: 
                    
                    
                    wrr_raw = 1.0 - (wer_raw / 100.0) if wer_raw <=100 else 0.0 
                
                if wer_raw is not None and wrr_raw is None and N_ref is not None and N_ref > 0 : 
                    logging.warning(f"WRR could not be calculated for {vtt_stem} (TC-7). WER={wer_raw}, H={H}, N_ref={N_ref}.")

            elif not gt_tokens and not pred_tokens: 
                wer_raw, wrr_raw = 0.0, 1.0
            else: 
                wer_raw, wrr_raw = 100.0, 0.0 
        
        
        else: 
            if tc_folder_name == "TC-1": folder_type_output = "Regular"
            elif tc_folder_name == "TC-2": folder_type_output = "Accent"
            elif tc_folder_name == "TC-3": folder_type_output = "Vocabulary"
            
            if not gt_text: logging.warning(f"Empty GT text for VTT: {vtt_path}. WER/WRR will be affected.")
            gt_tokens = get_tokens_for_wer(gt_text, language_code_for_processing)
            pred_tokens = get_tokens_for_wer(pred_text, language_code_for_processing)
            if not gt_text and not gt_tokens: logging.info(f"GT text for {vtt_stem} ({vtt_path}) was empty or yielded no tokens.")

            if gt_tokens:
                wer_tracker = ErrorRateStats()
                wer_tracker.append(ids=[vtt_stem + "_" + stt_method], predict=[pred_tokens], target=[gt_tokens])
                stats = wer_tracker.summarize()
                wer_raw = stats.get('error_rate', stats.get('WER')) 
                H, N_ref = stats.get('hits'), stats.get('num_ref_tokens')
                if H is None and hasattr(wer_tracker, 'hits'): H = wer_tracker.hits
                if N_ref is None and hasattr(wer_tracker, 'ref_tokens'): N_ref = wer_tracker.ref_tokens

                if H is not None and N_ref is not None:
                    if N_ref > 0: wrr_raw = H / N_ref
                    elif N_ref == 0: wrr_raw = 1.0 if not pred_tokens else 0.0
                elif wer_raw is not None:
                    wrr_raw = 1.0 - (wer_raw / 100.0) if wer_raw <=100 else 0.0
                if wer_raw is not None and wrr_raw is None and N_ref is not None and N_ref > 0:
                    logging.warning(f"WRR could not be calculated for {vtt_stem}. WER={wer_raw}, H={H}, N_ref={N_ref}.")
            elif not gt_tokens and not pred_tokens: wer_raw, wrr_raw = 0.0, 1.0
            else: wer_raw, wrr_raw = 100.0, 0.0
            
            
            if tc_folder_name == "TC-3" and calculate_vocabulary_flag and loaded_vocabulary:
                voc_acc_raw, gt_vocabs_found, pred_vocabs_matched = calculate_vocabulary_accuracy(
                    gt_text, pred_text, loaded_vocabulary, vtt_stem, stt_method
                )

        
        wer_out = f"{wer_raw:.2f}" if isinstance(wer_raw, (float, int)) else "N/A"
        wrr_out = f"{wrr_raw*100:.2f}" if isinstance(wrr_raw, (float, int)) else "N/A" 
        num_acc_out = f"{num_acc_raw*100:.2f}" if isinstance(num_acc_raw, (float, int)) else "N/A" 
        voc_acc_out = f"{voc_acc_raw*100:.2f}" if isinstance(voc_acc_raw, float) else voc_acc_raw 


        results_data.append({
            "TestCase": tc_folder_name,
            "LanguageSubFolder": display_lang_sub_folder, 
            "FolderType": folder_type_output, 
            "NoiseLevel_Percent": noise_level_percent if tc_folder_name == "TC-7" else "N/A",
            "GroundTruthFile": os.path.basename(vtt_path),
            "PredictionFile": pred_item_name,
            "STT_Method": stt_method,
            "WER": wer_out, "WRR_Percent": wrr_out, 
            "NumberAccuracy_Percent": num_acc_out, "VocabularyAccuracy_Percent": voc_acc_out,
            "ResponseSpeed_s": "N/A", 
            "GT_Text_Raw": gt_text, "Pred_Text_Raw": pred_text,
            "GT_Numbers_Extracted": ", ".join(gt_numbers_extracted) if gt_numbers_extracted else "",
            "Pred_Numbers_Extracted": ", ".join(pred_numbers_extracted) if pred_numbers_extracted else "",
            "GT_Vocabs_Found": ", ".join(gt_vocabs_found), 
            "Pred_Vocabs_Matched": ", ".join(pred_vocabs_matched) 
        })
    return pd.DataFrame(results_data)


def _process_test_case_4(base_test_set_dir, tc_folders_to_scan_for_vtts, output_dir_for_logs):
    """
    Processes data for Test Case 4 (Segmentation Accuracy).
    It iterates through specified test case folders (TC-1, TC-2, TC-3, TC-7) to find VTTs and their predictions.
    """
    results_data = []
    logging.info(f"TC4: Scanning for VTTs in {tc_folders_to_scan_for_vtts} under {base_test_set_dir}")

    for source_tc_folder in tc_folders_to_scan_for_vtts: 
        tc_path = os.path.join(base_test_set_dir, source_tc_folder)
        if not os.path.isdir(tc_path):
            logging.warning(f"TC4: Source folder for segments not found: {tc_path}. Skipping.")
            continue

        files_to_process_meta = []
        
        for lang_folder_name in os.listdir(tc_path):
            lang_full_path = os.path.join(tc_path, lang_folder_name)
            if not os.path.isdir(lang_full_path): continue

            paths_to_scan_for_files = []
            if source_tc_folder == "TC-7": 
                for noise_folder_name in os.listdir(lang_full_path):
                    noise_full_path = os.path.join(lang_full_path, noise_folder_name)
                    if os.path.isdir(noise_full_path):
                        paths_to_scan_for_files.append({
                            "path": noise_full_path,
                            "base_lang_folder": lang_folder_name,
                            "display_lang_sub_folder": os.path.join(lang_folder_name, noise_folder_name)
                        })
            else:
                paths_to_scan_for_files.append({
                    "path": lang_full_path,
                    "base_lang_folder": lang_folder_name,
                    "display_lang_sub_folder": lang_folder_name
                })
            
            for scan_target in paths_to_scan_for_files:
                current_scan_path = scan_target["path"]
                for item_name in os.listdir(current_scan_path):
                    if item_name.endswith(".vtt"):
                        vtt_path = os.path.join(current_scan_path, item_name)
                        vtt_stem, _ = os.path.splitext(item_name)
                        for pred_item_name in os.listdir(current_scan_path):
                            if pred_item_name.startswith(vtt_stem + ".") and pred_item_name.endswith(".txt"):
                                files_to_process_meta.append({
                                    "vtt_path": vtt_path,
                                    "pred_filename": pred_item_name,
                                    "base_lang_folder": scan_target["base_lang_folder"],
                                    "display_lang_sub_folder": scan_target["display_lang_sub_folder"],
                                    "current_scan_path": current_scan_path,
                                    "vtt_stem": vtt_stem,
                                    "source_tc_folder_vtt": source_tc_folder 
                                })
        
        for file_meta in tqdm(files_to_process_meta, desc=f"TC4 processing VTTs from {source_tc_folder}"):
            vtt_path = file_meta["vtt_path"]
            pred_item_name = file_meta["pred_filename"]
            
            display_lang_sub_folder = file_meta["display_lang_sub_folder"]
            current_scan_path = file_meta["current_scan_path"]
            vtt_stem = file_meta["vtt_stem"]
            source_tc_vtt = file_meta["source_tc_folder_vtt"] 

            gt_segments = get_vtt_segments(vtt_path) 
            pred_txt_path = os.path.join(current_scan_path, pred_item_name)
            pred_text = parse_txt(pred_txt_path) 

            stt_method = "unknown"
            expected_prefix = vtt_stem + "."
            if pred_item_name.startswith(expected_prefix) and pred_item_name.endswith(".txt"):
                method_part = pred_item_name[len(expected_prefix):-len(".txt")]
                stt_method = method_part
            
            if not stt_method or stt_method == "unknown":
                logging.warning(f"TC4: Could not determine STT method for '{pred_item_name}'. Skipping.")
                continue

            seg_acc_raw = "N/A" 
            if not gt_segments:
                logging.warning(f"TC4: No segments found in GT VTT {vtt_path}. Segmentation accuracy N/A.")
            elif not pred_text:
                logging.warning(f"TC4: Prediction text is empty for {pred_item_name}. Segmentation accuracy will be 0 or N/A if no GT boundaries.")
                if len(gt_segments) <= 1: 
                    seg_acc_raw = "N/A"
                else:
                    seg_acc_raw = 0.0 
            else:
                seg_acc_raw = calculate_segmentation_accuracy(gt_segments, pred_text)

            seg_acc_out = f"{seg_acc_raw*100:.2f}" if isinstance(seg_acc_raw, float) else seg_acc_raw 

            results_data.append({
                "TestCase": "TC-4", 
                "SourceTestCaseVTT": source_tc_vtt, 
                "LanguageSubFolder": display_lang_sub_folder, 
                "GroundTruthFile": os.path.basename(vtt_path),
                "PredictionFile": pred_item_name,
                "STT_Method": stt_method,
                "SegmentationAccuracy_Percent": seg_acc_out,
                
                "WER": "N/A", "WRR_Percent": "N/A", "NumberAccuracy_Percent": "N/A", "VocabularyAccuracy_Percent": "N/A",
                "ResponseSpeed_s": "N/A", 
                "GT_Segments_Count": len(gt_segments) if gt_segments else 0,
                "Pred_Text_Raw_Snippet": pred_text[:100] + "..." if pred_text and len(pred_text)>100 else pred_text
                
            })
            
    return pd.DataFrame(results_data)


def testcase1(base_test_set_dir="testset"):
    return _process_test_case_generic(base_test_set_dir, "TC-1", 
                                        calculate_numbers_flag=True, 
                                        calculate_vocabulary_flag=False)

def testcase2(base_test_set_dir="testset"):
    return _process_test_case_generic(base_test_set_dir, "TC-2", 
                                        calculate_numbers_flag=False,
                                        calculate_vocabulary_flag=False)

def testcase3(base_test_set_dir="testset", vocabulary_json_path="vocabulary.hsbc.json"):
    logging.info(f"Starting Test Case 3 processing. Data from 'TC-3' folder. Vocabulary from: {vocabulary_json_path}")
    return _process_test_case_generic(base_test_set_dir, "TC-3",
                                        calculate_numbers_flag=False,
                                        calculate_vocabulary_flag=True, 
                                        vocabulary_list_path=vocabulary_json_path)

def testcase4(base_test_set_dir="testset", output_dir_for_logs="test_case_logs"):
    """
    Processes Test Case 4 for segmentation accuracy.
    Uses VTTs from other test case folders (TC-1, TC-2, TC-3, TC-7).
    """
    logging.info(f"Starting Test Case 4 (Segmentation Accuracy) processing.")
    
    tc_folders_to_scan_for_vtts = ["TC-1", "TC-2", "TC-3", "TC-7"] 
    return _process_test_case_4(base_test_set_dir, tc_folders_to_scan_for_vtts, output_dir_for_logs)


def testcase5(base_test_set_dir="testset", vocabulary_json_path="vocabulary.profanity.json"):
    
    logging.info(f"Starting Test Case 5 processing: Using data from 'TC-3' folder with vocabulary from: {vocabulary_json_path}")
    return _process_test_case_generic(
        base_test_set_dir, "TC-3", 
        calculate_numbers_flag=False, calculate_vocabulary_flag=True,
        vocabulary_list_path=vocabulary_json_path 
    )

def testcase6(api_durations_csv_path):
    """
    Reads API call durations from a CSV file and prepares them for merging.
    The CSV should have 'output_path' and 'duration_seconds' columns.
    'output_path' is expected to be the full path to the prediction .txt file.
    This function will attempt to parse 'PredictionFile' and 'STT_Method' from 'output_path'.
    """
    logging.info(f"--- Processing Test Case 6 (API Durations) from {api_durations_csv_path} ---")
    durations_data = []
    try:
        
        durations_df = pd.read_csv(api_durations_csv_path, dtype={'output_path': str, 'duration_seconds': float})
    except FileNotFoundError:
        logging.error(f"API durations CSV file not found: {api_durations_csv_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error reading API durations CSV {api_durations_csv_path}: {e}")
        return pd.DataFrame()

    if durations_df.empty:
        logging.warning(f"API durations CSV file is empty: {api_durations_csv_path}")
        return pd.DataFrame()

    for _, row in durations_df.iterrows():
        output_path_csv = row['output_path']
        duration = row['duration_seconds']

        if pd.isna(output_path_csv) or pd.isna(duration):
            logging.warning(f"Skipping row with NaN data in durations CSV: output_path='{output_path_csv}', duration='{duration}'")
            continue
            
        
        output_path_csv_normalized = str(output_path_csv).replace('\\', '/')
        prediction_file_name_from_csv = os.path.basename(output_path_csv_normalized) 
        
        
        
        
        
        
        
        parts = prediction_file_name_from_csv[:-len(".txt")].split('.')
        stt_method_parsed_csv = "unknown"
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        name_without_ext = prediction_file_name_from_csv[:-len(".txt")] if prediction_file_name_from_csv.endswith(".txt") else prediction_file_name_from_csv
        stt_method_parsed_csv = name_without_ext.split('.')[-1] if '.' in name_without_ext and len(name_without_ext.split('.')) > 1 else name_without_ext 
        
        
        
        

        if not stt_method_parsed_csv or stt_method_parsed_csv == name_without_ext : 
                logging.warning(f"Could not reliably parse STT method from '{prediction_file_name_from_csv}' in durations CSV. Using last part: '{stt_method_parsed_csv}'. This might cause merge issues if STT methods contain '.' or VTT stems are complex.")
        
        
        
        
        

        durations_data.append({
            "PredictionFile": prediction_file_name_from_csv, 
            "STT_Method": stt_method_parsed_csv, 
            "ResponseSpeed_s_from_csv": f"{float(duration):.3f}" if isinstance(duration, (float, int)) else "N/A"
        })
    
    if not durations_data:
        logging.warning("No duration data successfully processed from CSV.")
        return pd.DataFrame()

    result_df = pd.DataFrame(durations_data)
    logging.info(f"Successfully processed {len(result_df)} duration entries from {api_durations_csv_path}.")
    
    result_df["TestCase"] = "TC-6" 
    return result_df


def testcase7(base_test_set_dir="testset"):
    logging.info(f"Starting Test Case 7 (Noise Level Test) processing. Data from 'TC-7' folder.")
    return _process_test_case_generic(base_test_set_dir, "TC-7",
                                        calculate_numbers_flag=False, 
                                        calculate_vocabulary_flag=False) 


def pipeline(base_test_set_dir="testset", output_dir="test_case_logs", 
            hsbc_vocabulary_file="vocabulary.hsbc.json", 
            profanity_vocabulary_file="vocabulary.profanity.json",
            api_durations_csv_file_path="api_call_durations.csv"):
    """
    Runs the STT comparison pipeline for specified test cases.
    Combines results and merges API durations.
    """
    print("Starting STT comparison pipeline...")
    os.makedirs(output_dir, exist_ok=True)
    
    log_file_path = os.path.join(output_dir, 'stt_processing_details.log')
    
    logging.basicConfig(filename=log_file_path, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s', filemode='w')
    print(f"Logging details (including INFO level for vocabulary and merge diagnostics) to: {log_file_path}")
    logging.info("STT Comparison Pipeline Started.")

    all_results_dfs = [] 

    
    print("\nProcessing Test Case 1...")
    logging.info("--- Processing Test Case 1 ---")
    tc1_results_df = testcase1(base_test_set_dir)
    if not tc1_results_df.empty:
        output_path_tc1 = os.path.join(output_dir, "stt_comparison_tc1_results.csv")
        try:
            tc1_results_df.to_csv(output_path_tc1, index=False, encoding='utf-8-sig')
            print(f"TC-1 results saved to: {output_path_tc1}")
            logging.info(f"TC-1 results saved to: {output_path_tc1}")
            all_results_dfs.append(tc1_results_df)
        except Exception as e:
            print(f"Error saving TC-1 results: {e}")
            logging.error(f"Error saving TC-1 results to {output_path_tc1}: {e}")
    else:
        print("No results for TC-1 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-1.")

    
    print("\nProcessing Test Case 2...")
    logging.info("--- Processing Test Case 2 ---")
    tc2_results_df = testcase2(base_test_set_dir)
    if not tc2_results_df.empty:
        output_path_tc2 = os.path.join(output_dir, "stt_comparison_tc2_results.csv")
        try:
            tc2_results_df.to_csv(output_path_tc2, index=False, encoding='utf-8-sig')
            print(f"TC-2 results saved to: {output_path_tc2}")
            logging.info(f"TC-2 results saved to: {output_path_tc2}")
            all_results_dfs.append(tc2_results_df)
        except Exception as e:
            print(f"Error saving TC-2 results: {e}")
            logging.error(f"Error saving TC-2 results to {output_path_tc2}: {e}")
    else:
        print("No results for TC-2 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-2.")

    
    print("\nProcessing Test Case 3 (HSBC Vocabulary)...")
    logging.info("--- Processing Test Case 3 (HSBC Vocabulary) ---")
    tc3_results_df = testcase3(base_test_set_dir, vocabulary_json_path=hsbc_vocabulary_file)
    if not tc3_results_df.empty:
        output_path_tc3 = os.path.join(output_dir, "stt_comparison_tc3_results.csv")
        try:
            tc3_results_df.to_csv(output_path_tc3, index=False, encoding='utf-8-sig')
            print(f"TC-3 results (HSBC vocab) saved to: {output_path_tc3}")
            logging.info(f"TC-3 results (HSBC vocab) saved to: {output_path_tc3}")
            all_results_dfs.append(tc3_results_df)
        except Exception as e:
            print(f"Error saving TC-3 results: {e}")
            logging.error(f"Error saving TC-3 results to {output_path_tc3}: {e}")
    else:
        print("No results for TC-3 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-3.")

    
    print("\nProcessing Test Case 4 (Segmentation Accuracy)...")
    logging.info("--- Processing Test Case 4 (Segmentation Accuracy) ---")
    tc4_results_df = testcase4(base_test_set_dir, output_dir_for_logs=output_dir)
    if not tc4_results_df.empty:
        output_path_tc4 = os.path.join(output_dir, "stt_comparison_tc4_results.csv")
        try:
            tc4_results_df.to_csv(output_path_tc4, index=False, encoding='utf-8-sig')
            print(f"TC-4 results saved to: {output_path_tc4}")
            logging.info(f"TC-4 results saved to: {output_path_tc4}")
            all_results_dfs.append(tc4_results_df) 
        except Exception as e:
            print(f"Error saving TC-4 results: {e}")
            logging.error(f"Error saving TC-4 results to {output_path_tc4}: {e}")
    else:
        print("No results for TC-4 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-4.")

    
    print("\nProcessing Test Case 5 (TC-3 data with Profanity Vocabulary)...")
    logging.info("--- Processing Test Case 5 (TC-3 data with Profanity Vocabulary) ---")
    tc5_results_df = testcase5(base_test_set_dir, vocabulary_json_path=profanity_vocabulary_file) 
    if not tc5_results_df.empty:
        
        tc5_results_df["TestCase"] = "TC-5" 
        output_path_tc5 = os.path.join(output_dir, "stt_comparison_tc5_results.csv")
        try:
            tc5_results_df.to_csv(output_path_tc5, index=False, encoding='utf-8-sig')
            print(f"TC-5 results (TC-3 data, profanity vocab, labeled as TC-5) saved to: {output_path_tc5}")
            logging.info(f"TC-5 results (TC-3 data, profanity vocab, labeled as TC-5) saved to: {output_path_tc5}")
            all_results_dfs.append(tc5_results_df)
        except Exception as e:
            print(f"Error saving TC-5 results: {e}")
            logging.error(f"Error saving TC-5 results to {output_path_tc5}: {e}")
    else:
        print("No results for TC-5 (TC-3 data, profanity vocab) or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-5 (TC-3 data, profanity vocab).")

    
    print("\nProcessing Test Case 7 (Noise Level Test)...")
    logging.info("--- Processing Test Case 7 (Noise Level Test) ---")
    tc7_results_df = testcase7(base_test_set_dir)
    if not tc7_results_df.empty:
        output_path_tc7 = os.path.join(output_dir, "stt_comparison_tc7_results.csv")
        try:
            tc7_results_df.to_csv(output_path_tc7, index=False, encoding='utf-8-sig')
            print(f"TC-7 results saved to: {output_path_tc7}")
            logging.info(f"TC-7 results saved to: {output_path_tc7}")
            all_results_dfs.append(tc7_results_df)
        except Exception as e:
            print(f"Error saving TC-7 results: {e}")
            logging.error(f"Error saving TC-7 results to {output_path_tc7}: {e}")
    else:
        print("No results for TC-7 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-7.")

    
    
    print("\nProcessing Test Case 6 (API Durations)...")
    logging.info(f"--- Processing Test Case 6 (API Durations) from: {api_durations_csv_file_path} ---")
    tc6_durations_df = testcase6(api_durations_csv_file_path) 
    if not tc6_durations_df.empty:
        output_path_tc6_standalone = os.path.join(output_dir, "stt_comparison_tc6_results.csv")
        try:
            
            tc6_durations_df.to_csv(output_path_tc6_standalone, index=False, encoding='utf-8-sig')
            print(f"TC-6 raw extracted API duration data saved to: {output_path_tc6_standalone}")
            logging.info(f"TC-6 raw extracted API duration data saved to: {output_path_tc6_standalone}")
        except Exception as e:
            print(f"Error saving standalone TC-6 extracted data: {e}")
            logging.error(f"Error saving standalone TC-6 extracted data to {output_path_tc6_standalone}: {e}")
    else:
        print("No API duration data processed for TC-6 or error occurred. Check logs.")
        logging.warning("No results dataframe generated for TC-6 (API Durations). tc6_durations_df is empty.")


    
    combined_results_df = None 
    if all_results_dfs: 
        combined_results_df = pd.concat(all_results_dfs, ignore_index=True)
        logging.info(f"Combined results from TC1-TC5, TC7 created with {len(combined_results_df)} rows before TC6 merge.")
        
        
        if 'ResponseSpeed_s' not in combined_results_df.columns:
            combined_results_df['ResponseSpeed_s'] = "N/A"
        initial_speeds_populated = combined_results_df[combined_results_df['ResponseSpeed_s'] != "N/A"].shape[0]

        if not tc6_durations_df.empty:
            logging.info(f"Attempting to merge {len(tc6_durations_df)} duration entries from TC6 into main results ({len(combined_results_df)} rows).")
            logging.info(f"Merge keys: ['PredictionFile', 'STT_Method']")
            
            
            logging.info(f"Pre-merge: combined_results_df shape: {combined_results_df.shape}")
            if not combined_results_df.empty:
                logging.info(f"Sample keys from combined_results_df (first 5 rows, relevant columns for merge):\n{combined_results_df[['TestCase', 'PredictionFile', 'STT_Method']].head().to_string()}")
            
            logging.info(f"Pre-merge: tc6_durations_df shape: {tc6_durations_df.shape}")
            if not tc6_durations_df.empty:
                logging.info(f"Sample keys from tc6_durations_df (first 5 rows, relevant columns for merge):\n{tc6_durations_df[['PredictionFile', 'STT_Method', 'ResponseSpeed_s_from_csv']].head().to_string()}")

            
            
            
            merged_df_with_indicator = pd.merge(
                combined_results_df, 
                tc6_durations_df.drop(columns=['TestCase'], errors='ignore'), 
                on=["PredictionFile", "STT_Method"], 
                how="left",
                indicator=True 
            )
            logging.info(f"Post-merge: merged_df_with_indicator shape: {merged_df_with_indicator.shape}")
            
            merge_counts = merged_df_with_indicator['_merge'].value_counts()
            logging.info(f"Merge indicator counts ('_merge' column):\n{merge_counts.to_string()}")
            
            successful_merges = merge_counts.get('both', 0) 
            left_only_merges = merge_counts.get('left_only',0) 

            logging.info(f"Number of rows in combined_results_df that successfully merged with TC6 data (found a match): {successful_merges}")
            logging.info(f"Number of rows in combined_results_df that did NOT find a match in TC6 data: {left_only_merges}")

            if successful_merges == 0 and not tc6_durations_df.empty and not combined_results_df.empty :
                logging.warning("TC6 MERGE DIAGNOSTIC: No rows from tc6_durations_df matched any rows in combined_results_df. "
                                "This means 'ResponseSpeed_s' could not be updated from TC6 data. "
                                "Critical Check Needed: 'PredictionFile' and 'STT_Method' values must be *exactly identical* between the TC6 CSV data "
                                "(see 'stt_comparison_tc6_durations_extracted.csv') and the main test case results (e.g., 'stt_comparison_tc1_results.csv'). "
                                "Verify consistent filename parsing and STT method naming conventions.")
            
            combined_results_df = merged_df_with_indicator.drop(columns=['_merge']) 

            
            if 'ResponseSpeed_s_from_csv' in combined_results_df.columns:
                combined_results_df['ResponseSpeed_s'] = combined_results_df['ResponseSpeed_s_from_csv'].combine_first(combined_results_df['ResponseSpeed_s'])
                combined_results_df.drop(columns=['ResponseSpeed_s_from_csv'], inplace=True)
                
                final_speeds_populated = combined_results_df[combined_results_df['ResponseSpeed_s'] != "N/A"].shape[0]
                num_updated_by_tc6 = final_speeds_populated - initial_speeds_populated
                logging.info(f"'ResponseSpeed_s' column updated. {num_updated_by_tc6} rows had their speed value newly populated or changed by TC6 data.")
                if num_updated_by_tc6 == 0 and successful_merges > 0:
                        logging.warning("TC6 MERGE DIAGNOSTIC: Merge indicated matches, but no 'ResponseSpeed_s' values were actually changed. "
                                        "This could happen if all matched TC6 rows had 'N/A' for 'ResponseSpeed_s_from_csv' or if the original 'ResponseSpeed_s' was already populated and identical.")
            else:
                
                
                logging.warning("After attempting to merge TC6 data, the 'ResponseSpeed_s_from_csv' column was not found in the merged DataFrame. "
                                "Durations from TC6 may not have been correctly integrated. Check tc6_durations_df structure.")
        else: 
            logging.info("No TC6 duration data (tc6_durations_df is empty) to merge with other test case results.")
            if 'ResponseSpeed_s' not in combined_results_df.columns: 
                combined_results_df['ResponseSpeed_s'] = "N/A"
            
    elif not tc6_durations_df.empty: 
        logging.warning("Only TC6 duration data was generated (no results from TC1-5, TC7). The combined report will only contain this TC6 data.")
        
        combined_results_df = tc6_durations_df.rename(columns={"ResponseSpeed_s_from_csv": "ResponseSpeed_s"})
        
        if "TestCase" not in combined_results_df.columns: 
            combined_results_df["TestCase"] = "TC-6" 
        
        standard_cols_to_add = ["SourceTestCaseVTT", "LanguageSubFolder", "FolderType", "NoiseLevel_Percent", 
                                "GroundTruthFile", "WER", "WRR_Percent", "NumberAccuracy_Percent", 
                                "VocabularyAccuracy_Percent", "SegmentationAccuracy_Percent", "GT_Segments_Count",
                                "GT_Text_Raw", "Pred_Text_Raw", "Pred_Text_Raw_Snippet",
                                "GT_Numbers_Extracted", "Pred_Numbers_Extracted",
                                "GT_Vocabs_Found", "Pred_Vocabs_Matched"]
        for col in standard_cols_to_add:
            if col not in combined_results_df.columns:
                combined_results_df[col] = "N/A"
    else: 
        print("\nNo results generated from any test case (TC1-5, TC7, or TC6). Cannot create combined report.")
        logging.error("STT Comparison Pipeline Finished: No data from any test case to save.")
        return 

    
    if combined_results_df is not None and not combined_results_df.empty:
        logging.info(f"Final combined DataFrame for saving has {len(combined_results_df)} rows and columns: {combined_results_df.columns.tolist()}")
        
        
        cols_order = [
            "TestCase", "SourceTestCaseVTT", "LanguageSubFolder", "FolderType", 
            "NoiseLevel_Percent", "GroundTruthFile", "PredictionFile", "STT_Method",
            "WER", "WRR_Percent", "NumberAccuracy_Percent", "VocabularyAccuracy_Percent", "SegmentationAccuracy_Percent",
            "ResponseSpeed_s", "GT_Segments_Count", 
            "GT_Text_Raw", "Pred_Text_Raw", "Pred_Text_Raw_Snippet",
            "GT_Numbers_Extracted", "Pred_Numbers_Extracted",
            "GT_Vocabs_Found", "Pred_Vocabs_Matched"
        ]
        
        
        for col in cols_order:
            if col not in combined_results_df.columns:
                combined_results_df[col] = "N/A" 

        
        present_cols_in_order = [col for col in cols_order if col in combined_results_df.columns]
        additional_cols = sorted([col for col in combined_results_df.columns if col not in present_cols_in_order])
        final_ordered_columns = present_cols_in_order + additional_cols
        
        combined_results_df = combined_results_df[final_ordered_columns]

        output_path_combined = os.path.join(output_dir, "stt_comparison_all_tc_results.csv")
        try:
            combined_results_df.to_csv(output_path_combined, index=False, encoding='utf-8-sig')
            print(f"\nAll test case results combined and saved to: {output_path_combined}")
            logging.info(f"All test case results combined and saved to: {output_path_combined}. Final shape: {combined_results_df.shape}")
        except Exception as e:
            print(f"Error saving combined results: {e}")
            logging.error(f"Error saving combined results to {output_path_combined}: {e}")
    else:
        print("\nNo combined results to save (DataFrame is None or empty after processing all TCs).")
        logging.warning("No combined results DataFrame was generated or it was empty at the saving stage.")

    print("\nPipeline finished.")
    logging.info("STT Comparison Pipeline Finished.")

if __name__ == "__main__":
    print("Attempting to run STT comparison pipeline.")
    print("Ensure 'testset/TC-1/', 'testset/TC-2/', 'testset/TC-3/', 'testset/TC-7/' directories are structured correctly.")
    print("The 'testset' directory, vocabulary JSON files, and 'api_call_durations.csv' should be accessible from the script's location or specified with full paths.")
    
    
    base_test_directory = "testset" 
    results_and_logs_directory = "test_case_logs" 
    hsbc_vocab_json_file = "vocabulary.hsbc.json"
    profanity_vocab_json_file = "vocabulary.profanity.json"
    api_durations_file = "api_call_durations.csv" 

    pipeline(base_test_set_dir=base_test_directory, 
            output_dir=results_and_logs_directory,
            hsbc_vocabulary_file=hsbc_vocab_json_file,
            profanity_vocabulary_file=profanity_vocab_json_file,
            api_durations_csv_file_path=api_durations_file)
