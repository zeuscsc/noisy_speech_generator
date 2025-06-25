import os
from pydub import AudioSegment
import glob
import multiprocessing
from functools import partial
import time
import traceback
from tqdm import tqdm

def vtt_time_to_ms(vtt_time_str):
    parts = vtt_time_str.split(':')
    h, m, s_ms_val = 0, 0, ""

    if len(parts) == 3:
        h, m, s_ms_val = parts
    elif len(parts) == 2:
        h = 0
        m, s_ms_val = parts
    elif len(parts) == 1 and '.' in parts[0]:
        h = 0
        m = 0
        s_ms_val = parts[0]
    else:
        raise ValueError(f"Invalid VTT time format: {vtt_time_str}")

    s_ms_parts = s_ms_val.split('.')
    s = int(s_ms_parts[0])
    ms_str = s_ms_parts[1] if len(s_ms_parts) > 1 else "0"
    ms = int(ms_str.ljust(3, '0')[:3])

    return (int(h) * 3600 + int(m) * 60 + s) * 1000 + ms

def ms_to_vtt_time(ms_time):
    if ms_time < 0:
        ms_time = 0
    seconds_total = ms_time // 1000
    milliseconds = ms_time % 1000
    minutes_total = seconds_total // 60
    seconds = seconds_total % 60
    hours = minutes_total // 60
    minutes = minutes_total % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(milliseconds):03d}"

def parse_vtt_content(vtt_content_str):
    lines = vtt_content_str.strip().splitlines()
    cues = []
    idx = 0

    while idx < len(lines):
        line_strip = lines[idx].strip()
        if "-->" in line_strip or line_strip == "":
            break
        idx += 1
    
    current_cue_lines = []
    while idx < len(lines):
        line = lines[idx] 
        
        if not line.strip(): 
            if current_cue_lines:
                time_line_str = None
                text_start_idx_in_cue = -1

                if "-->" in current_cue_lines[0]:
                    time_line_str = current_cue_lines[0]
                    text_start_idx_in_cue = 1
                elif len(current_cue_lines) > 1 and "-->" in current_cue_lines[1]:
                    time_line_str = current_cue_lines[1]
                    text_start_idx_in_cue = 2
                
                if time_line_str:
                    try:
                        text_content_actual_lines = [l.strip() for l in current_cue_lines[text_start_idx_in_cue:]]
                        start_str, end_str_full = time_line_str.strip().split("-->")
                        end_str_cleaned = end_str_full.strip().split(' ')[0]
                        start_ms = vtt_time_to_ms(start_str.strip())
                        end_ms = vtt_time_to_ms(end_str_cleaned)
                        
                        cues.append({
                            "start_ms": start_ms,
                            "end_ms": end_ms,
                            "text_lines": [l for l in text_content_actual_lines if l],
                            "raw_cue_lines": list(current_cue_lines) 
                        })
                    except (ValueError, IndexError):
                        pass 
                current_cue_lines = [] 
            idx += 1
            continue 
        
        current_cue_lines.append(line) 
        idx += 1

    if current_cue_lines:
        time_line_str = None
        text_start_idx_in_cue = -1
        if "-->" in current_cue_lines[0]:
            time_line_str = current_cue_lines[0]
            text_start_idx_in_cue = 1
        elif len(current_cue_lines) > 1 and "-->" in current_cue_lines[1]:
            time_line_str = current_cue_lines[1]
            text_start_idx_in_cue = 2
        
        if time_line_str:
            try:
                text_content_actual_lines = [l.strip() for l in current_cue_lines[text_start_idx_in_cue:]]
                start_str, end_str_full = time_line_str.strip().split("-->")
                end_str_cleaned = end_str_full.strip().split(' ')[0]
                start_ms = vtt_time_to_ms(start_str.strip())
                end_ms = vtt_time_to_ms(end_str_cleaned)
                cues.append({
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text_lines": [l for l in text_content_actual_lines if l],
                    "raw_cue_lines": list(current_cue_lines)
                })
            except (ValueError, IndexError):
                pass
            
    return cues

