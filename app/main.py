import glob
from app import decode_controller, loss_diagnosis,  move_files
from common import file_io

"""
保守のためのテストコードを書く。
loggingを用いる
"""

def main(file_paths):
    # 1. 既存の損失データ読込
    packet_groups = file_io.load_loss_packet_group()
    # print(packet_groups)
    # 2. デコード
    decoded_packet_groups = decode_controller.decode_all_files(file_paths, packet_groups)

    # 3. ロス解析 & 保存
    loss_diagnosis.packet_loss_diagnosis(decoded_packet_groups)
    # 4. 後処理（例: 移動）
    # move_files.move_files(file_paths)

if __name__ == "__main__": 
    file_paths = glob.glob("data/raw_data_unprocessed/*.bin") + glob.glob("data/raw_data_unprocessed/*.cadu")
    file_paths.sort(reverse=False)
    main(file_paths)


# import glob
# from common import decode_utils 
# from common import constants as CONST 
# import datetime
# import os 
# import csv
# import pickle
# import shutil

# """
# トータルパケットを追加する
# 保存にタイプを記載する
# """

# def save_packet_group_file(data, file_uid, extension, output_dir='./output/X_band_decoded'):
#     os.makedirs(output_dir, exist_ok=True)
#     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#     file_created_time = datetime.datetime.fromtimestamp(int(file_uid,16)).strftime("%Y%m%d%H%M%S")
#     filename = f'{output_dir}/decoded_{file_created_time}_{timestamp}.{extension}'
#     with open(filename, 'wb') as f:
#         f.write(data)
#     print(f"Saved {extension} file for UID {file_uid} as: {filename}")
#     print(f"decoded :{filename}")
#     return filename
#     return


# # def initialize_loss_report_file():
# #     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
# #     os.makedirs('output/report',exist_ok=True)
# #     report_path = f'output/report/{timestamp}.csv'
# #     with open(report_path, mode='w') as f:
# #         writer = csv.writer(f)
# #         writer.writerow(["ID","extension","start","end","number"])
# #     return report_path

# def save_loss_packet_group(packet_loss_group,):
#     os.makedirs('data/loss_packet_group',exist_ok=True)
#     with open('data/loss_packet_group/loss_packet_group.pkl', 'wb') as f:
#         pickle.dump(packet_loss_group, f)
#     return

# def load_loss_packet_group():
#     path = 'data/loss_packet_group/loss_packet_group.pkl'
#     if not os.path.exists(path):
#         return {}
#     with open(path, 'rb') as f:
#         return pickle.load(f)
    

# # def reassemble_payload(payloads, extension):
# #     combined_packet = b"".join(payloads)
# #     if extension == 'bin':
# #         reassembled_data = combined_packet[:3003*3008*2] # end data handling
# #     else:
# #         reassembled_data = bytes(combined_packet).rstrip(b'\0')

# #     return reassembled_data

# # def extension_from_ptype(ptype):
# #     if ptype == 0x03:
# #         extension = 'txt'
# #     elif ptype == 0x04:
# #         extension = 'log'
# #     elif ptype == 0x01:
# #         extension = 'csv'
# #     elif ptype == 0x05:
# #         extension = 'jpg'
# #     else:
# #         extension = 'bin'
# #     return extension

# # def write_loss_report(report_path, file_uid, extension, loss_sequence):
# #     ranges = decode_utils.get_ranges(loss_sequence)
# #     with open(report_path, mode='a') as f:
# #         writer = csv.writer(f)
# #         for rng in ranges:
# #             writer.writerow([file_uid,extension]+list(rng))

# # def decode_all_files(file_paths,packet_groups):
# #     for target_file in file_paths:
# #         print(f"Decoding file: {target_file}")
# #         packet_groups = decode_utils.decode_packets(target_file, packet_groups)
# #     return packet_groups

# # def packet_loss_diagnosis(packet_groups):
# #     report_path = initialize_loss_report_file()
# #     packet_loss_group = {} 

# #     for file_uid, packet_group in packet_groups.items():
# #         payloads = packet_group['payloads']
# #         ptype = packet_group['ptypes'][0]
# #         extension = extension_from_ptype(ptype)
# #         print(f'file_uid is {file_uid}')
# #         loss_sequence = []
# #         for i, packet in enumerate(payloads):
# #             if packet == bytes([0xEE])*CONST.PAYLOAD_SIZE:
# #                 print(f'find packet loss @ {i}')
# #                 loss_sequence.append(i)
# #         if not loss_sequence:
# #             reassembled_data = reassemble_payload(payloads, extension)
# #             save_packet_group_file(reassembled_data, file_uid, extension)
# #         else:
# #             print(f'loss packet found {file_uid}')
# #             write_loss_report(report_path, file_uid, extension, loss_sequence)
# #             packet_loss_group[file_uid] = packet_group
# #     return packet_loss_group

# def main(file_paths):
#     packet_groups = load_loss_packet_group()
#     decoded_packet_groups = decode_all_files(file_paths, packet_groups)
#     loss_groups = packet_loss_diagnosis(decoded_packet_groups)
#     save_loss_packet_group(loss_groups)
#     # move_files(file_paths)



# if __name__ == "__main__": 
#     file_paths = glob.glob("data/raw_data_unprocessed/*.bin")
#     file_paths.sort(reverse=False)
#     main(file_paths)
