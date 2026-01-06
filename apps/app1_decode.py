import glob
from common import decode_utils 
from common import constants as C 
import datetime
import os 
import csv

"""
次回すること
カラム名をつける
"""

def save_packet_group_file():
    return

def move_files(files):
    print(f"move file {files}" )
    return


def main(target_files):

    packet_groups = {}
    # packet_group =  read_packet_group()
    for target_file in target_files:
        print(f"Decoding file: {target_file}")
        packet_groups = decode_utils.decode_packets(target_file, packet_groups)

    for k, v in packet_groups.items():
        id = k
        packets = v['packets']
        print(f'ID is {id}')
        loss_sequence = []
        for i, packet in enumerate(packets):
            if packet == bytes([0xEE])*C.PAYLOAD_SIZE:
                # print(i/)
                print(f'find packet loss @ {i}')
                loss_sequence.append(i)
        print(loss_sequence)
        if loss_sequence:
            print('write')
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            os.makedirs('output/report',exist_ok=True)
            path_w = f'output/report/{timestamp}.csv'
            ranges = decode_utils.get_ranges(loss_sequence)
            print(ranges[0])
            with open(path_w, mode='w') as f:
                # f.write(ranges[0])
                writer = csv.writer(f)
                for range in ranges:
                    writer.writerow([id]+list(range))



    # for file_uid, packet_group in packet_groups.items():
    #     reassembled_data, missing_seq, extension = reassemble_packet_group(packet_group)
    #     total_packet_size = packet_group['total_packet_size']
    #     calculated_file_size = total_packet_size * PAYLOAD_SIZE  # Total file size in bytes based on packet count.

    #     print(f"\nUID: {file_uid} | Type: {extension}")
    #     print(f"Number of Packets (from MDPU header): {total_packet_size}")
    #     print(f"Calculated File Size (from packet count): {calculated_file_size} bytes")

    #     if missing_seq:
    #         ranges = get_ranges(missing_seq)
    #         print("Missing packet sequence numbers (start, end, loss numbers):", (ranges))
    #         print(f"Missing packet numbers: {len(missing_seq)}")
    #         #save_with_missing_seq()
    #     else:
    #         print("No missing packets.")
    #         save_packet_group_file(reassembled_data, file_uid, extension)
    
    move_files(target_files)

    return 



if __name__ == "__main__":
    # target_files = glob.glob('x_band_test_data/four_images_F20250515170302*')
    # target_files = glob.glob('x_band_test_data/x_band_test_data/four_images_F20250515170302.bin')
    # target_files = glob.glob('x_band_test_data/part*.bin')
  
    files = glob.glob("data/x_devided_bin/*.bin")
    target_files = [f for f in files if "packet_base" not in f]

    # target_files = glob.glob("devide_bin/*packet_base*.bin")
    target_files.sort(reverse=False)
    target_files = target_files
    # target_files = target_files[:6]
    main(target_files)
