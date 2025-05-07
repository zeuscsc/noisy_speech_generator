import os
from pydub import AudioSegment
import glob
import multiprocessing
from functools import partial
import time

def vtt_time_to_ms(vtt_time_str):
    parts = vtt_time_str.split(':')
    if len(parts) == 3:
        h, m, s_ms = parts
    elif len(parts) == 2:
        h = 0
        m, s_ms = parts
    elif len(parts) == 1 and '.' in vtt_time_str:
        h = 0
        m = 0
        s_ms = parts[0]
    else:
        raise ValueError(f"Invalid VTT time format: {vtt_time_str}")

    s_ms_parts = s_ms.split('.')
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
        line = lines[idx].strip()
        
        if not line:
            if current_cue_lines:
                time_line_str = None
                time_line_idx_in_cue = -1
                text_start_idx_in_cue = -1

                if "-->" in current_cue_lines[0]:
                    time_line_str = current_cue_lines[0]
                    time_line_idx_in_cue = 0
                    text_start_idx_in_cue = 1
                elif len(current_cue_lines) > 1 and "-->" in current_cue_lines[1]:
                    time_line_str = current_cue_lines[1]
                    time_line_idx_in_cue = 1
                    text_start_idx_in_cue = 2
                
                if time_line_str:
                    try:
                        text_content_lines = current_cue_lines[text_start_idx_in_cue:]
                        start_str, end_str_full = time_line_str.split("-->")
                        end_str_cleaned = end_str_full.strip().split(' ')[0]

                        start_ms = vtt_time_to_ms(start_str.strip())
                        end_ms = vtt_time_to_ms(end_str_cleaned)
                        
                        cues.append({
                            "start_ms": start_ms,
                            "end_ms": end_ms,
                            "text_lines": [l for l in text_content_lines if l.strip()],
                            "raw_cue_lines": list(current_cue_lines)
                        })
                    except ValueError:
                        pass
                    except IndexError:
                        pass
                current_cue_lines = []
            idx += 1
            continue
        
        current_cue_lines.append(lines[idx])
        idx += 1

    if current_cue_lines:
        time_line_str = None
        time_line_idx_in_cue = -1
        text_start_idx_in_cue = -1

        if "-->" in current_cue_lines[0]:
            time_line_str = current_cue_lines[0]
            time_line_idx_in_cue = 0
            text_start_idx_in_cue = 1
        elif len(current_cue_lines) > 1 and "-->" in current_cue_lines[1]:
            time_line_str = current_cue_lines[1]
            time_line_idx_in_cue = 1
            text_start_idx_in_cue = 2

        if time_line_str:
            try:
                text_content_lines = current_cue_lines[text_start_idx_in_cue:]
                start_str, end_str_full = time_line_str.split("-->")
                end_str_cleaned = end_str_full.strip().split(' ')[0]
                start_ms = vtt_time_to_ms(start_str.strip())
                end_ms = vtt_time_to_ms(end_str_cleaned)
                cues.append({
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "text_lines": [l for l in text_content_lines if l.strip()],
                    "raw_cue_lines": list(current_cue_lines)
                })
            except ValueError:
                pass
            except IndexError:
                pass
            
    return cues

def create_vtt_chunk_from_cues(all_cues, chunk_start_ms, chunk_end_ms):
    chunk_vtt_parts = ["WEBVTT", ""]
    found_entry_in_chunk = False

    for cue in all_cues:
        if cue["start_ms"] < chunk_end_ms and cue["end_ms"] > chunk_start_ms:
            original_time_line = ""
            if cue.get("raw_cue_lines"):
                for raw_line in cue["raw_cue_lines"]:
                    if "-->" in raw_line:
                        original_time_line = raw_line
                        break
            
            if not original_time_line:
                time_header = f"{ms_to_vtt_time(cue['start_ms'])} --> {ms_to_vtt_time(cue['end_ms'])}"
            else:
                try:
                    parsed_start_vtt = ms_to_vtt_time(cue['start_ms'])
                    parsed_end_vtt = ms_to_vtt_time(cue['end_ms'])
                    
                    original_start_str, original_end_str_full = original_time_line.split("-->")
                    original_end_parts = original_end_str_full.strip().split(' ', 1)
                    
                    styling_suffix = ""
                    if len(original_end_parts) > 1:
                        styling_suffix = " " + original_end_parts[1]
                    
                    time_header = f"{parsed_start_vtt} --> {parsed_end_vtt}{styling_suffix}"

                except Exception:
                    time_header = f"{ms_to_vtt_time(cue['start_ms'])} --> {ms_to_vtt_time(cue['end_ms'])}"

            chunk_vtt_parts.append(time_header)
            cleaned_text_lines = [text_line for text_line in cue["text_lines"] if text_line.strip()]
            if not cleaned_text_lines and cue["text_lines"]:
                chunk_vtt_parts.append("")
            else:
                chunk_vtt_parts.extend(cleaned_text_lines)
            chunk_vtt_parts.append("")
            found_entry_in_chunk = True

    if not found_entry_in_chunk:
        return None
    
    if len(chunk_vtt_parts) > 2 and chunk_vtt_parts[-1] == "": 
        return "\n".join(chunk_vtt_parts)
    elif len(chunk_vtt_parts) > 2 :
        return "\n".join(chunk_vtt_parts) + "\n" 
    
    return None