def generate_relative_vtt_from_cues(cues_in_segment, segment_absolute_start_ms):
    vtt_parts = ["WEBVTT", ""]
    if not cues_in_segment:
        return None

    for cue in cues_in_segment:
        relative_start_ms = cue["start_ms"] - segment_absolute_start_ms
        relative_end_ms = cue["end_ms"] - segment_absolute_start_ms
        relative_start_ms = max(0, relative_start_ms)
        relative_end_ms = max(relative_start_ms, relative_end_ms)

        new_start_vtt = ms_to_vtt_time(relative_start_ms)
        new_end_vtt = ms_to_vtt_time(relative_end_ms)

        styling_suffix = ""
        if cue.get("raw_cue_lines"):
            original_time_line = ""
            for raw_line in cue["raw_cue_lines"]:
                if "-->" in raw_line:
                    original_time_line = raw_line
                    break
            if original_time_line:
                try:
                    _, original_end_str_full = original_time_line.split("-->")
                    original_end_parts = original_end_str_full.strip().split(' ', 1)
                    if len(original_end_parts) > 1:
                        styling_suffix = " " + original_end_parts[1]
                except ValueError:
                    styling_suffix = ""
        
        time_header = f"{new_start_vtt} --> {new_end_vtt}{styling_suffix}"
        vtt_parts.append(time_header)
        
        cleaned_text_lines = cue.get("text_lines", [])
        if not cleaned_text_lines and cue.get("raw_cue_lines"):
            cue_id_lines = 0
            time_line_index_in_raw = -1
            if "-->" in cue["raw_cue_lines"][0]:
                time_line_index_in_raw = 0
            elif len(cue["raw_cue_lines"]) > 1 and "-->" in cue["raw_cue_lines"][1]:
                 time_line_index_in_raw = 1
            
            if time_line_index_in_raw != -1:
                text_portion_raw = cue["raw_cue_lines"][time_line_index_in_raw+1:]
                if text_portion_raw and all(not line.strip() for line in text_portion_raw):
                    for _ in text_portion_raw:
                        vtt_parts.append("")
                else:
                    vtt_parts.extend(cleaned_text_lines)
            else:
                vtt_parts.extend(cleaned_text_lines)
        else:
            vtt_parts.extend(cleaned_text_lines)
        vtt_parts.append("")

    if len(vtt_parts) > 2:
        return "\n".join(vtt_parts)
    return None

