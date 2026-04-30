import os
import datetime
from tqdm import tqdm

# Constants (should match the transmitter and optical processing)
SYNC_MARKER = b'\x1A\xCF\xFC\x1D'
# Raw file no longer includes the optical extra header bytes after the sync marker
OPT_EXTRA_HEADER = 0       # Set to 0 since raw files have no extra header now
OPT_EXTRA_TRAILER = 160    # Optical receiver adds 160 bytes at the end of each packet
TX_HEADER_SIZE = 28        # Transmitter header after sync marker (2+3+1+22 = 28 bytes)
MAX_DATA_SIZE = 1087       # Payload size per packet

# Global counter for invalid VCDU headers.
invalid_vcdu_count = 0

def process_packet(raw_packet):
    """
    Process a single raw optical packet (one chunk from splitting by the sync marker).

    Raw optical packet structure:
      [Transmitter Packet: (VCDU header (2) + sequence (3) + reserved (1) + MDPU header (22) + payload (MAX_DATA_SIZE))]
      [Optical Extra Trailer (160 bytes)]

    The MDPU header (22 bytes) is structured as follows:
      • Bytes  0–1: Reserved (unique ID as 2 bytes)
      • Bytes  2–8: Destination callsign (7 bytes, e.g. "JG6YBW\x00")
      • Bytes  9–15: Unique identifier (4-byte hex, padded with 3 null bytes)
      • Byte     16: Data type (1 byte)
      • Bytes 17–20: Actual file length (4 bytes, big-endian) [total number of packets]
      • Byte     21: Packet type indicator (1 byte)
    """
    global invalid_vcdu_count
    # No extra header to trim; raw_packet already starts at the transmitter packet
    trimmed = raw_packet[OPT_EXTRA_HEADER:]
    transmitter_packet = trimmed[:-OPT_EXTRA_TRAILER]
    if len(transmitter_packet) < TX_HEADER_SIZE:
        return None

    # Validate VCDU header (first 2 bytes)
    vcdu = transmitter_packet[0:2]
    if vcdu != b'\x55\x40':
        invalid_vcdu_count += 1
        return None
    print(len(transmitter_packet))
    # Sequence number: bytes 2-4 (3 bytes)
    seq = int.from_bytes(transmitter_packet[2:5], 'big')
    mdpu_header = transmitter_packet[6:28]
    payload = transmitter_packet[28:28+MAX_DATA_SIZE]
    ptype = mdpu_header[21]
    # Interpret the MDPU header field as the total number of packets for the file.
    actual_file_length = int.from_bytes(mdpu_header[17:21], 'big')
    # Unique identifier: bytes 9–12 as an 8-digit hex string.
    file_uid = mdpu_header[9:13].hex()
    return seq, ptype, actual_file_length, payload, file_uid, mdpu_header


def decode_packets(received_file):
    """
    Reads the received optical file, processes each packet, and groups packets by file UID.

    Returns a dictionary where keys are file_uid and values are dicts with:
      'packets': list of (seq, ptype, payload)
      'num_packets': total expected (from MDPU header)
      'dest_callsign': extracted from MDPU header
    """
    with open(received_file, 'rb') as f:
        raw_data = f.read()
    packet_chunks = raw_data.split(SYNC_MARKER)[1:]
    if not packet_chunks:
        raise ValueError("No packets found in received file.")
    
    groups = {}
    for chunk in tqdm(packet_chunks, desc="Processing packets"):
        result = process_packet(chunk)
        if result is None:
            continue
        seq, ptype, num_packets, payload, file_uid, mdpu_header = result
        if file_uid not in groups:
            dest = mdpu_header[2:9].split(b'\x00')[0].decode('ascii', errors='replace')
            groups[file_uid] = {'packets': [], 'num_packets': num_packets, 'dest_callsign': dest}
        groups[file_uid]['packets'].append((seq, ptype, payload))
    return groups


def reassemble_group(group):
    packets = group['packets']
    packets.sort(key=lambda x: x[0])
    seqs = [p[0] for p in packets]
    first_seq = min(seqs)
    num_packets = group['num_packets']
    expected_last_seq = first_seq + num_packets - 1
    missing_seq = sorted(set(range(first_seq, expected_last_seq + 1)) - set(seqs))
    calculated_file_size = num_packets * MAX_DATA_SIZE
    
    # Determine file type based on first packet
    first_ptype = packets[0][1]
    if first_ptype == 0x03:
        file_type = 'TXT'
    elif first_ptype == 0x04:
        file_type = 'LOG'
    elif first_ptype == 0x01:
        file_type = 'CSV'
    elif first_ptype == 0x05:
        file_type = 'JPG'
    elif first_ptype == 0x06:
        file_type = 'H264'
    elif num_packets > 0:
        file_type = 'BIN'
    else:
        file_type = 'CSV'
    
    reassembled = bytearray()
    if file_type == 'BIN':
        for (seq, ptype, payload) in packets:
            effective_seq = seq - first_seq
            if ptype == 0x00:
                reassembled.extend(payload)
            elif ptype == 0x02:
                remaining = calculated_file_size - effective_seq * MAX_DATA_SIZE
                reassembled.extend(payload[:max(0, remaining)])
        reassembled = reassembled[:calculated_file_size]
    else:
        for (_, _, payload) in packets:
            reassembled.extend(payload)
        if file_type in ['JPG', 'H264']:
            reassembled = reassembled[:calculated_file_size]

    final_data = bytes(reassembled).rstrip(b'\0')
    return final_data, first_seq, expected_last_seq, missing_seq, file_type, calculated_file_size


def save_group_file(data, file_uid, file_type, first_seq, expected_last_seq, missing_seq, output_dir='./decoded'):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    ext = {'BIN':'bin','CSV':'csv','TXT':'txt','LOG':'log','JPG':'jpg','H264':'h264'}.get(file_type, 'dat')
    filename = os.path.join(output_dir, f"decoded_{timestamp}_{file_uid}_{file_type}.{ext}")
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved {file_type} file for UID {file_uid}: {filename}")
    if missing_seq:
        print(f"Missing sequences: {[hex(s) for s in missing_seq]}")
    return filename


def main():
    received_file = r"/Users/rh/Desktop/programing/python/2026/vertecs/x_band_analyzer/data/raw_data_unprocessed/hold/qpsk20Mbps.cadu"
    print(f"Decoding file: {received_file}")
    groups = decode_packets(received_file)
    if not groups:
        print("No valid packets found.")
        return
    print(f"Total invalid VCDU headers encountered: {invalid_vcdu_count}")
    for file_uid, group in groups.items():
        data, first_seq, expected_last_seq, missing_seq, file_type, size = reassemble_group(group)
        print(f"\nUID: {file_uid} | Type: {file_type}")
        print(f"Num Packets (header): {group['num_packets']}")
        print(f"Calculated Size: {size} bytes")
        print(f"First Seq: {first_seq:06X}")
        print(f"Expected Last Seq: {expected_last_seq:06X}")
        if missing_seq:
            print("Missing Seq (hex):", [f"{s:06X}" for s in missing_seq])
        else:
            print("No missing packets.")
        save_group_file(data, file_uid, file_type, first_seq, expected_last_seq, missing_seq)

if __name__ == '__main__':
    main()