def process_single_audio_and_transcript_file(audio_file_path, output_base_dir, chunk_sizes_seconds, base_input_transcript_dir):
    pid = os.getpid()
    processed_audio_chunks_count = 0
    created_transcript_chunks_count = 0
    
    try:
        audio_filename = os.path.basename(audio_file_path)
        noisy_level_folder_name = os.path.splitext(audio_filename)[0] 
        youtube_video_id = os.path.basename(os.path.dirname(audio_file_path))

        if not youtube_video_id:
            return None, 0, 0 
        if not noisy_level_folder_name:
            return youtube_video_id, 0, 0

        all_parsed_vtt_data = [] 
        transcript_dir_for_video_id = os.path.join(base_input_transcript_dir, youtube_video_id)
        
        if os.path.isdir(transcript_dir_for_video_id):
            vtt_file_names_to_process = [
                fn for fn in sorted(os.listdir(transcript_dir_for_video_id))
                if fn.endswith(".vtt") and not fn.startswith("audio_")
            ]

            for vtt_filename in vtt_file_names_to_process:
                original_transcript_path = os.path.join(transcript_dir_for_video_id, vtt_filename)
                try:
                    with open(original_transcript_path, 'r', encoding='utf-8') as f:
                        vtt_content_str = f.read()
                    cues = parse_vtt_content(vtt_content_str)
                    if cues:
                        vtt_basename = os.path.splitext(vtt_filename)[0]
                        all_parsed_vtt_data.append((vtt_basename, cues))
                except Exception as e:
                    print(f"[PID {pid}] Error reading/parsing transcript {original_transcript_path} for {youtube_video_id}: {e}")
        
        video_id_base_output_dir = os.path.join(output_base_dir, youtube_video_id)
        try:
            audio = AudioSegment.from_mp3(audio_file_path)
        except Exception as e:
            print(f"[PID {pid}] Error loading audio file {audio_file_path}: {e}. Skipping audio and related transcript processing.")
            return youtube_video_id, 0, 0

        for chunk_size_s in chunk_sizes_seconds:
            chunk_size_specific_dir = os.path.join(video_id_base_output_dir, f"chunk_{chunk_size_s}")
            noisy_level_specific_chunk_output_dir = os.path.join(chunk_size_specific_dir, noisy_level_folder_name)
            os.makedirs(noisy_level_specific_chunk_output_dir, exist_ok=True)
            chunk_length_ms = chunk_size_s * 1000
            
            for i, start_ms in enumerate(range(0, len(audio), chunk_length_ms)):
                end_ms = start_ms + chunk_length_ms
                chunk = audio[start_ms:end_ms]
                
                audio_chunk_filename = f"audio_{i}.mp3"
                audio_chunk_filepath = os.path.join(noisy_level_specific_chunk_output_dir, audio_chunk_filename)
                
                if not os.path.exists(audio_chunk_filepath) or os.path.getsize(audio_chunk_filepath) == 0:
                    try:
                        chunk.export(audio_chunk_filepath, format="mp3")
                        processed_audio_chunks_count += 1
                    except Exception as e:
                        print(f"[PID {pid}] Error saving audio chunk {audio_chunk_filepath}: {e}")
                
                if all_parsed_vtt_data: 
                    for vtt_basename, original_vtt_cues in all_parsed_vtt_data:
                        transcript_chunk_filename = f"{vtt_basename}_audio_{i}.vtt" 
                        transcript_chunk_filepath = os.path.join(noisy_level_specific_chunk_output_dir, transcript_chunk_filename)

                        if not os.path.exists(transcript_chunk_filepath):
                            chunk_vtt_str = create_vtt_chunk_from_cues(original_vtt_cues, start_ms, end_ms)
                            if chunk_vtt_str:
                                try:
                                    with open(transcript_chunk_filepath, 'w', encoding='utf-8') as f_chunk:
                                        f_chunk.write(chunk_vtt_str)
                                    created_transcript_chunks_count += 1
                                except Exception as e:
                                    print(f"[PID {pid}] Error writing transcript chunk {transcript_chunk_filepath}: {e}")
                                    
        return youtube_video_id, processed_audio_chunks_count, created_transcript_chunks_count

    except Exception as e:
        print(f"[PID {os.getpid()}] Unhandled error processing {audio_file_path} (or its transcript): {e}")
        try:
            return os.path.basename(os.path.dirname(audio_file_path)), processed_audio_chunks_count, created_transcript_chunks_count
        except: 
            return None, processed_audio_chunks_count, created_transcript_chunks_count

