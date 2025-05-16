import os
import re
import jiwer
import opencc 
import logging
import csv
from collections import defaultdict

DETAILED_LOG_FILE = "stt_evaluation_details.log"
SUMMARY_REPORT_FILE = "stt_summary_report.csv"
HYPOTHESIS_FILE_EXTENSION = ".txt"
GROUND_TRUTH_EXTENSION = ".vtt"

def setup_logger():
    """Configures the logger to write to a file and console."""
    logger = logging.getLogger('STT_Evaluation')
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler(DETAILED_LOG_FILE, mode='w', encoding='utf-8')
    fh.setLevel(logging.INFO)
    formatter_fh = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter_fh)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter_ch = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter_ch)
    logger.addHandler(ch)
    return logger

logger = setup_logger()


try:
    s2t_converter = opencc.OpenCC('s2t.json') 
    logger.info("OpenCC Initialized: Simplified to Traditional Chinese conversion enabled for hypotheses.")
except Exception as e:
    logger.warning(f"Could not initialize OpenCC converter ('s2t.json'): {e}. "
                   "Proceeding without Chinese script conversion for hypotheses. This may significantly affect accuracy.")
    s2t_converter = None


def read_vtt_file(file_path):
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

def preprocess_text(text, convert_to_traditional=False):
    if not text:
        return ""
    if convert_to_traditional and s2t_converter:
        text = s2t_converter.convert(text)
    punctuation = (
        r"""＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏﹑﹔·！？｡。"""
        r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    )
    text = re.sub(f"[{re.escape(punctuation)}]", "", text)
    text = re.sub(r'\s+', '', text)
    text = text.lower()
    return text

def calculate_stt_metrics(ground_truth, hypothesis):
    if not ground_truth and not hypothesis: wer, cer = 0.0, 0.0
    elif not ground_truth: wer, cer = 1.0, 1.0
    elif not hypothesis: wer, cer = 1.0, 1.0
    else:
        try: wer = jiwer.wer(ground_truth, hypothesis)
        except Exception as e:
            logger.debug(f"JiWER WER calculation error: {e}. GT='{ground_truth}', HYP='{hypothesis}'")
            wer = 1.0
        try: cer = jiwer.cer(ground_truth, hypothesis)
        except Exception as e:
            logger.debug(f"JiWER CER calculation error: {e}. GT='{ground_truth}', HYP='{hypothesis}'")
            cer = 1.0
    wrr = 1.0 - wer
    return {"WER": wer, "WRR": wrr, "CER": cer}


