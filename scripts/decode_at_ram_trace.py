#!/usr/bin/env python3
"""Decode four Landmark RAM Trace pages, each in displayed T0 T1 T2 T3 order."""
import argparse
import json


def decode(pages):
    compare, path, physical, registers = pages
    ah, bl, bus = (compare[0] >> 16) & 255, (compare[0] >> 8) & 255, compare[0] & 255
    di = compare[2] & 65535
    es_base = physical[2] & 0xFFFFFF
    return {
        "format": f"{compare[0] >> 24:02X}",
        "cs_ip": f"{compare[1] >> 16:04X}:{compare[1] & 65535:04X}",
        "expected_AH": f"{ah:02X}", "received_BL": f"{bl:02X}", "CPU_bus_byte": f"{bus:02X}",
        "expected_xor_received": f"{ah ^ bl:02X}",
        "CX": f"{compare[2] >> 16:04X}", "DI_after_increment": f"{di:04X}",
        "FLAGS": f"{compare[3] >> 16:04X}", "ZF": bool(compare[3] & (1 << 22)),
        "SI": f"{compare[3] & 65535:04X}",
        "CPU_byte_address": f"{path[0] & 0xFFFFFF:06X}",
        "backend_byte_address": f"{path[1] & 0xFFFFFF:06X}",
        "KF_word_address": f"{path[2] & 0xFFFFFF:06X}",
        "CPU_flags": f"{path[0] >> 24:02X}", "backend_flags": f"{path[1] >> 24:02X}",
        "KF_flags": f"{path[2] >> 24:02X}",
        "CPU_word": f"{path[3] >> 16:04X}", "backend_word": f"{path[3] & 65535:04X}",
        "KF_word": f"{physical[0] >> 16:04X}",
        "DQM_READ": f"{(physical[0] >> 14) & 3:02b}",
        "DQM_sample": f"{(physical[0] >> 12) & 3:02b}",
        "BE": f"{(physical[0] >> 10) & 3:02b}",
        "owner_state": f"{(physical[0] >> 6) & 15:04b}",
        "ES": f"{physical[1] >> 16:04X}", "DS": f"{physical[1] & 65535:04X}",
        "ES_base": f"{es_base:06X}", "DS_base": f"{physical[3] & 0xFFFFFF:06X}",
        "address_from_ES_DI_minus_one": f"{(es_base + ((di - 1) & 65535)) & 0xFFFFFF:06X}",
        "AX": f"{registers[0] >> 16:04X}", "BX": f"{registers[0] & 65535:04X}",
        "DX": f"{registers[1] >> 16:04X}", "BP": f"{registers[1] & 65535:04X}",
        "last_write_byte_address": f"{registers[2] & 0xFFFFFF:06X}",
        "last_write_BE": f"{(registers[2] >> 24) & 3:02b}",
        "last_write_data": f"{registers[3] >> 16:04X}", "SP": f"{registers[3] & 65535:04X}",
    }


def word(value):
    result = int(value, 16)
    if not 0 <= result <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("each word must contain at most 8 hex digits")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for i, name in enumerate(("compare", "read", "sdram", "registers")):
        parser.add_argument("--" + name, nargs=4, type=word, required=True,
                            metavar=("T0", "T1", "T2", "T3"), help=f"Page {i}, displayed word order")
    args = parser.parse_args()
    print(json.dumps(decode([args.compare, args.read, args.sdram, args.registers]), indent=2))
