#!/usr/bin/env python3
import sys
import re

MAX_TOKENS = 21
HEX_RE = re.compile(r'^[0-9A-Fa-f]{1,2}$')

byte_table = [
    0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 1,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1,
    2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1, 1, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    2, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1,
    2, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
]

def normalize(raw_tokens):
    toks = [t.strip().upper() for t in raw_tokens if t.strip()]
    for t in toks:
        if not HEX_RE.match(t):
            print(f"Invalid hex byte: {t}")
    return [t.zfill(2).upper() for t in toks]

def split_hex_bytes(hex_string):
    hex_string = hex_string.strip().replace(' ', '')
    if len(hex_string) % 2 != 0:
        print("Hex string must have an even number of characters.")
    return [hex_string[i:i+2].upper() for i in range(0, len(hex_string), 2)]


def contains_letter(tok):
    return any(ch in 'ABCDEF' for ch in tok)


def parse_and_transform(hex_string):
    global byte_table
    raw = split_hex_bytes(hex_string)
    normalized_toks = normalize(raw)

    byte_1 = []
    checked_toks = []
    i = 0
    while i < len(normalized_toks):
        t = normalized_toks[i]
        val = int(t, 16)

        if t.upper().startswith("F"):
            if i + 1 >= len(normalized_toks):
                continue
            pair_next = normalized_toks[i + 1]

            checked_toks.append(t)
            checked_toks.append(pair_next)
            byte_1.append(t + pair_next)
            i += 2
            continue

        if byte_table[val] == 0:
            output = "contains invalid byte 00"
            return output, byte_1
        elif byte_table[val] == 1:
            checked_toks.append(t)
            byte_1.append(t)

        i += 1

    normalized_toks = checked_toks

    all_toks = ['00', '00'] + normalized_toks

    i = 0
    while i < len(all_toks):
        if (i % 8 == 5 or i % 8 == 7) and contains_letter(all_toks[i]):
            insert_pos = i
            if i > 0 and all_toks[i-1].startswith('F'):
                insert_pos = i - 1
            
            all_toks.insert(insert_pos, '30')
            i += 1
        i += 1

    A_final = all_toks[0:8]
    B_final = all_toks[8:16]
    C_final = all_toks[16:]

    if C_final:
        C_final.append('23')
    elif B_final:
        B_final.append('23')
    elif A_final:
        A_final.append('23')

    if len(A_final) + len(B_final) + len(C_final) <= 24:
        if len(A_final) == 8 and (B_final or C_final):
            A_final = A_final[:-1] + ['x10^', A_final[-1]]

        if len(B_final) == 8 and C_final:
            B_final = B_final[:-1] + ['x10^', B_final[-1]]

        if len(C_final) == 8:
            C_final = C_final[:-1] + ['x10^', C_final[-1]]

        output = [A_final, B_final, C_final]
        names = ['A', 'B', 'C']
        parts = []
        for i, arr in enumerate(output):
            if arr:
                parts.append(f"{names[i]} = 1. {' '.join(arr)}")
        output = ":\n".join(parts)
    else:
        output="The length of the hex string exceeds 21 bytes."

    return output, byte_1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        inp = ' '.join(sys.argv[1:])

    try:
        out, byte1 = parse_and_transform(inp)
        print(out)
        if out != "The length of the hex string exceeds 21 bytes.":
            if byte1:
                print('\nNumber of bytes to assign:', ' '.join(byte1))
            else:
                print('\nNo bytes to assign.')
    except Exception as e:
        print('Error:', e)