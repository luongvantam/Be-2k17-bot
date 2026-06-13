import sys
import os
import re
from typing import List, Dict, Optional, Set

# --- CONSTANT FOR LENGTH CHECK ---
MAX_OUTPUT_LENGTH = 1900 

# --- New Function to Strip ANSI Codes ---
def strip_ansi_colors(text: str) -> str:
    """Removes all ANSI escape sequences from a string."""
    # Regex to match ANSI escape codes: \x1b[...m
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

# --- Existing Helper Functions (omitted for brevity) ---
def load_file(model: str) -> List[str]:
    path = os.path.join("./commands/data", f"{model}.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip() for line in f if line.strip()]

def extract_address_from_line(line: str) -> str:
    match = re.match(r"([0-9A-F]+:[0-9A-F]{4}H)", line.strip(), re.IGNORECASE)
    if match: return match.group(1).upper()
    return ""

def extract_instruction_payload(line: str) -> str:
    addr_match = re.match(r"([0-9A-F]+:[0-9A-F]{4}H)", line.strip(), re.IGNORECASE)
    if not addr_match: return ""
    payload_part = line[addr_match.end():].strip()
    parts = re.sub(r'\s+', ' ', payload_part).strip().split(maxsplit=2)
    if len(parts) >= 2: return f"{parts[0]} {parts[1]}".upper()
    return ""

def get_source_chain(src_lines: List[str], search_addr: str) -> List[str]:
    search_low = search_addr.lower()
    start_index = -1
    for i, line in enumerate(src_lines):
        if search_low in line.lower():
            start_index = i
            break
    if start_index == -1: return []
    target_payload = extract_instruction_payload(src_lines[start_index])
    if not target_payload: return []
    next_index = start_index + 1
    next_payload = ""
    while next_index < len(src_lines):
        next_payload = extract_instruction_payload(src_lines[next_index])
        if next_payload: break
        next_index += 1
    chain = [target_payload.upper()]
    if next_payload: chain.append(next_payload.upper())
    return chain

def translate_by_chain_match(src_chain: List[str], dst_lines: List[str]) -> List[str]:
    if not src_chain: return []
    results: Set[str] = set()
    n_chain = len(src_chain)
    for i in range(len(dst_lines)):
        dst_payload_start = extract_instruction_payload(dst_lines[i])
        if dst_payload_start.upper() != src_chain[0].upper(): continue
        if n_chain == 1:
            results.add(dst_lines[i])
            continue
        if n_chain == 2:
            next_index = i + 1
            dst_payload_next = ""
            while next_index < len(dst_lines):
                dst_payload_next = extract_instruction_payload(dst_lines[next_index])
                if dst_payload_next: break
                next_index += 1
            if dst_payload_next.upper() == src_chain[1].upper():
                 results.add(dst_lines[i])
    return list(results)

def normalize_address(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("0x", "").replace("h", "")
    if ":" in s:
        bank, addr = s.split(":", 1)
    else:
        if len(s) >= 5 and s[0].isalnum():
             bank, addr = s[0], s[1:]
        else:
             raise ValueError(f"Invalid address format: {s}")
    addr = addr.zfill(4).upper()
    return f"{bank.upper()}:{addr}H"

def hex_to_address(hex_str: str) -> str:
    clean = ''.join(re.findall(r'[0-9A-Fa-f]{2}', hex_str))
    if len(clean) != 8:
        raise ValueError("Input must be 4 bytes (8 hex chars)")
    b1, b2, b3, b4 = clean[0:2], clean[2:4], clean[4:6], clean[6:8]
    offset = f"{b2}{b1}".upper().zfill(4)
    bank = int(b3[1], 16)
    return f"{bank:X}:{offset}H"

def decrement_address(addr: str) -> str:
    match = re.match(r"([0-9A-F]+):([0-9A-F]{4})H", addr, re.IGNORECASE)
    if not match: return addr
    bank, offset = match.groups()
    value = int(offset, 16)
    if value == 0: return addr
    new_value = value - 1
    return f"{bank.upper()}:{new_value:04X}H"

def extract_offset_int(addr: str) -> int:
    match = re.match(r"([0-9A-F]+):([0-9A-F]{4})H", addr, re.IGNORECASE)
    if not match: return -1
    return int(match.groups()[1], 16)

def closest(translated_lines: List[str], original_addr: str) -> str:
    if not translated_lines: return ""
    original_offset = extract_offset_int(original_addr)
    if original_offset == -1: return translated_lines[0]
    best_line = translated_lines[0]
    min_diff = float('inf')
    for line in translated_lines:
        current_addr = extract_address_from_line(line)
        current_offset = extract_offset_int(current_addr)
        if current_offset != -1:
            diff = abs(current_offset - original_offset)
            if diff < min_diff:
                min_diff = diff
                best_line = line
            elif diff == min_diff and current_offset < extract_offset_int(extract_address_from_line(best_line)):
                 best_line = line
    return best_line

def parse_multi_addresses(raw_input: str) -> List[str]:
    s = re.sub(r'[\s;]+', ',', raw_input.strip())
    s = re.sub(r',+', ',', s)
    addresses = [addr.strip() for addr in s.split(',') if addr.strip()]
    return addresses

def format_address_input(raw_addr: str) -> Optional[str]:
    try:
        if re.fullmatch(r'([0-9A-Fa-f]{2}\s*){4}', raw_addr.strip()):
            return hex_to_address(raw_addr)
        else:
            return normalize_address(raw_addr)
    except ValueError:
        return None

# --- UPDATED translate_single_gadget FUNCTION ---

def translate_single_gadget(src_lines: List[str], dst_lines: List[str], raw_input: str, use_colors: bool) -> List[str]:
    """Translates a single gadget and returns formatted output lines."""
    output = []
    
    formatted_addr = format_address_input(raw_input)
    
    gadget_header_addr = formatted_addr.upper() if formatted_addr else raw_input.strip() 
    output.append(f"---Gadget {gadget_header_addr}---")

    if formatted_addr is None:
        output.append(f"Error: Invalid address format for '{raw_input}'. Skipping.")
        return output

    # 1. Find source gadget chain (try up to 4 decrements)
    source_chain = []
    current_addr = formatted_addr
    attempts = 0
    while attempts < 4:
        source_chain = get_source_chain(src_lines, current_addr)
        if source_chain: break
        current_addr = decrement_address(current_addr)
        attempts += 1
        
    if not source_chain:
        output.append(f"No valid ROP instruction found for {formatted_addr} after {attempts} attempts.")
        return output

    # 2. Find ALL matching destination gadgets
    results = translate_by_chain_match(source_chain, dst_lines)
    
    if results:
        # 3. Find the closest match and format output
        closest_result_line = closest(results, formatted_addr)
        sorted_results = sorted(results, key=extract_address_from_line) 
        
        for res_line in sorted_results: 
            if res_line.strip() == closest_result_line.strip():
                line = (
                    f"{res_line}"
                    f" [closest option]" 
                )
            else:
                line = res_line
            output.append(line)
            
    else:
        output.append(f"No translations found for ROP chain matching '{formatted_addr}' in target model.")
        
    return output

# --- UPDATED translate_multiple_gadgets FUNCTION ---

def translate_multiple_gadgets(src_model: str, dst_model: str, raw_input: str):
    """Controls the translation process for multiple ROP gadgets with length check for colors."""
    try:
        src_lines = load_file(src_model)
        dst_lines = load_file(dst_model)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return

    raw_addresses = parse_multi_addresses(raw_input)
    
    if not raw_addresses:
        print(f"Error: No valid addresses provided for translation.")
        return
    
    colored_output = []
    
    colored_output.append(f"---ROP Translation Result from {src_model} to {dst_model}---")
    
    for i, raw_addr in enumerate(raw_addresses):
        if i > 0:
            colored_output.append("") 
            
        result_lines = translate_single_gadget(src_lines, dst_lines, raw_addr, use_colors=True)
        colored_output.extend(result_lines)
    
    # --- Phase 2: Check length and finalize output ---
    
    final_output_string = "\n".join(colored_output).strip()
    
    # Check the length of the string without color codes
    stripped_output_string = strip_ansi_colors(final_output_string)
    
    if len(stripped_output_string) > MAX_OUTPUT_LENGTH:
        print(stripped_output_string)
    else:
        print(final_output_string)

def main():
    if len(sys.argv) < 4:
        print(f"Usage: python translator_rop.py <source_model> <target_model> <address1> [<address2>...]")
        print(f"Example 1: python translator_rop.py model_a model_b \"1:7b34h 2:03d2h\"")
        print(f"Example 2: python translator_rop.py model_a model_b 1:7b34h; 2:03d2h")
        return

    src_model = sys.argv[1]
    dst_model = sys.argv[2]
    raw_input_chain = " ".join(sys.argv[3:]) 

    translate_multiple_gadgets(src_model, dst_model, raw_input_chain)

if __name__ == "__main__":
    main()