# from common import decode_utils, file_io
# import csv
# import datetime
# import os
# from common import constants as CONST
# from dataclasses import dataclass

# @dataclass
# class DiagnosisResult:
#     completed: dict        # {file_uid: output_filename}
#     lost: dict             # {file_uid: packet_group}
#     report_path: str       # created CSV report path

from common import decode_utils, file_io
import csv
import datetime
from common import constants as CONST
from common.paths import REPORT_DIR

def packet_loss_diagnosis(packet_groups):
    """
    ロスあり -> ロスレポート + EEフィル済み未完成ファイル保存
    ロスなし -> 完成ファイル生成 
    ロスの有無にかかわらず -> 次回用パケットグループを保存
    """

    report_path = _create_loss_report_file()
    loss_packet_groups = {} 
    for file_uid, packet_group in packet_groups.items():
        print(f"missing file_uid {file_uid}")
        extension = _extract_extension(packet_group)
        loss_sequence = analyze_packet_loss(packet_group)

        if loss_sequence:
            _handle_loss_case(report_path, file_uid, extension, loss_sequence, packet_group, loss_packet_groups)
        else:
            _handle_complete_case(file_uid, extension, packet_group)

    file_io.save_loss_packet_group(loss_packet_groups)
    return loss_packet_groups



# -----------------------------
# 1. ロス解析
# -----------------------------
# def analyze_packet_loss(packet_group):
#     """ロス位置(index)をリストで返す"""
#     # print(packet_group)
#     payloads = packet_group["payloads"]
#     loss_sequence = [
#         i for i, packet in enumerate(payloads)
#         if packet == bytes([0xEE]) * CONST.PAYLOAD_SIZE
#     ]
#     return loss_sequence

def analyze_packet_loss(packet_group):
    """ロス位置(index)をリストで返す"""
    return [
        i for i, ptype in enumerate(packet_group["ptypes"])
        if ptype is None
    ]

# -----------------------------
# 2. ロスなしケース処理
# -----------------------------
def _handle_complete_case(file_uid, extension, packet_group):
    payloads = packet_group["payloads"]
    reassembled_data = reassemble_payload(payloads, extension)
    file_io.save_packet_group_file(reassembled_data, file_uid, extension)
    print(extension)
    # if extension == "bin":
    #     file_io.save_bin_bytes_as_fits(reassembled_data, file_uid, extension)
    #     print('save fits')
        
    print(f"save {file_uid}")


# -----------------------------
# 3. ロスありケース処理
# -----------------------------
def _handle_loss_case(report_path, file_uid, extension, loss_sequence,
                      packet_group, loss_packet_groups):
    file_io.write_loss_report(report_path, file_uid, extension, loss_sequence)

    missing_count = len(loss_sequence)
    received_count = len(packet_group["ptypes"]) - missing_count
    print(f"save EE-filled {file_uid}: received={received_count}, missing={missing_count}")

    payloads = packet_group["payloads"]
    reassembled_data = reassemble_payload(payloads, extension)
    file_io.save_packet_group_file_EE_filled(reassembled_data, file_uid, extension, )
    
    loss_packet_groups[file_uid] = packet_group


# -----------------------------
# 付属機能
# -----------------------------
# def _extract_extension(packet_group):
#     ptype = packet_group["ptypes"][0]
#     return decode_utils.extension_from_ptype(ptype)
def _extract_extension(packet_group):
    for ptype in packet_group["ptypes"]:
        if ptype is not None:
            return decode_utils.extension_from_ptype(ptype)
    raise ValueError("Cannot determine extension because all packet types are missing")


def _create_loss_report_file():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{timestamp}.csv"
    with path.open(mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "extension", "start", "end", "number"])

    return path


def reassemble_payload(payloads, extension):
    combined = b"".join(payloads)
    if extension == "bin":
        return combined[: 3003 * 3008 * 2]  # 固定長補正
    return combined.rstrip(b"\0")




# def reassemble_payload(payloads, extension):
#     combined_packet = b"".join(payloads)
#     if extension == 'bin':
#         reassembled_data = combined_packet[:3003*3008*2] # end data handling
#     else:
#         reassembled_data = bytes(combined_packet).rstrip(b'\0')

#     return reassembled_data


# def analyze_packet_loss(packet_group):
#     payloads = packet_group['payloads']
#     loss_sequence = []

#     for i, packet in enumerate(payloads):
#         if packet == bytes([0xEE]) * CONST.PAYLOAD_SIZE:
#             loss_sequence.append(i)

#     return loss_sequence


# # def packet_loss_diagnosis(packet_groups):

# #     report_path = file_io.create_loss_report_file()
# #     completed = {}
# #     lost = {}

# #     for file_uid, packet_group in packet_groups.items():

# #         print(f'file_uid is {file_uid}')

# #         # --- ロス解析 ---
# #         loss_sequence = analyze_packet_loss(packet_group)

# #         ptype = packet_group['ptypes'][0]
# #         extension = decode_utils.extension_from_ptype(ptype)

# #         # --- 完成 ---
# #         if not loss_sequence:
# #             reassembled = reassemble_payload(
# #                 packet_group['payloads'],
# #                 extension
# #             )
# #             output_name = file_io.save_packet_group_file(
# #                 reassembled, file_uid, extension
# #             )
# #             completed[file_uid] = output_name
# #             continue

# #         # --- ロス ---
# #         print(f'loss packet found {file_uid}')
# #         file_io.write_loss_report(report_path, file_uid, extension, loss_sequence)
# #         lost[file_uid] = packet_group

# #     return DiagnosisResult(
# #         completed=completed,
# #         lost=lost,
# #     )

# # def analyze_packet_loss(packet_group):
# #     payloads = packet_group['payloads']
# #     loss_sequence = []

# #     for i, packet in enumerate(payloads):
# #         if packet == bytes([0xEE]) * CONST.PAYLOAD_SIZE:
# #             loss_sequence.append(i)

# #     return loss_sequence

# # def run_diagnosis(packet_groups):
# #     diagnosis_results = packet_loss_diagnosis(packet_groups)

# #     # 4. ロスなし → 完成系保存
# #     file_io.save_packet_group_file(diagnosis_results.completed)

# #     # 5. ロスあり → レポート保存
# #     file_io.write_loss_report(diagnosis_results.lost)

# #     # 6. ロスありグループだけを保存
# #     file_io.save_loss_packet_group(diagnosis_results.lost_groups)
# #     return 

# # def packet_loss_diagnosis(packet_groups):

# #     report_path = file_io.create_loss_report_file()
# #     packet_loss_group = {}

# #     for file_uid, packet_group in packet_groups.items():

# #         print(f'file_uid is {file_uid}')

# #         # --- 1) ロス解析（純ロジック） ---
# #         loss_sequence = analyze_packet_loss(packet_group)

# #         ptype = packet_group['ptypes'][0]
# #         extension = decode_utils.extension_from_ptype(ptype)

# #         # --- 2) ロスなし：完成データ保存 ---
# #         if not loss_sequence:
# #             reassembled_data = reassemble_payload(
# #                 packet_group['payloads'], extension
# #             )
# #             file_io.save_packet_group_file(reassembled_data, file_uid, extension)
# #             continue

# #         # --- 3) ロスあり：レポート & 未完成データ保存 ---
# #         print(f'loss packet found {file_uid}')
# #         write_loss_report(report_path, file_uid, extension, loss_sequence)

# #         # 次回 decode のため保存
# #         packet_loss_group[file_uid] = packet_group

# #     return packet_loss_group
