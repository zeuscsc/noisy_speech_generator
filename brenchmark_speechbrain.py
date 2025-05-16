import os
import re
import opencc
import logging
import csv
from collections import defaultdict
from tqdm import tqdm

try:
    from speechbrain.utils.metric_stats import ErrorRateStats
    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False

DETAILED_LOG_FILE = "stt_evaluation_details_speechbrain.log"
SUMMARY_REPORT_FILE = "stt_summary_report_speechbrain.csv"
HYPOTHESIS_FILE_EXTENSION = ".txt"
GROUND_TRUTH_EXTENSION = ".vtt"
OPENCC_CONFIG = 's2hk.json'

def setup_logger():
    logger = logging.getLogger('STT_Evaluation_SpeechBrain')
    logger.handlers = []
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(DETAILED_LOG_FILE, mode='w', encoding='utf-8')
    fh.setLevel(logging.INFO)
    formatter_fh = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter_fh)
    logger.addHandler(fh)

    return logger

logger = setup_logger()

if not SPEECHBRAIN_AVAILABLE:
    logger.error("SpeechBrain library not found. Please install it: pip install speechbrain")

try:
    converter = opencc.OpenCC(OPENCC_CONFIG)
    logger.info(f"OpenCC Initialized: Using '{OPENCC_CONFIG}'.")
except Exception as e:
    logger.warning(f"Could not initialize OpenCC converter ('{OPENCC_CONFIG}'): {e}. "
                   "Proceeding without Chinese script conversion.")
    converter = None

def read_vtt_file(file_path):
    """Reads WebVTT file and extracts continuous text, removing timestamps and tags."""
    lines = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line == "WEBVTT" or "-->" in line or not line:
                    continue
                line = re.sub(r'<[^>]+>', '', line)
                lines.append(line)
    except Exception as e:
        logger.error(f"Error reading VTT file {file_path}: {e}")
        return None
    return " ".join(lines)

def read_txt_file(file_path):
    """Reads hypothesis TXT file, skipping specific header lines."""
    transcription_lines = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("Detected language") or \
                   line.startswith("TRANSCRIPTION:") or \
                   line.startswith("UTTERANCE "):
                    continue
                if line:
                    transcription_lines.append(line)
    except Exception as e:
        logger.error(f"Error reading TXT file {file_path}: {e}")
        return None
    return " ".join(transcription_lines)

