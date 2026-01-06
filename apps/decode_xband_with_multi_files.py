import os
import datetime
import glob
from tqdm import tqdm
import json
import numpy as np

# Constants (should match the transmitter and optical processing)
SYNC_MARKER = b'\x1A\xCF\xFC\x1D'
OPT_EXTRA_HEADER = 28      # Optical receiver adds 28 bytes at the beginning
OPT_EXTRA_TRAILER = 160    # ...and 160 bytes at the end of each packet
TX_HEADER_SIZE = 28        # Transmitter header after sync marker (2+3+1+22 = 28 bytes)
PAYLOAD_SIZE = 1087       # Payload size per packet

PTYPE_NORMAL  = 0x00
PTYPE_FINAL  = 0x02

# Global counter for invalid VCDU headers.
invalid_vcdu_count = 0

def process_packet(raw_packet):
    """
    Process a single raw optical packet (one chunk from splitting by the sync marker).

    Raw optical packet structure:
      [Optical Extra Header (28 bytes)] +
      [Transmitter Packet: (VCDU header (2) + sequence (3) + reserved (1) + MDPU header (22) + payload (PAYLOAD_SIZE))] +
      [Optical Extra Trailer (160 bytes)]
      
    The new MDPU header (22 bytes) is structured as follows:
      • Bytes  0–1: Reserved (unique ID as 2 bytes, from the first 2 bytes of the provided hex identifier)
      • Bytes  2–8: Destination callsign (7 bytes, e.g. "JG6YBW\x00")
      • Bytes  9–15: Unique identifier (4-byte hex derived from the provided hex identifier, padded with 3 null bytes)
      • Byte     16: Data type (1 byte)
      • Bytes 17–20: Actual file length (4 bytes, big-endian) [Now represents the total number of packets]
      • Byte     21: Packet type indicator (1 byte)
    
    Returns a tuple:
      (seq, ptype, actual_file_length, payload, file_uid, mdpu_header)
    where file_uid is the unique identifier as an 8-digit hex string.
    """
    global invalid_vcdu_count
    trimmed = raw_packet[OPT_EXTRA_HEADER:]
    transmitter_packet = trimmed[:-OPT_EXTRA_TRAILER]
    if len(transmitter_packet) < TX_HEADER_SIZE:
        return None

    # Validate VCDU header (first 2 bytes)
    vcdu = transmitter_packet[0:2]
    if vcdu != b'\x55\x40':
        invalid_vcdu_count += 1
        return None

    # Sequence number: bytes 2-4 (3 bytes)
    seq = int.from_bytes(transmitter_packet[2:5], 'big')
    mdpu_header = transmitter_packet[6:28]
    payload = transmitter_packet[28:28+PAYLOAD_SIZE]
    ptype = mdpu_header[21]
    # Interpret the MDPU header field as the total number of packets for the file.
    actual_file_length = int.from_bytes(mdpu_header[17:21], 'big')
    # Unique identifier: bytes 9–12 (first 4 bytes of the unique info) as an 8-digit hex string.
    file_uid = mdpu_header[9:13].hex()
    return seq, ptype, actual_file_length, payload, file_uid, mdpu_header



def decode_packets(packet_groups, target_file):
    """
    Reads the received optical file, processes each packet, and packet_groups packets by file UID.
    
    Returns a dictionary where keys are file_uid (8-digit hex string) and values are dictionaries with:
      'packets': list of (seq, ptype, payload)
      'total_packet_size': total number of packets expected (from MDPU header, same for all packets in packet_group)
      'dest_callsign': destination callsign extracted from MDPU header.
    """
    with open(target_file, 'rb') as f:
        raw_data = f.read()
    packet_chunks = raw_data.split(SYNC_MARKER)[1:]
    if not packet_chunks:
        raise ValueError("No packets found in received file.")
    
    #  = {}  # key: file_uid, value: dictionary with keys: 'packets', 'total_packet_size', 'dest_callsign'
    for chunk in tqdm(packet_chunks, desc="Processing packets"):
        result = process_packet(chunk)
        if result is None:
            continue
        seq, ptype, total_packet_size, payload, file_uid, mdpu_header = result
        if ptype == 0x00:
            total_packet_size = 16621

        if file_uid not in packet_groups:
            # Extract destination callsign from bytes 2-8 (null terminated)
            dest = mdpu_header[2:9].split(b'\x00')[0].decode('ascii', errors='replace')
            # packet_groups[file_uid] = {'packets':{"payload":[b'FF'] * total_packet_size,'ptype':ptype}, 'total_packet_size': total_packet_size, 'dest_callsign': dest}
            packet_groups[file_uid] = {
                'packets': [bytes([0xDD]) * PAYLOAD_SIZE for _ in range(total_packet_size)],
                'ptypes': [None] * total_packet_size,
                'total_packet_size': total_packet_size,
                'dest_callsign': dest
            }

        packet_groups[file_uid]['packets'][seq] = payload
        packet_groups[file_uid]['ptypes'][seq] = ptype
    return packet_groups

