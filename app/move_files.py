import shutil
def move_files(file_paths):
    print(f"move files {file_paths}" )
    for file in file_paths:
        filename = file.split('/')[-1]
        dst_filename = f'data/raw_data_processed/{filename}'
        shutil.move(file, dst_filename)
    return