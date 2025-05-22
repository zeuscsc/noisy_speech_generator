import csv
import os
import statistics
from collections import defaultdict


BASE_PATH = "test_case_logs" 
OUTPUT_FILE = "summary_report_by_provider.md"

TEST_CASE_CONFIG = {
    "TC-1": {
        "title": "Multilingual Support",
        "file_name": "stt_comparison_tc1_results.csv",
        "input_desc": "Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 4s to 10s.\nGround truth transcriptions for each clip.",
        "output_desc": "WER (Word Error Rate), WRR (Word Recognition Rate) for each language.",
        "relevant_cols": ["LanguageSubFolder", "WER", "WRR_Percent"],
        "group_by_col": "LanguageSubFolder",
        "metrics_to_process": {"WER": "avg", "WRR_Percent": "avg"},
        "report_headers": ["Language", "Average WER (%)", "Average WRR (%)"]
    },
    "TC-2": {
        "title": "Robustness Across Accents",
        "file_name": "stt_comparison_tc2_results.csv",
        "input_desc": "Voice datasets for each language (Cantonese-HK with Mandarin accent, Mandarin with Cantonese accent, English with Southeast Asian accent, English with Indian accent), with length ranging from 4s to 10s.\nGround truth transcriptions for each clip.",
        "output_desc": "WER (Word Error Rate), WRR (Word Recognition Rate) and for each language.",
        "relevant_cols": ["LanguageSubFolder", "WER", "WRR_Percent"],
        "group_by_col": "LanguageSubFolder",
        "metrics_to_process": {"WER": "avg", "WRR_Percent": "avg"},
        "report_headers": ["Accent/Language", "Average WER (%)", "Average WRR (%)"]
    },
    "TC-3": {
        "title": "Domain Vocabulary Support",
        "file_name": "stt_comparison_tc3_results.csv",
        "input_desc": "Voice datasets for each language (English, Cantonese-HK), with length ranging from 4s to 10s, where HSBC specific terms are mentioned.\nGround truth transcriptions for each clip.",
        "output_desc": "WER (Word Error Rate), and full vocab recognition for each language.",
        "relevant_cols": ["LanguageSubFolder", "WER", "VocabularyAccuracy_Percent"],
        "group_by_col": "LanguageSubFolder",
        "metrics_to_process": {"WER": "avg", "VocabularyAccuracy_Percent": "avg"},
        "report_headers": ["Language", "Average WER (%)", "Average Vocabulary Accuracy (%)"]
    },
    "TC-4": {
        "title": "Auto Punctuation Feature",
        "file_name": "stt_comparison_tc4_results.csv",
        "input_desc": "Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 4s to 10s, and clear punctuation syntax (periods, commas, question marks).\nGround truth transcriptions for each clip.",
        "output_desc": "Proportion of correct punctuation placements for each language.",
        "relevant_cols": ["LanguageSubFolder", "SegmentationAccuracy_Percent"],
        "group_by_col": "LanguageSubFolder",
        "metrics_to_process": {"SegmentationAccuracy_Percent": "avg"},
        "report_headers": ["Language", "Average Segmentation Accuracy (%)"]
    },
    "TC-5": {
        "title": "Profanity Filtering",
        "file_name": "stt_comparison_tc5_results.csv",
        "input_desc": "Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 4s to 10s, containing profanity vocabulary.\nGround truth transcriptions for each clip.",
        "output_desc": "Rate of profanity vocabulary identified for each language.",
        "relevant_cols": ["LanguageSubFolder", "VocabularyAccuracy_Percent"],
        "group_by_col": "LanguageSubFolder",
        "metrics_to_process": {"VocabularyAccuracy_Percent": "avg"},
        "report_headers": ["Language", "Average Profanity Identification Rate (%)"]
    },
    "TC-6": {
        "title": "Transcription Speed and Latency",
        "file_name": "stt_comparison_tc6_results.csv",
        "input_desc": "Audio clips of lengths: 5-10 seconds.",
        "output_desc": "Actual latency in seconds vs system-reported latency.",
        "relevant_cols": ["ResponseSpeed_s_from_csv"],
        "group_by_col": None, 
        "metrics_to_process": {"ResponseSpeed_s_from_csv": "avg"},
        "report_headers": ["Metric", "Value"],
        "custom_processing": True
    },
    "TC-7": {
        "title": "Noise Robustness",
        "file_name": "stt_comparison_tc7_results.csv",
        "input_desc": "Voice datasets for each language (English-US, English-UK, English-HK, Cantonese-HK, Mandarin), with length ranging from 5s to 10s, mixed with various environment noise at different SNR levels.",
        "output_desc": "WER (Word Error Rate), WRR (Word Recognition Rate).",
        "relevant_cols": ["LanguageSubFolder", "NoiseLevel_Percent", "WER", "WRR_Percent"],
        "group_by_col": ["LanguageSubFolder", "NoiseLevel_Percent"],
        "metrics_to_process": {"WER": "avg", "WRR_Percent": "avg"},
        "report_headers": ["Language/Condition", "Noise Level (%)", "Average WER (%)", "Average WRR (%)"]
    }
}


