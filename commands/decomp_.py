# -*- coding: utf-8 -*-
import argparse
import json
import os
import re
import sys
from lib.radc import *


config_path = os.path.join("commands/data", "config.json")

if not os.path.exists(config_path):
    print(f"Error: Configuration file '{config_path}' not found.", file=sys.stderr)
    sys.exit()

try:
    with open(config_path, "r", encoding="utf-8") as json_file:
        config_data = json.load(json_file)
except Exception as e:
    print(f"Error: Failed to parse {config_path}. Invalid JSON format. ({e})", file=sys.stderr)
    sys.exit()

g_name = config_data.get("gadgets", "gadgets.txt")
l_name = config_data.get("labels", "labels.txt")
d_name = config_data.get("disasm", "disas.asm")

gadgets_file = os.path.join("commands/data", g_name)
labels_file = os.path.join("commands/data", l_name)
disasm_file = os.path.join("commands/data", d_name)

load_gadgets(gadgets_file)
load_labels(labels_file)
if os.path.exists(disasm_file):
    load_disassembly(disasm_file)
else:
    print(f"Warning: Disassembly file '{disasm_file}' not found.", file=sys.stderr)

hex_program_content = sys.stdin.read().strip()

start_dest, start_src = 0xd730, 0xe9e0  

src_match = re.search(r'\[\s*src\s*:\s*(0x[0-9a-fA-F]+|\d+)\s*\]', hex_program_content, re.IGNORECASE)
dest_match = re.search(r'\[\s*dest\s*:\s*(0x[0-9a-fA-F]+|\d+)\s*\]', hex_program_content, re.IGNORECASE)

if src_match:
    start_src = int(src_match.group(1), 0)
    hex_program_content = re.sub(r'\[\s*src\s*:\s*(0x[0-9a-fA-F]+|\d+)\s*\]', '', hex_program_content, flags=re.IGNORECASE)
if dest_match:
    start_dest = int(dest_match.group(1), 0)
    hex_program_content = re.sub(r'\[\s*dest\s*:\s*(0x[0-9a-fA-F]+|\d+)\s*\]', '', hex_program_content, flags=re.IGNORECASE)

hex_program_content = re.sub(r'\[.*?\]', '', hex_program_content)

bytes_list = parse_hex(hex_program_content)
if not bytes_list:
    print("Error: Input file hex payload stream is either blank or invalidly aligned.", file=sys.stderr)
    sys.exit(1)

parsed_items = tokenize(bytes_list, start_dest, start_src)
referenced_items = resolve_labels(parsed_items, start_dest, start_src)

output_result = process_program(referenced_items, start_dest, start_src)

print(output_result)