def reassemble_packet_group(packet_group):
    packet_data = packet_group['packets']
    combined_packet = b"".join(packet_data)
    reassembled_data = combined_packet[:3003*3008*2] # end data handling
    # reassembled_data = bytes(combined_packet).rstrip(b'\0') # end data handling
    missing_seq = 0
    first_ptype = packet_group['ptypes'][0]
    if first_ptype == 0x03:
        extension = 'txt'
    elif first_ptype == 0x04:
        extension = 'log'
    elif first_ptype == 0x01:
        extension = 'csv'
    elif first_ptype == 0x05:
        extension = 'jpg'
    else:
        extension = 'bin'

    return reassembled_data, missing_seq, extension
    

def save_packet_group_file(data,file_uid, extension, output_dir='./X_band_decoded'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
    filename = f'{output_dir}/decoded_{file_created_time}_{timestamp}.{extension}'
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved {extension} file for UID {file_uid} as: {filename}")
    # print(f"First packet sequence: {first_seq:06X} (dec: {first_seq}), Expected last packet sequence: {expected_last_seq:06X} (dec: {expected_last_seq})")
    # if missing_seq:
    #     print(f"Missing sequences: {[f'{s:06X}' for s in missing_seq]}")
    # else:
    #     print("No missing packets.")
    print(f"decoded :{filename}")
    return filename

def move_files(target_file):
    """
    Docstring for move_file
    move target file after all process complete

    :param target_file: Description
    """
    print("move to delete file(not developed)")
def main(target_files):

    packet_groups = {}
    for target_file in target_files:
        print(f"Decoding file: {target_file}")
        packet_groups = decode_packets(packet_groups,target_file)

    print(f"Total invalid VCDU headers encountered: {invalid_vcdu_count}")
    
    for file_uid, packet_group in packet_groups.items():
        reassembled_data, missing_seq, extension = reassemble_packet_group(packet_group)
        total_packet_size = packet_group['total_packet_size']
        calculated_file_size = total_packet_size * PAYLOAD_SIZE  # Total file size in bytes based on packet count.

        print(f"\nUID: {file_uid} | Type: {extension}")
        print(f"Number of Packets (from MDPU header): {total_packet_size}")
        print(f"Calculated File Size (from packet count): {calculated_file_size} bytes")

        if missing_seq:
            ranges = get_ranges(missing_seq)
            print("Missing packet sequence numbers (start, end, loss numbers):", (ranges))
            print(f"Missing packet numbers: {len(missing_seq)}")
            #save_with_missing_seq()
        else:
            print("No missing packets.")
            save_packet_group_file(reassembled_data, file_uid, extension)
    
    move_files(target_files)
    
def get_ranges(nums):
    if not nums:
        return []
    
    ranges = []
    start = nums[0]
    prev = nums[0]

    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        
        # 連続が途切れたので範囲を保存
        numbers = prev - start + 1
        ranges.append((start, prev, numbers))
    
        start = n
        prev = n

    # 最後の範囲を追加
    numbers = prev - start + 1

    ranges.append((start, prev, numbers))
    return ranges

if __name__ == "__main__":
    # target_files = glob.glob('x_band_test_data/four_images_F20250515170302*')
    # target_files = glob.glob('x_band_test_data/x_band_test_data/four_images_F20250515170302.bin')
    # target_files = glob.glob('x_band_test_data/part*.bin')
  
    files = glob.glob("devide_bin/*.bin")
    target_files = [f for f in files if "packet_base" not in f]

    # target_files = glob.glob("devide_bin/*packet_base*.bin")
    target_files.sort(reverse=False)
    target_files = target_files
    # target_files = target_files[:6]
    main(target_files)