def main(root_dir):
    all_results_data = [] 
    file_pairs_found = 0
    files_processed_successfully = 0

    logger.info(f"Starting STT accuracy calculation in root directory: {root_dir}")
    logger.info(f"Mode: Comparing against Ground Truth in Traditional Chinese. Hypotheses will be converted to Traditional Chinese.")
    logger.info(f"Detailed logs will be saved to: {DETAILED_LOG_FILE}")
    logger.info(f"Summary report will be saved to: {SUMMARY_REPORT_FILE}")

    for subdir, _, files in os.walk(root_dir):
        for hyp_file_name in files:
            if not hyp_file_name.endswith(HYPOTHESIS_FILE_EXTENSION):
                continue

            name_parts = hyp_file_name.rsplit('.', 2)
            method_name = "unknown_method" 

            if len(name_parts) == 3 and name_parts[2] == HYPOTHESIS_FILE_EXTENSION.strip('.'):
                base_name_for_gt = name_parts[0]
                method_name = name_parts[1]
                hyp_path = os.path.join(subdir, hyp_file_name)
                gt_file_name = base_name_for_gt + GROUND_TRUTH_EXTENSION
                gt_path = os.path.join(subdir, gt_file_name)
            else:
                base_name_for_gt = hyp_file_name[:-len(HYPOTHESIS_FILE_EXTENSION)]
                hyp_path = os.path.join(subdir, hyp_file_name)
                gt_file_name = base_name_for_gt + GROUND_TRUTH_EXTENSION
                gt_path = os.path.join(subdir, gt_file_name)

            if os.path.exists(gt_path):
                file_pairs_found += 1
                logger.info(f"--- Processing Pair {file_pairs_found} (Method: {method_name}) ---")
                logger.info(f"  GT_File: {gt_path}")
                logger.info(f"  HYP_File: {hyp_path}")

                raw_gt = read_vtt_file(gt_path)
                raw_hyp = read_txt_file(hyp_path)

                if raw_gt is None or raw_hyp is None:
                    logger.warning("  Skipping pair due to read error for one or both files.")
                    logger.info("--- End Pair Processing ---")
                    continue
                
                logger.debug(f"  Raw GT: '{raw_gt[:150]}{'...' if len(raw_gt)>150 else ''}'")
                logger.debug(f"  Raw HYP: '{raw_hyp[:150]}{'...' if len(raw_hyp)>150 else ''}'")

                processed_gt = preprocess_text(raw_gt, convert_to_traditional=False)
                processed_hyp = preprocess_text(raw_hyp, convert_to_traditional=True)

                logger.info(f"  Processed GT (Traditional): '{processed_gt}'")
                logger.info(f"  Processed HYP (Traditional): '{processed_hyp}'")

                metrics = calculate_stt_metrics(processed_gt, processed_hyp)
                logger.info(f"  Metrics: WER={metrics['WER']:.4f}, WRR={metrics['WRR']:.4f}, CER={metrics['CER']:.4f}")

                all_results_data.append({
                    "method": method_name,
                    "gt_file": gt_path,
                    "hyp_file": hyp_path,
                    **metrics
                })
                files_processed_successfully += 1
                logger.info("--- End Pair Processing ---")
            else:
                
                logger.debug(f"Ground truth file not found for hypothesis {hyp_path} (expected at {gt_path})")


    logger.info(f"Finished processing files. Total pairs found: {file_pairs_found}. Pairs successfully processed: {files_processed_successfully}.")

    if files_processed_successfully > 0:
        generate_summary_report(all_results_data)
    else:
        logger.info("No files were successfully processed, so no summary report will be generated.")


def generate_summary_report(all_results_data):
    """Generates a CSV summary report of metrics grouped by method."""
    if not all_results_data:
        logger.info("No data available to generate summary report.")
        return

    method_summary = defaultdict(lambda: {"total_wer": 0, "total_wrr": 0, "total_cer": 0, "count": 0})

    for result in all_results_data:
        method = result["method"]
        method_summary[method]["total_wer"] += result["WER"]
        method_summary[method]["total_wrr"] += result["WRR"]
        method_summary[method]["total_cer"] += result["CER"]
        method_summary[method]["count"] += 1

    logger.info(f"Generating summary report at: {SUMMARY_REPORT_FILE}")

    try:
        with open(SUMMARY_REPORT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Method', 'File_Count', 'Average_WER', 'Average_WRR', 'Average_CER']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            sorted_methods = sorted(method_summary.keys())

            for method in sorted_methods:
                data = method_summary[method]
                count = data['count']
                avg_wer = data['total_wer'] / count if count > 0 else 0
                avg_wrr = data['total_wrr'] / count if count > 0 else 0 
                avg_cer = data['total_cer'] / count if count > 0 else 0
                writer.writerow({
                    'Method': method,
                    'File_Count': count,
                    'Average_WER': f"{avg_wer:.4f}",
                    'Average_WRR': f"{avg_wrr:.4f}",
                    'Average_CER': f"{avg_cer:.4f}"
                })
        logger.info("Summary report generated successfully.")
    except IOError as e:
        logger.error(f"Failed to write summary report: {e}")

if __name__ == "__main__":
    root_folder = "sampled_testcase" 

    if os.path.isdir(root_folder):
        main(root_folder)
    else:
        logger.error(f"Root directory '{root_folder}' not found.")
        logger.error("Please ensure the path is correct or create the directory with your test files.")