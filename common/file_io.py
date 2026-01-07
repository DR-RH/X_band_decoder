import pickle
import shutil
import os
import datetime
from common import decode_utils
import csv

def save_loss_packet_group(packet_loss_group,):
    os.makedirs('data/loss_packet_group',exist_ok=True)
    with open('data/loss_packet_group/loss_packet_group.pkl', 'wb') as f:
        pickle.dump(packet_loss_group, f)
    return

def load_loss_packet_group():
    path = 'data/loss_packet_group/loss_packet_group.pkl'
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return pickle.load(f)
    
def save_packet_group_file(data, file_uid, extension, output_dir='./output/X_band_decoded'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = f'{output_dir}/decoded_{file_created_time}_{timestamp}.{extension}'
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved {extension} file for UID {file_uid} as: {filename}")
    return filename

def move_files(file_paths):
    print(f"move files {file_paths}" )
    for file in file_paths:
        filename = file.split('/')[-1]
        dst_filename = f'data/raw_data_processed/{filename}'
        shutil.move(file, dst_filename)
    return

def write_loss_report(report_path, file_uid, extension, loss_sequence):
    ranges = decode_utils.get_ranges(loss_sequence)
    with open(report_path, mode='a') as f:
        writer = csv.writer(f)
        for rng in ranges:
            writer.writerow([file_uid,extension]+list(rng))

def create_loss_report_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs('output/report', exist_ok=True)
    report_path = f'output/report/{timestamp}.csv'
    with open(report_path, mode='w') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "extension", "start", "end", "number"])
    return report_path
