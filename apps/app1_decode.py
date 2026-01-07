import glob
from common import decode_utils 
from common import constants as C 
import datetime
import os 
import csv
import pickle
import shutil

"""
トータルパケットを追加する
保存にタイプを記載する
"""

def save_packet_group_file(data, file_uid, extension, output_dir='./output/X_band_decoded'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = f'{output_dir}/decoded_{file_created_time}_{timestamp}.{extension}'
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved {extension} file for UID {file_uid} as: {filename}")

    print(f"decoded :{filename}")
    return filename
    return

def move_files(files):
    print(f"move file {files}" )
    for file in files:
        filename = file.split('/')[-1]
        dst_filename = f'data/raw_data_processed/{filename}'
        shutil.move(file, dst_filename)
    return

def initialize_report_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs('output/report',exist_ok=True)
    path_w = f'output/report/{timestamp}.csv'
    with open(path_w, mode='w') as f:
        writer = csv.writer(f)
        writer.writerow(["ID","start","end","number"])
    return path_w

def save_loss_packtet_group(packet_loss_group,):
    os.makedirs('data/loss_packet_group',exist_ok=True)
    with open('data/loss_packet_group/loss_packet_group.pkl', 'wb') as f:
        pickle.dump(packet_loss_group, f)
    return

def load__loss_packtet_group():

    path = 'data/loss_packet_group/loss_packet_group.pkl'
    if not os.path.exists(path):
        return {}
    with open(path, 'rb') as f:
        return pickle.load(f)
    

def reassemble_packet_group(packet_group, extension):
    packet_data = packet_group['packets']
    combined_packet = b"".join(packet_data)

    if extension == 'bin':
        reassembled_data = combined_packet[:3003*3008*2] # end data handling
    else:
        reassembled_data = bytes(combined_packet).rstrip(b'\0')

    return reassembled_data

def check_extension(ptype):
    if ptype == 0x03:
        extension = 'txt'
    elif ptype == 0x04:
        extension = 'log'
    elif ptype == 0x01:
        extension = 'csv'
    elif ptype == 0x05:
        extension = 'jpg'
    else:
        extension = 'bin'
    return extension

def main(target_files):

    packet_groups = load__loss_packtet_group()
    # packet_group =  read_packet_group()
    for target_file in target_files:
        print(f"Decoding file: {target_file}")
        packet_groups = decode_utils.decode_packets(target_file, packet_groups)

    packet_loss_group = {} 
    for k, v in packet_groups.items():
        id = k
        packet_group = v
        packets = packet_group['packets']
        ptype = packet_group['ptypes'][0]
        extension = check_extension(ptype)

        print(f'ID is {id}')
        loss_sequence = []
        for i, packet in enumerate(packets):
            if packet == bytes([0xEE])*C.PAYLOAD_SIZE:
                print(f'find packet loss @ {i}')
                loss_sequence.append(i)
        path_w = initialize_report_file()
        if not loss_sequence:
            reassembled_data = reassemble_packet_group(packet_group, extension)
            save_packet_group_file(reassembled_data, id, extension)
        else:
            print('loss packet found ')
            ranges = decode_utils.get_ranges(loss_sequence)
            with open(path_w, mode='a') as f:
                writer = csv.writer(f)
                for range in ranges:
                    writer.writerow([id]+list(range))
            packet_loss_group[k] = v

    save_loss_packtet_group(packet_loss_group)




    move_files(target_files)

    return 



if __name__ == "__main__":
    # target_files = glob.glob('x_band_test_data/four_images_F20250515170302*')
    # target_files = glob.glob('x_band_test_data/x_band_test_data/four_images_F20250515170302.bin')
    # target_files = glob.glob('x_band_test_data/part*.bin')
  
    files = glob.glob("data/raw_data_unprocessed"
    "/*.bin")
    target_files = [f for f in files if "packet_base" not in f]

    # target_files = glob.glob("data/x_divided_bin/*packet_base*.bin")
    target_files.sort(reverse=False)
    target_files = target_files
    # target_files = target_files[:6]
    main(target_files)
