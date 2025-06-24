import os

def check_and_rename_files(root_folder):
    """
    Loops through all files in a directory and its subdirectories.
    If a file has a .vtt extension but is not a valid VTT file,
    it renames it to the specified format.

    For example:
    'file_name_iphone.vtt' -> 'file_name.iphone.txt'
    """
    print(f"Starting scan in directory: {root_folder}\n")

    if not os.path.isdir(root_folder):
        print(f"Error: The directory '{root_folder}' was not found.")
        return

    for subdir, _, files in os.walk(root_folder):
        for filename in files:
            if filename.endswith(".vtt"):
                file_path = os.path.join(subdir, filename)

                is_valid_vtt = False
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline()
                        if first_line.strip().startswith("WEBVTT"):
                            is_valid_vtt = True
                except Exception as e:
                    print(f"Could not read file {file_path}. Error: {e}")
                    continue

                if not is_valid_vtt:
                    print(f"Found invalid VTT file: {filename}")

                    base_name = filename[:-4]

                    parts = base_name.rsplit('_', 1)
                    if len(parts) == 2:
                        new_base_name = f"{parts[0]}.{parts[1]}"
                        
                        new_filename = new_base_name + ".txt"
                        
                        old_file_path = os.path.join(subdir, filename)
                        new_file_path = os.path.join(subdir, new_filename)

                        try:
                            os.rename(old_file_path, new_file_path)
                            print(f"  -> Renamed to: {new_filename}\n")
                        except OSError as e:
                            print(f"  -> Error renaming file: {e}\n")
                    else:
                        print(f"  -> Could not find a '_' to replace in {filename}. Skipping rename.\n")

    print("Script finished.")

def rename_files_in_folder(root_folder):
    """
    Recursively walks through a folder and its subfolders to rename specific
    .json and .txt files.

    This function searches for files ending with '.json' or '.txt' that
    contain '.custom.' in their filenames. It then renames these files by
    replacing '.custom.' with '.fano.'.

    Args:
        root_folder (str): The absolute or relative path to the root folder
                           to start the file traversal from.
    """
    if not os.path.isdir(root_folder):
        print(f"Error: The specified folder '{root_folder}' does not exist.")
        return

    print(f"Starting to scan files in: {root_folder}\n")
    renamed_files_count = 0

    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            # Check if the file has a .json or .txt extension and contains '.custom.'
            if (filename.endswith(".json") or filename.endswith(".txt")) and ".custom." in filename:
                original_filepath = os.path.join(dirpath, filename)
                
                # Create the new filename by replacing '.custom.' with '.fano.'
                new_filename = filename.replace(".custom.", ".fano.")
                new_filepath = os.path.join(dirpath, new_filename)

                try:
                    # Rename the file
                    os.rename(original_filepath, new_filepath)
                    print(f"Renamed: {original_filepath}  ->  {new_filepath}")
                    renamed_files_count += 1
                except OSError as e:
                    print(f"Error renaming file {original_filepath}: {e}")

    if renamed_files_count == 0:
        print("No files matching the criteria were found to rename.")
    else:
        print(f"\nFinished renaming {renamed_files_count} file(s).")

if __name__ == "__main__":
    target_directory = "testset"
    check_and_rename_files(target_directory)
    rename_files_in_folder(target_directory)