def create_chunked_dataset_parallel(base_input_audio_dir, base_input_transcript_dir, output_base_dir, num_processes=None):
    start_time = time.time()

    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir, exist_ok=True)
        print(f"Created base output directory: {output_base_dir}")

    chunk_sizes_seconds = [8, 30, 60] 

    audio_files = glob.glob(os.path.join(base_input_audio_dir, "*", "*.mp3")) 
    if not audio_files:
        print(f"No MP3 files found in subdirectories of {base_input_audio_dir}. Exiting.")
        return

    print(f"Found {len(audio_files)} audio files to potentially process.")

    actual_num_processes = num_processes or os.cpu_count()
    print(f"\n--- Starting Parallel Audio and Transcript Chunking (using up to {actual_num_processes} processes) ---")
    
    worker_func = partial(process_single_audio_and_transcript_file,
                          output_base_dir=output_base_dir,
                          chunk_sizes_seconds=chunk_sizes_seconds,
                          base_input_transcript_dir=base_input_transcript_dir)

    processed_video_ids = set()
    total_audio_chunks_processed = 0
    total_transcript_chunks_created = 0
    
    with multiprocessing.Pool(processes=actual_num_processes) as pool:
        results = pool.map(worker_func, audio_files)

    files_where_audio_chunks_were_made = 0
    files_where_transcript_chunks_were_made = 0

    for video_id_result, audio_chunks_count, transcript_chunks_count in results:
        if video_id_result: 
            processed_video_ids.add(video_id_result)
            if audio_chunks_count > 0:
                files_where_audio_chunks_were_made +=1
            if transcript_chunks_count > 0:
                files_where_transcript_chunks_were_made +=1
            total_audio_chunks_processed += audio_chunks_count
            total_transcript_chunks_created += transcript_chunks_count
            
    print(f"--- Finished Audio and Transcript Chunking Phase ---")
    print(f"Checked/Processed {len(audio_files)} source audio files corresponding to {len(processed_video_ids)} unique video IDs.")
    print(f"Audio chunking operations were performed for {files_where_audio_chunks_were_made} source audio files.")
    print(f"Total individual audio chunks saved (new or overwritten): {total_audio_chunks_processed}.")
    print(f"Transcript chunking operations were performed for {files_where_transcript_chunks_were_made} source audio files.")
    print(f"Total individual transcript chunks created (new or overwritten): {total_transcript_chunks_created}.")
    
    end_time = time.time()
    print(f"\n--- Total Processing Complete in {end_time - start_time:.2f} seconds ---")

def pipeline():
    multiprocessing.freeze_support() 

    NUM_PROCESSES = None 

    print(f"Starting dataset processing at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input Audio Directory: {input_audio_directory}")
    print(f"Input Transcript Directory: {input_transcript_directory}")
    print(f"Output Chunked Directory: {output_chunked_directory}")

    if not os.path.isdir(input_audio_directory):
        print(f"ERROR: Input audio directory not found: {input_audio_directory}")
        exit()
    if not os.path.isdir(input_transcript_directory):
        print(f"WARNING: Base input transcript directory not found: {input_transcript_directory}. Transcript chunking will likely be skipped for most/all files unless video-specific transcript folders exist unexpectedly.")

    create_chunked_dataset_parallel(
        input_audio_directory,
        input_transcript_directory,
        output_chunked_directory,
        num_processes=NUM_PROCESSES
    )

current_working_directory = os.getcwd()
input_audio_directory = os.path.join(current_working_directory, "output_noisy_audio")
input_transcript_directory = os.path.join(current_working_directory, "dataset") 
output_chunked_directory = os.path.join(current_working_directory, "chunked_dataset")

if __name__ == "__main__":
    pipeline()