def process_single_audio_and_transcript_file(audio_file_path, output_base_dir, target_chunk_durations_s, base_input_transcript_dir):
    pid = os.getpid()
    processed_audio_chunks_count = 0
    created_transcript_chunks_count = 0
    youtube_video_id = "unknown_video_id"

    try:
        audio_filename = os.path.basename(audio_file_path)
        noisy_level_folder_name = os.path.splitext(audio_filename)[0]
        youtube_video_id = os.path.basename(os.path.dirname(audio_file_path))

        if not youtube_video_id or not noisy_level_folder_name:
            print(f"[PID {pid}] Could not determine video ID or noisy level for {audio_file_path}. Skipping.")
            return None, 0, 0

        all_parsed_vtt_data = [] 
        vtt_files_to_actually_parse = [] 

        transcript_dir_for_video_id = os.path.join(base_input_transcript_dir, youtube_video_id)
        if os.path.isdir(transcript_dir_for_video_id):
            all_available_vtt_filenames = sorted([
                fn for fn in os.listdir(transcript_dir_for_video_id)
                if fn.endswith(".vtt") and not fn.startswith(f"{noisy_level_folder_name}_audio_")
            ])

            gt_vtt_files = [fn for fn in all_available_vtt_filenames if fn.endswith(".gt.vtt")]

            if gt_vtt_files:
                selected_gt_vtt = gt_vtt_files[0]
                vtt_files_to_actually_parse.append(selected_gt_vtt)
                if len(gt_vtt_files) > 1:
                    print(f"[PID {pid}] WARNING: Multiple '.gt.vtt' files found for {audio_file_path}. Using only the first: {selected_gt_vtt}. Others: {gt_vtt_files[1:]}")
            elif all_available_vtt_filenames:
                vtt_files_to_actually_parse.extend(all_available_vtt_filenames)
                print(f"[PID {pid}] INFO: No '.gt.vtt' file found for {audio_file_path}. Processing other available VTTs: {vtt_files_to_actually_parse}")

            for vtt_filename in vtt_files_to_actually_parse:
                original_transcript_path = os.path.join(transcript_dir_for_video_id, vtt_filename)
                try:
                    with open(original_transcript_path, 'r', encoding='utf-8') as f:
                        vtt_content_str = f.read()
                    cues = parse_vtt_content(vtt_content_str)
                    if cues: 
                        cues.sort(key=lambda c: c["start_ms"])
                        vtt_basename = os.path.splitext(vtt_filename)[0]
                        all_parsed_vtt_data.append((vtt_basename, cues))
                except Exception as e:
                    print(f"[PID {pid}] Error reading/parsing VTT {original_transcript_path}: {e}")
        
        if not all_parsed_vtt_data:
            print(f"[PID {pid}] No usable VTT data for {audio_file_path} after selection/parsing. Skipping VTT-based processing.")
            return youtube_video_id, 0, 0

        try:
            audio = AudioSegment.from_mp3(audio_file_path)
        except Exception as e:
            print(f"[PID {pid}] Error loading audio {audio_file_path}: {e}. Skipping.")
            return youtube_video_id, 0, 0

        for vtt_basename, original_cues in all_parsed_vtt_data:
            for target_s in target_chunk_durations_s:
                target_ms = target_s * 1000
                chunk_size_specific_dir = os.path.join(output_base_dir, youtube_video_id, f"chunk_{target_s}s")
                noisy_level_specific_chunk_output_dir = os.path.join(chunk_size_specific_dir, noisy_level_folder_name)
                os.makedirs(noisy_level_specific_chunk_output_dir, exist_ok=True)

                current_global_cue_idx = 0
                chunk_num = 0
                
                while current_global_cue_idx < len(original_cues):
                    cues_for_this_chunk = []
                    chunk_intended_start_ms_abs = original_cues[current_global_cue_idx]["start_ms"]
                    
                    temp_cue_collector_idx = current_global_cue_idx
                    while temp_cue_collector_idx < len(original_cues):
                        cue_to_consider = original_cues[temp_cue_collector_idx]
                        potential_duration_if_added = cue_to_consider["end_ms"] - chunk_intended_start_ms_abs

                        if not cues_for_this_chunk:
                            cues_for_this_chunk.append(cue_to_consider)
                            temp_cue_collector_idx += 1
                        elif potential_duration_if_added <= target_ms * 1.5:
                            cues_for_this_chunk.append(cue_to_consider)
                            temp_cue_collector_idx += 1
                            if potential_duration_if_added >= target_ms:
                                break
                        else:
                            break 
                    
                    if not cues_for_this_chunk:
                        break 

                    chunk_actual_start_ms = cues_for_this_chunk[0]["start_ms"]
                    chunk_actual_end_ms = cues_for_this_chunk[-1]["end_ms"]

                    if chunk_actual_start_ms > chunk_actual_end_ms: 
                        print(f"[PID {pid}] WARNING: Audio segment start_ms ({chunk_actual_start_ms}) > end_ms ({chunk_actual_end_ms}) for {vtt_basename}_audio_{chunk_num} in {audio_file_path}. Skipping segment.")
                        current_global_cue_idx = temp_cue_collector_idx 
                        continue
                    
                    try:
                        audio_segment = audio[chunk_actual_start_ms:chunk_actual_end_ms]
                    except Exception as e:
                        print(f"[PID {pid}] Error slicing audio for {vtt_basename}_audio_{chunk_num} ({chunk_actual_start_ms}:{chunk_actual_end_ms}) in {audio_file_path}: {e}. Skipping segment.")
                        current_global_cue_idx = temp_cue_collector_idx
                        continue

                    audio_chunk_filename = f"{vtt_basename}_audio_{chunk_num}.mp3"
                    audio_chunk_filepath = os.path.join(noisy_level_specific_chunk_output_dir, audio_chunk_filename)

                    if not os.path.exists(audio_chunk_filepath) or os.path.getsize(audio_chunk_filepath) == 0:
                        try:
                            audio_segment.export(audio_chunk_filepath, format="mp3")
                            processed_audio_chunks_count += 1
                        except Exception as e:
                            print(f"[PID {pid}] Error saving audio chunk {audio_chunk_filepath}: {e}")
                    
                    vtt_chunk_str = generate_relative_vtt_from_cues(cues_for_this_chunk, chunk_actual_start_ms)
                    if vtt_chunk_str:
                        transcript_chunk_filename = f"{vtt_basename}_audio_{chunk_num}.vtt"
                        transcript_chunk_filepath = os.path.join(noisy_level_specific_chunk_output_dir, transcript_chunk_filename)
                        if not os.path.exists(transcript_chunk_filepath) or True:
                            try:
                                with open(transcript_chunk_filepath, 'w', encoding='utf-8') as f_out:
                                    f_out.write(vtt_chunk_str)
                                created_transcript_chunks_count += 1
                            except Exception as e:
                                print(f"[PID {pid}] Error writing VTT chunk {transcript_chunk_filepath}: {e}")
                    
                    chunk_num += 1
                    current_global_cue_idx = temp_cue_collector_idx

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"[PID {pid}] MAJOR UNHANDLED error in process_single_audio_and_transcript_file for {audio_file_path}: {e}\nTraceback:\n{tb_str}")
        if audio_file_path and os.path.dirname(audio_file_path): 
             youtube_video_id_fallback = os.path.basename(os.path.dirname(audio_file_path))
             return youtube_video_id_fallback, processed_audio_chunks_count, created_transcript_chunks_count
        return "unknown_video_id_due_to_error", processed_audio_chunks_count, created_transcript_chunks_count
    
    return youtube_video_id, processed_audio_chunks_count, created_transcript_chunks_count