def safe_float(value, default=None):
    """Converts a value to float, returning default if conversion fails."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def generate_markdown_table(headers, rows_data):
    """Generates a Markdown table from headers and rows of data."""
    if not rows_data:
        return "No data available to display for this section.\n"
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_lines = []
    for row in rows_data:
        data_lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join([header_line, separator_line] + data_lines) + "\n"

def read_csv_data(file_path):
    """Reads data from a CSV file into a list of dictionaries."""
    if not os.path.exists(file_path):
        print(f"Warning: File not found at {file_path}")
        return []
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            return list(reader)
    except Exception as e:
        print(f"Error reading CSV file {file_path}: {e}")
        return []


def process_tc_data_grouped_by_stt(tc_id, all_rows_data, config):
    """
    Processes data for a specific test case, grouped by STT_Method, 
    and returns a Markdown string for the results section.
    """
    stt_methods_in_data = set()
    for row in all_rows_data:
        if 'STT_Method' in row and row['STT_Method']:
            stt_methods_in_data.add(row['STT_Method'])
    
    if not stt_methods_in_data:
        return "No STT_Method found in data or data is empty.\n"
    
    sorted_stt_methods = sorted(list(stt_methods_in_data))

    tc_results_md = ""

    for stt_method in sorted_stt_methods:
        tc_results_md += f"\n#### STT Method: {stt_method}\n\n"
        
        stt_specific_data = [row for row in all_rows_data if row.get('STT_Method') == stt_method]

        if not stt_specific_data:
            tc_results_md += "No data for this STT method.\n"
            continue

        if config.get("custom_processing") and tc_id == "TC-6":
            speeds = [safe_float(row.get("ResponseSpeed_s_from_csv")) for row in stt_specific_data]
            valid_speeds = [s for s in speeds if s is not None]
            avg_speed = statistics.mean(valid_speeds) if valid_speeds else "N/A"
            
            table_rows = [
                ["Average Actual Latency (s)", f"{avg_speed:.3f}" if isinstance(avg_speed, float) else avg_speed],
                ["System-Reported Latency (s)", "Data not available in source CSV"]
            ]
            summary_table_md = generate_markdown_table(config["report_headers"], table_rows)
            tc_results_md += summary_table_md + "\n"
            continue

        grouped_data_for_stt = defaultdict(lambda: {metric: [] for metric in config["metrics_to_process"]})
        
        for row in stt_specific_data:
            group_key_parts = []
            current_secondary_group_key = "Overall"

            if config["group_by_col"]:
                if isinstance(config["group_by_col"], list):
                    for col_name in config["group_by_col"]:
                        group_key_parts.append(row.get(col_name, "Unknown"))
                    current_secondary_group_key = tuple(group_key_parts)
                else:
                    current_secondary_group_key = row.get(config["group_by_col"], "Unknown")
            
            for metric_name in config["metrics_to_process"]:
                raw_value = row.get(metric_name)
                value = safe_float(raw_value)
                if value is not None:
                    grouped_data_for_stt[current_secondary_group_key][metric_name].append(value)

        if not grouped_data_for_stt:
            tc_results_md += "No valid data to aggregate for this STT method after filtering.\n"
            continue

        table_rows_for_stt = []
        
        try:
            sorted_secondary_group_keys = sorted(grouped_data_for_stt.keys(), key=lambda k: str(k))
        except TypeError:
            sorted_secondary_group_keys = list(grouped_data_for_stt.keys())

        for sec_key in sorted_secondary_group_keys:
            output_row_for_stt = []
            if isinstance(sec_key, tuple):
                output_row_for_stt.extend(list(sec_key))
            else:
                output_row_for_stt.append(sec_key)
            
            for metric_name, operation in config["metrics_to_process"].items():
                values = grouped_data_for_stt[sec_key][metric_name]
                if not values:
                    result = "N/A"
                elif operation == "avg":
                    agg_result = statistics.mean(values)
                    result = f"{agg_result:.2f}"
                else: 
                    result = "Unsupported Op" 
                output_row_for_stt.append(result)
            table_rows_for_stt.append(output_row_for_stt)
            
        if not table_rows_for_stt:
             tc_results_md += "No data rows generated for this STT method's table.\n"
        else:
            summary_table_md = generate_markdown_table(config["report_headers"], table_rows_for_stt)
            tc_results_md += summary_table_md + "\n"
            
    return tc_results_md


def generate_report():
    """Generates the full Markdown report and writes it to a file."""
    all_markdown_parts = ["# STT System Evaluation Summary Report\n"]

    sorted_tc_ids = sorted(TEST_CASE_CONFIG.keys())

    for tc_id in sorted_tc_ids:
        config = TEST_CASE_CONFIG[tc_id]
        print(f"Processing {tc_id}: {config['title']}...")
        
        markdown_part = f"\n## {tc_id}: {config['title']}\n\n"
        markdown_part += f"### Input:\n\n{config['input_desc']}\n\n\n"
        markdown_part += f"### Output Requirement:\n\n{config['output_desc']}\n\n\n"
        markdown_part += f"### Results:\n"

        file_path = os.path.join(BASE_PATH, config["file_name"])
        raw_data_from_csv = read_csv_data(file_path)

        if not raw_data_from_csv:
            markdown_part += "Could not read data or file is empty.\n\n"
        else:
            results_markdown_for_tc = process_tc_data_grouped_by_stt(tc_id, raw_data_from_csv, config)
            markdown_part += results_markdown_for_tc
            
        all_markdown_parts.append(markdown_part)

    final_report_content = "".join(all_markdown_parts)
    
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(final_report_content)
        print(f"\nReport successfully generated: {OUTPUT_FILE}")
    except IOError as e:
        print(f"Error writing report to file {OUTPUT_FILE}: {e}")

if __name__ == "__main__":
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)
        print(f"Created directory {BASE_PATH} as it did not exist.")

    generate_report()
