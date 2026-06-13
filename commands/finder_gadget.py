import re
import sys
import itertools

def expand_register_pattern(template, max_value=15):
    """
    {1}   -> [0-9]
    {2} -> (?:[0-9]|1[0-4])
    """
    # tìm các biến dạng {a}
    vars_found = sorted(set(re.findall(r"\{([a-zA-Z_]\w*)\}", template)))

    if not vars_found:
        return [template]

    results = []

    # sinh mọi tổ hợp giá trị cho các biến
    for values in itertools.product(range(max_value + 1), repeat=len(vars_found)):
        mapping = dict(zip(vars_found, values))

        def replacer(match):
            var_name = match.group(1)
            return str(mapping[var_name])

        expanded = re.sub(r"\{([a-zA-Z_]\w*)\}", replacer, template)
        results.append(expanded)

    return results


def build_full_regex(instructions):
    line_prefix = r"\d:[0-9A-F]+H\s+[0-9A-F]+\s+"

    # expand toàn bộ instruction thành mọi tổ hợp
    expanded_instr_lists = [expand_register_pattern(instr) for instr in instructions]

    full_patterns = []

    # sinh tổ hợp giữa các dòng instruction
    for combo in itertools.product(*expanded_instr_lists):

        pattern = ""
        for i, instr in enumerate(combo):
            pattern += line_prefix + instr
            if i != len(combo) - 1:
                pattern += r"\r?\n"

        full_patterns.append(pattern)

    # nối tất cả pattern bằng OR
    return "|".join(full_patterns)

def search_gadgets(disas_file, pattern):
    with open(disas_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()

    line_to_func = {}
    current_func = "<unknown>"

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.endswith(":") and "." not in stripped:
            current_func = stripped
        line_to_func[idx] = current_func

    matches = list(re.finditer(pattern, content, re.MULTILINE))

    if not matches:
        print("[-] Not found.")
        return

    print(f"[+] Found {len(matches)} gadgets:\n")

    for m in matches:
        start_pos = m.start()
        start_line = content[:start_pos].count("\n")

        func_name = line_to_func.get(start_line, "<unknown>")

        print(f"In function {func_name}")
        print(m.group()+"\n")

def parse_instruction_string(instr_string):
    """
    Supports:
    - \n
    - ;
    """
    instr_string = instr_string.replace(";", "\n")
    lines = instr_string.splitlines()

    return [line.strip().upper() for line in lines if line.strip()]

def main():
    if len(sys.argv) != 3:
        print("Usage:")
        print('python find_gadgets.py disas.txt "pop er2;pop pc"')
        sys.exit(1)

    #disas_file = sys.argv[1]
    disas_file = "./commands/data/fx580vnx.txt"
    instruction_string = sys.argv[2]

    instructions = parse_instruction_string(instruction_string)

    pattern = build_full_regex(instructions)

    #print("\n[DEBUG REGEX]:\n")
    #print(pattern)
    #print("\nSearching...\n")

    search_gadgets(disas_file, pattern)

if __name__ == "__main__":
    main()