def create_chunked_dataset_parallel(base_input_audio_dir, base_input_transcript_dir, output_base_dir, num_processes=None):
    start_time = time.time()

    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir, exist_ok=True)
        print(f"Created base output directory: {output_base_dir}")

    # target_chunk_durations_s = [8, 30, 60]
    target_chunk_durations_s = [6000]

    audio_files = glob.glob(os.path.join(base_input_audio_dir, "*", "*.mp3"))
    if not audio_files:
        print(f"No MP3 files found in subdirectories of {base_input_audio_dir}. Example structure: {base_input_audio_dir}/<video_id>/<audio_file.mp3>. Exiting.")
        return

    print(f"Found {len(audio_files)} audio files to potentially process.")

    actual_num_processes = num_processes if num_processes is not None else os.cpu_count()
    print(f"\n--- Starting Parallel Audio and Transcript Chunking (using up to {actual_num_processes} processes) ---")

    worker_func = partial(process_single_audio_and_transcript_file,
                          output_base_dir=output_base_dir,
                          target_chunk_durations_s=target_chunk_durations_s,
                          base_input_transcript_dir=base_input_transcript_dir)

    processed_video_ids = set()
    total_audio_chunks_overall = 0 
    total_transcript_chunks_overall = 0 
    results = [] 

    with multiprocessing.Pool(processes=actual_num_processes) as pool:
        with tqdm(total=len(audio_files), desc="Processing audio files") as pbar:
            for result in pool.imap_unordered(worker_func, audio_files):
                results.append(result)
                pbar.update()

    files_where_audio_chunks_were_made = 0
    files_where_transcript_chunks_were_made = 0

    for res in results: 
        if res is None: 
            print("Warning: Worker function returned None for a file processing attempt.")
            continue
        video_id_result, audio_count_for_file, transcript_count_for_file = res
        
        if video_id_result and "unknown_video_id" not in video_id_result: 
            processed_video_ids.add(video_id_result)
        if audio_count_for_file > 0:
            files_where_audio_chunks_were_made += 1
        if transcript_count_for_file > 0:
            files_where_transcript_chunks_were_made += 1
        total_audio_chunks_overall += audio_count_for_file
        total_transcript_chunks_overall += transcript_count_for_file
            
    print(f"--- Finished Audio and Transcript Chunking Phase ---")
    print(f"Checked/Processed {len(audio_files)} source audio files corresponding to {len(processed_video_ids)} unique video IDs.")
    print(f"Audio chunking operations were performed for {files_where_audio_chunks_were_made} source audio files (across all target durations).")
    print(f"Total individual audio chunks saved (new or overwritten): {total_audio_chunks_overall}.")
    print(f"Transcript chunking operations were performed for {files_where_transcript_chunks_were_made} source audio files (across all target durations).")
    print(f"Total individual transcript chunks created (new or overwritten): {total_transcript_chunks_overall}.")
    
    end_time = time.time()
    print(f"\n--- Total Processing Complete in {end_time - start_time:.2f} seconds ---")

def pipeline():
    multiprocessing.freeze_support() 

    current_working_directory = os.getcwd()
    input_audio_directory = os.path.join(current_working_directory, "output_noisy_audio")
    input_transcript_directory = os.path.join(current_working_directory, "dataset") 
    output_chunked_directory = os.path.join(current_working_directory, "chunked_dataset") 

    NUM_PROCESSES = None

    print(f"Starting dataset processing at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input Audio Directory: {input_audio_directory}")
    print(f"Input Transcript Directory: {input_transcript_directory}")
    print(f"Output Chunked Directory: {output_chunked_directory}")

    if not os.path.isdir(input_audio_directory):
        print(f"ERROR: Input audio directory not found: {input_audio_directory}")
        return 
    if not os.path.isdir(input_transcript_directory):
        print(f"ERROR: Base input transcript directory not found: {input_transcript_directory}. Transcript chunking cannot proceed without transcripts.")
        return

    create_chunked_dataset_parallel(
        input_audio_directory,
        input_transcript_directory,
        output_chunked_directory,
        num_processes=NUM_PROCESSES
    )

if __name__ == "__main__":
    pipeline()