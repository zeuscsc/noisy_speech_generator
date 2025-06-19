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

if __name__ == "__main__":
    target_directory = "testset"
    check_and_rename_files(target_directory)