def preprocess_text_for_logging(text, perform_chinese_conversion=False):
    """
    Normalizes text for logging:
    - Optionally converts Chinese script.
    - Removes punctuation.
    - Converts to lowercase.
    - Normalizes whitespace to single spaces.
    """
    if not text:
        return ""
    if perform_chinese_conversion and converter:
        text = converter.convert(text)
    
    punctuation = (
        r"""＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏﹑﹔·！？｡。"""
        r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    )
    text = re.sub(f"[{re.escape(punctuation)}]", "", text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def preprocess_text_for_metrics(text, perform_chinese_conversion=False):
    """
    Normalizes text for STT metric calculation:
    - Optionally converts Chinese script.
    - Removes punctuation.
    - Converts to lowercase.
    - Removes ALL whitespace for character-level comparison.
    """
    if not text:
        return ""
    if perform_chinese_conversion and converter:
        original_text_snippet = text[:30]
        text = converter.convert(text)
        if text != original_text_snippet:
             logger.debug(f"Applied OpenCC conversion for metrics: '{original_text_snippet}...' -> '{text[:30]}...'")

    punctuation = (
        r"""＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏﹑﹔·！？｡。"""
        r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    )
    text = re.sub(f"[{re.escape(punctuation)}]", "", text)
    text = text.lower()
    text = re.sub(r'\s+', '', text)
    return text

def calculate_stt_metrics_speechbrain(ground_truth_str, hypothesis_str):
    """
    Calculates STT metrics using SpeechBrain.
    Note: Tokenizes by character, so WER reported is effectively CER.
    """
    if not SPEECHBRAIN_AVAILABLE:
        logger.error("SpeechBrain not available for metrics calculation.")
        return {"WER": float('nan'), "WRR": float('nan'), "CER": float('nan'), "SER": float('nan')}

    calculated_wer = float('nan')
    calculated_cer = float('nan')
    wrr = float('nan')
    ser_segment = float('nan')

    if not ground_truth_str and not hypothesis_str:
        calculated_wer, calculated_cer, ser_segment = 0.0, 0.0, 0.0
        wrr = 1.0
    elif not ground_truth_str:
        calculated_wer, calculated_cer, ser_segment = 1.0, 1.0, 1.0
        wrr = 0.0
    elif not hypothesis_str:
        calculated_wer, calculated_cer, ser_segment = 1.0, 1.0, 1.0
        wrr = 0.0
    else:
        ref_tokens = list(ground_truth_str)
        hyp_tokens = list(hypothesis_str)
        try:
            error_computer = ErrorRateStats()
            error_computer.append(ids=["segment1"], predict=[hyp_tokens], target=[ref_tokens])
            stats = error_computer.summarize()
            error_val = stats.get('error_rate')

            if error_val is None:
                logger.warning(f"SpeechBrain 'error_rate' not found in summary: {stats}. Defaulting error to 1.0 for this segment.")
                error_val = 100.0
            
            calculated_cer = error_val / 100.0
            calculated_wer = calculated_cer 
            wrr = 1.0 - calculated_wer
            ser_segment = 1.0 if calculated_wer > 1e-9 else 0.0
        except Exception as e:
            logger.error(f"Error during SpeechBrain metrics calculation: {e}")
            logger.error(f"  GT (len {len(ground_truth_str)}): '{ground_truth_str[:70]}...'")
            logger.error(f"  HYP (len {len(hypothesis_str)}): '{hypothesis_str[:70]}...'")
    return {"WER": calculated_wer, "WRR": wrr, "CER": calculated_cer, "SER": ser_segment}

def main(root_dir):
    all_results_data = []
    file_pairs_found = 0
    files_processed_successfully = 0

    logger.info(f"Starting STT accuracy calculation using SpeechBrain in root directory: {root_dir}")
    logger.info(f"Mode: Comparing Ground Truth (.vtt) against Hypothesis (.txt).")
    if converter:
        logger.info(f"Chinese script conversion for GT and Hypotheses enabled via OpenCC ({OPENCC_CONFIG}).")
    else:
        logger.info("OpenCC not available/enabled; no Chinese script conversion will be performed.")
    logger.info(f"Metrics calculated: CER (reported as WER/CER), CRR (reported as WRR), SER.")
    logger.info(f"Detailed logs will be saved to: {DETAILED_LOG_FILE}")
    logger.info(f"Summary report will be saved to: {SUMMARY_REPORT_FILE}")

    walk_items = list(os.walk(root_dir))
    if not walk_items:
        logger.warning(f"Root directory '{root_dir}' is empty or not accessible.")
        return

    main_pbar = tqdm(walk_items, desc="Scanning Dirs", unit="dir", position=0, dynamic_ncols=True)
    for subdir, _, files in main_pbar:
        current_dir_name = os.path.relpath(subdir, root_dir) if subdir != root_dir else os.path.basename(root_dir)
        if not current_dir_name or current_dir_name == '.':
            current_dir_name = os.path.basename(root_dir)
        main_pbar.set_description(f"Processing Dir: {current_dir_name[:30]}")

        hyp_files_in_subdir = [f for f in files if f.endswith(HYPOTHESIS_FILE_EXTENSION)]
        if not hyp_files_in_subdir:
            continue

        sub_pbar = tqdm(hyp_files_in_subdir, desc="Files", unit="file", leave=False, position=1, dynamic_ncols=True)
        for hyp_file_name in sub_pbar:
            sub_pbar.set_description(f"{hyp_file_name[:25].ljust(25)}...")

            base_with_method = hyp_file_name[:-len(HYPOTHESIS_FILE_EXTENSION)]
            parts = base_with_method.rsplit('.', 1)
            if len(parts) == 2:
                base_name_for_gt = parts[0]
                method_name = parts[1]
            else:
                base_name_for_gt = base_with_method 
                method_name = "unknown_method"
                logger.debug(f"Could not parse method from hyp_file '{hyp_file_name}'. Using method '{method_name}'. Expected format 'basename.method.txt'.")
            
            gt_file_name = base_name_for_gt + GROUND_TRUTH_EXTENSION
            gt_path = os.path.join(subdir, gt_file_name)
            hyp_path = os.path.join(subdir, hyp_file_name)

            if os.path.exists(gt_path):
                file_pairs_found += 1
                logger.info(f"--- Processing Pair {file_pairs_found} (Method: {method_name}) ---")
                logger.info(f"  GT_File: {gt_path}")
                logger.info(f"  HYP_File: {hyp_path}")

                raw_gt = read_vtt_file(gt_path)
                raw_hyp = read_txt_file(hyp_path)

                if raw_gt is None or raw_hyp is None:
                    logger.warning(f"  Skipping pair due to read error: GT='{gt_path}', HYP='{hyp_path}'")
                    logger.info("--- End Pair Processing (Read Error) ---")
                    main_pbar.set_postfix(pairs=file_pairs_found, success=files_processed_successfully, refresh=True)
                    continue
                
                logger.debug(f"Raw GT (Pair {file_pairs_found} {os.path.basename(gt_path)}): '{raw_gt[:70]}{'...' if len(raw_gt)>70 else ''}'")
                logger.debug(f"Raw HYP (Pair {file_pairs_found} {os.path.basename(hyp_path)}): '{raw_hyp[:70]}{'...' if len(raw_hyp)>70 else ''}'")

                apply_conversion = converter is not None
                
                gt_for_readable_log = preprocess_text_for_logging(raw_gt, perform_chinese_conversion=apply_conversion)
                hyp_for_readable_log = preprocess_text_for_logging(raw_hyp, perform_chinese_conversion=apply_conversion)

                processed_gt_for_metrics = preprocess_text_for_metrics(raw_gt, perform_chinese_conversion=apply_conversion)
                processed_hyp_for_metrics = preprocess_text_for_metrics(raw_hyp, perform_chinese_conversion=apply_conversion)

                logger.info(f"(Method: {method_name}) Pair {file_pairs_found}:")
                logger.info(f"  GT  (readable log): '{gt_for_readable_log[:70]}...' (len: {len(gt_for_readable_log)})")
                logger.info(f"  HYP (readable log): '{hyp_for_readable_log[:70]}...' (len: {len(hyp_for_readable_log)})")
                logger.info(f"  GT  (for metrics): '{processed_gt_for_metrics[:50]}...' (len: {len(processed_gt_for_metrics)})")
                logger.info(f"  HYP (for metrics): '{processed_hyp_for_metrics[:50]}...' (len: {len(processed_hyp_for_metrics)})")

                if not processed_gt_for_metrics and not processed_hyp_for_metrics:
                    metrics = {"WER": 0.0, "WRR": 1.0, "CER": 0.0, "SER": 0.0}
                elif not processed_gt_for_metrics:
                     metrics = {"WER": 1.0, "WRR": 0.0, "CER": 1.0, "SER": 1.0}
                elif not processed_hyp_for_metrics:
                     metrics = {"WER": 1.0, "WRR": 0.0, "CER": 1.0, "SER": 1.0}
                else:
                    metrics = calculate_stt_metrics_speechbrain(processed_gt_for_metrics, processed_hyp_for_metrics)

                logger.info(f"  Metrics (Pair {file_pairs_found} {os.path.basename(hyp_path)}):")
                logger.info(f"    WER (CER)={metrics['WER']:.4f}, WRR (CRR)={metrics['WRR']:.4f}, CER={metrics['CER']:.4f}, SER={metrics['SER']:.4f}")

                all_results_data.append({
                    "method": method_name,
                    "gt_file": os.path.basename(gt_path),
                    "hyp_file": os.path.basename(hyp_path),
                    **metrics
                })
                files_processed_successfully += 1
                logger.info("--- End Pair Processing ---")
            else:
                logger.debug(f"Ground truth file not found for hypothesis {hyp_path} (expected at {gt_path})")
            
            main_pbar.set_postfix(pairs=file_pairs_found, success=files_processed_successfully, refresh=True)
        sub_pbar.close()
    main_pbar.close()

    logger.info(f"Finished processing files. Total pairs found: {file_pairs_found}. Pairs successfully processed: {files_processed_successfully}.")

    if files_processed_successfully > 0:
        generate_summary_report(all_results_data)
    else:
        logger.info("No files were successfully processed, so no summary report will be generated.")

def generate_summary_report(all_results_data):
    if not all_results_data:
        logger.info("No data available to generate summary report.")
        return

    method_summary = defaultdict(lambda: {"total_wer": 0.0, "total_wrr": 0.0, "total_cer": 0.0, "total_ser": 0.0, "count": 0, "nan_count": 0})

    for result in all_results_data:
        method = result["method"]
        current_metrics = [result["WER"], result["WRR"], result["CER"], result["SER"]]
        if any(m != m for m in current_metrics): 
            method_summary[method]["nan_count"] += 1
            logger.warning(f"NaN metric found for method '{method}', file '{result['hyp_file']}'. It will be excluded from averages.")
            continue 

        method_summary[method]["total_wer"] += result["WER"]
        method_summary[method]["total_wrr"] += result["WRR"]
        method_summary[method]["total_cer"] += result["CER"]
        method_summary[method]["total_ser"] += result["SER"]
        method_summary[method]["count"] += 1
    
    logger.info(f"Generating summary report at: {SUMMARY_REPORT_FILE}")
    try:
        with open(SUMMARY_REPORT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Method', 'File_Count (Valid Metrics)', 'Average_WER (CER)', 'Average_WRR (CRR)', 'Average_CER', 'Average_SER', 'Files_With_Metric_Errors']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            sorted_methods = sorted(method_summary.keys())

            for method in sorted_methods:
                data = method_summary[method]
                count = data['count']
                nan_count = data['nan_count']
                
                avg_wer = data['total_wer'] / count if count > 0 else 0
                avg_wrr = data['total_wrr'] / count if count > 0 else 0
                avg_cer = data['total_cer'] / count if count > 0 else 0
                avg_ser = data['total_ser'] / count if count > 0 else 0
                
                writer.writerow({
                    'Method': method,
                    'File_Count (Valid Metrics)': count,
                    'Average_WER (CER)': f"{avg_wer:.4f}",
                    'Average_WRR (CRR)': f"{avg_wrr:.4f}",
                    'Average_CER': f"{avg_cer:.4f}",
                    'Average_SER': f"{avg_ser:.4f}",
                    'Files_With_Metric_Errors': nan_count
                })
        logger.info("Summary report generated successfully.")
    except IOError as e:
        logger.error(f"Failed to write summary report: {e}")

if __name__ == "__main__":
    root_folder = "sampled_testcase" 
    
    if not SPEECHBRAIN_AVAILABLE:
        logger.error("Exiting: SpeechBrain is required but not found. Please install it: pip install speechbrain")
        exit(1)
    
    if os.path.isdir(root_folder):
        main(root_folder)
    else:
        logger.error(f"Root directory '{root_folder}' not found.")
        logger.error("Please ensure the path is correct or create the directory with your test files.")
        logger.error("Example structure: root_folder/subdirectory/audiofile.vtt")
        logger.error("                                         /audiofile.stt_method1.txt")
        logger.error("                                         /audiofile.stt_method2.txt")