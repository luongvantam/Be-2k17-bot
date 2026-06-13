blocked_user_ids = []

help_text_en = (
    "```ansi\n"
    "\x1b[1;37mList of available commands (fx580vnx only):\x1b[0m\n\n"
    "\x1b[1;34m[Decompile]\x1b[0m\n"
    " \x1b[1;32mo!decomp <hex>\x1b[0m        Decompile hex to asm\n\n"
    "\x1b[1;34m[Compile]\x1b[0m\n"
    " \x1b[1;32mo!comp <code/attachment>\x1b[0m        Compile asm to hex\n\n"
    "\x1b[1;34m[Gadget Finder]\x1b[0m\n"
    " \x1b[1;32mo!find_gadget <gadget>\x1b[0m   Search gadgets in disassembly\n\n"
    "\x1b[1;34m[Translation]\x1b[0m\n"
    " \x1b[1;32mo!vnx2cnx <gadgets>\x1b[0m  Translate gadgets fx580vnx → fx991cnx\n"
    " \x1b[1;32mo!cnx2vnx <gadgets>\x1b[0m  Translate gadgets fx991cnx → fx580vnx\n\n"
    "\x1b[1;34m[Conversion]\x1b[0m\n"
    " \x1b[1;32mo!conv_hex <hex>\x1b[0m    Convert hex to tokens/characters\n"
    " \x1b[1;32mo!hex_split <hex>\x1b[0m   Split hex string to sort into variables\n"
    " \x1b[1;32mo!p2h <attachment>\x1b[0m    Convert attached image to hex\n"
    " \x1b[1;32mo!h2p <hex/attachment>\x1b[0m Convert hex to image\n\n"
    "\x1b[1;34m[Generator]\x1b[0m\n"
    " \x1b[1;32mo!talk <prompt>\x1b[0m talk with AI\n\n"
    "\x1b[1;34m[General]\x1b[0m\n"
    " \x1b[1;32mo!help <vi/en/ >\x1b[0m               Show command list\n"
    " \x1b[1;32mo!usage <vi/en/ > <command>\x1b[0m    Show detailed usage of a command (no need for o!)\n\n"
    "\x1b[1;37mContribute:\x1b[0m\n"
    "  Created by luongvantam\n"
    "```"
)

help_text_vi = (
    "```ansi\n"
    "\x1b[1;37mDanh sách các lệnh có thể dùng (chỉ cho fx580vnx):\x1b[0m\n\n"
    "\x1b[1;34m[Decompiler]\x1b[0m\n"
    " \x1b[1;32mo!decomp <hex>\x1b[0m        Decomp hex sang asm\n\n"
    "\x1b[1;34m[Compiler]\x1b[0m\n"
    " \x1b[1;32mo!comp <code/file đính kèm>\x1b[0m        Comp asm sang hex\n\n"
    "\x1b[1;34m[Gadget Finder]\x1b[0m\n"
    " \x1b[1;32mo!find_gadget <gadget>\x1b[0m   Tìm gadget liên quan trong disas\n\n"
    "\x1b[1;34m[Translation]\x1b[0m\n"
    " \x1b[1;32mo!vnx2cnx <gadgets>\x1b[0m  Chuyển gadget từ fx580vnx sang fx991cnx\n"
    " \x1b[1;32mo!cnx2vnx <gadgets>\x1b[0m  Chuyển gadget từ fx991cnx sang fx580vnx\n\n"
    "\x1b[1;34m[Conversion]\x1b[0m\n"
    " \x1b[1;32mo!conv_hex <hex>\x1b[0m    Chuyển hex thành token/ký tự\n"
    " \x1b[1;32mo!hex_split <hex>\x1b[0m   Tách chuỗi hex để phân loại vào biến\n"
    " \x1b[1;32mo!p2h <file đính kèm>\x1b[0m  Chuyển hình ảnh đính kèm sang hex\n"
    " \x1b[1;32mo!h2p <hex/file đính kèm>\x1b[0m Chuyển hex sang hình ảnh\n\n"
    "\x1b[1;34m[Generator]\x1b[0m\n"
    " \x1b[1;32mo!talk <prompt>\x1b[0m Nói chuyện với AI\n\n"
    "\x1b[1;34m[General]\x1b[0m\n"
    " \x1b[1;32mo!help\x1b[0m                Hiển thị danh sách lệnh\n"
    " \x1b[1;32mo!usage <lệnh>\x1b[0m        Hiển thị hướng dẫn chi tiết cho một lệnh (không cần gõ o!)\n\n"
    "\x1b[1;37mContribute:\x1b[0m\n"
    "  Created by luongvantam\n"
    "```"
)

usage_dict_vi = {
    "talk": (
        "```o!talk <prompt>```\n"
        "───────────────\n"
        "## Ví dụ:\n"
        "**Input:** `o!talk tính tổng từ 1 đến n bằng python`\n"
        "**Output:**\n"
        "```python\ndef sum_n(n):\n   return sum(range(1, n + 1))\n```"
    ),
    "conv_hex": (
        "```o!conv_hex <hex string>```\n"
        "───────────────\n"
        "## Ví dụ:\n"
        "**Input:** `o!conv_hex 34 7B 31 30 21 21 30 30`\n"
        "**Output:**\n"
        "Token: ```4 cos⁻¹( 1 0 e e 0 0```\n"
        "Char : ```4 { 1 0 ! e 0 0```"
    ),
    "decomp": (
        "```o!decomp <hex string>```\n"
        "───────────────\n"
        "## Cú pháp:\n"
        "- **Bỏ qua:** Đặt 1 chuỗi hex vào bên trong `[` và `]` để bỏ qua decomp nó.\n"
        "- **Địa chỉ ORG:** Ở dòng đầu tiên ta nhập như sau `ADDR <địa chỉ>:` nó sẽ thành `org 0x<địa chỉ>` sau khi decomp.\n"
        "- **Ghi chú:** Đặt 1 đoạn text vào trong `(` và `)` để biến nó thành ghi chú trong đoạn đó.\n"
        "───────────────\n"
        "## Ví dụ 1:\n"
        "**Input:** o!decomp ```34 7B 31 30 30 30 30 30 [7E 94 30 30]```\n\n"
        "**Output:**"
        "```xr0 = hex 30 30 30 30\nhex 7E 94 30 30```\n"
        "## Ví dụ 2:\n"
        "**Input:** o!decomp ```ADDR E9E0: \n34 7B 31 30 30 30 30 30```\n"
        "**Output:**```org 0xE9E0\nxr0 = hex 30 30 30 30```\n"
        "## Ví dụ 3:\n"
        "**Input:** o!decomp ```34 7B 31 30 30 30 (hello)```\n"
        '**Output:**```xr0 = hex 30 30, note "hello"```\n'
        "## Ví dụ 4:\n"
        "**Input:** o!decomp ```(hello) 34 7B 31 30 30 30```\n"
        '**Output:**```note "hello"\nxr0 = hex 30 30```'
    ),
    "vnx2cnx": (
        "```o!vnx2cnx <gadgets>```\n"
        "───────────────\n"
        "## Ví dụ:\n"
        "**Input:** o!vnx2cnx 1:7B34H\n"
        "**Output:** ```1:79BEH	F02E			POP XR0```"
    ),
    "cnx2vnx": (
        "```o!cnx2vnx <gadgets>```\n"
        "───────────────\n"
        "Cách dùng như o!vnx2cnx nhưng ngược lại."
    ),
    "find_gadget": (
        "```o!find_gadget <gadget>```\n"
        "───────────────\n"
        "## Ví dụ:\n"
        "**Input:** o!find_gadget ```\nPOP ER2\nPOP PC\n```"
        "**Output:**```In function memzero:\n0:9D3EH    F21E            POP ER2\n0:9D40H    F28E            POP PC\n...```"
    ),
    "hex_split": (
        "```o!hex_split <hex string>```\n"
        "───────────────\n"
        "## Ví dụ:\n"
        "**Input:** o!hex_split 34 7B 31 30 30 30 30 30 7E 94 30 30\n"
        "**Output:** \n```A = 1. 00 00 94 23\n\nNumber of bytes to assign: 94\nRemaining bytes: 34 7B 31 30 30 30 30 30 7E 30 30 ```"
        "───────────────\n"
        "## Lưu ý: nếu chuỗi hex quá dài (>21 bytes) sẽ báo lỗi."
    ),
    "help": (
        "```o!help```\n"
        "───────────────\n"
        "Hiển thị danh sách lệnh."
    ),
    "info": (
        "```o!info```\n"
        "───────────────\n"
        "Hiển thị thông tin bot (owner only)."
    ),
    "restart": (
        "```o!restart```\n"
        "───────────────\n"
        "Khởi động lại bot (owner only)."
    ),
    "usage": (
        "```o!usage <command>```\n"
        "───────────────\n"
        "Hiển thị hướng dẫn chi tiết của lệnh."
    ),
    "h2p": (
        "```o!h2p <attachment>```\n"
        "───────────────\n"
        "Chuyển hình ảnh thành hex."
    ),
    "p2h": (
        "```o!p2h <hex/attachment>```\n"
        "───────────────\n"
        "Chuyển hex thành hình ảnh."
    ),
    "comp": (
        "```o!comp <code/attachment>```\n"
        "────────────────────────────────\n"
        "[Bạn hãy đọc chi tiết tại đây](https://github.com/luongvantam/RAC-compiler/blob/main/Guide.vi.md)"
    )
}


usage_dict_en = {
    "talk": (
        "```o!talk <prompt>```\n"
        "────────────────────────────────\n"
        "## Example:\n"
        "**Input:** `o!talk sum from 1 to n in python`\n"
        "**Output:**\n"
        "```python\ndef sum_n(n):\n   return sum(range(1, n + 1))\n```"
    ),
    "conv_hex": (
        "```o!conv_hex <hex string>```\n"
        "────────────────────────────────\n"
        "## Example:\n"
        "**Input:** `o!conv_hex 34 7B 31 30 21 21 30 30`\n"
        "**Output:**\n"
        "Token: ```4 cos⁻¹( 1 0 e e 0 0```\n"
        "Char : ```4 { 1 0 ! e 0 0```"
    ),
    "decomp": (
        "```o!decomp <hex string>```\n"
        "────────────────────────────────\n"
        "## Syntax:\n"
        "- **Skip:** Put a hex string inside `[` and `]` to skip decompiling it.\n"
        "- **ORG Address:** On the first line, enter `ADDR <address>:` to make it `org 0x<address>`.\n"
        "- **Note:** Put text inside `(` and `)` to turn it into a comment.\n"
        "────────────────────────────────\n"
        "## Example 1:\n"
        "**Input:** o!decomp ```34 7B 31 30 30 30 30 30 [7E 94 30 30]```\n\n"
        "**Output:**```xr0 = hex 30 30 30 30\nhex 7E 94 30 30```\n"
        "## Example 2:\n"
        "**Input:** o!decomp ```ADDR E9E0:\n34 7B 31 30 30 30 30 30```\n"
        "**Output:**```org 0xE9E0\nxr0 = hex 30 30 30 30```\n"
        "## Example 3:\n"
        "**Input:** o!decomp ```34 7B 31 30 30 30 (hello)```\n"
        "**Output:**```xr0 = hex 30 30, note \"hello\"```\n"
        "## Example 4:\n"
        "**Input:** o!decomp ```(hello) 34 7B 31 30 30 30```\n"
        "**Output:**```note \"hello\"\nxr0 = hex 30 30```"
    ),
    "vnx2cnx": (
        "```o!vnx2cnx <gadgets>```\n"
        "────────────────────────────────\n"
        "## Example:\n"
        "**Input:** `o!vnx2cnx 1:7B34H`\n"
        "**Output:** ```1:79BEH    F02E            POP XR0```"
    ),
    "cnx2vnx": (
        "```o!cnx2vnx <gadgets>```\n"
        "────────────────────────────────\n"
        "Usage is the same as `o!vnx2cnx`, but reversed."
    ),
    "find_gadget": (
        "```o!find_gadget <gadget>```\n"
        "────────────────────────────────\n"
        "## Example:\n"
        "**Input:** o!find_gadget ```\nPOP ER2\nPOP PC\n```\n"
        "**Output:**```In function memzero:\n0:9D3EH    F21E            POP ER2\n0:9D40H    F28E            POP PC\n...```"
    ),
    "hex_split": (
        "```o!hex_split <hex string>```\n"
        "────────────────────────────────\n"
        "## Example:\n"
        "**Input:** `o!hex_split 34 7B 31 30 30 30 30 30 7E 94 30 30`\n"
        "**Output:**\n```A = 1. 00 00 94 23\n\nNumber of bytes to assign: 94\nRemaining bytes: 34 7B 31 30 30 30 30 30 7E 30 30```\n"
        "────────────────────────────────\n"
        "## Note: Input length must not exceed 21 bytes."
    ),
    "help": (
        "```o!help```\n"
        "────────────────────────────────\n"
        "Show the list of available commands."
    ),
    "info": (
        "```o!info```\n"
        "────────────────────────────────\n"
        "Show bot info (owner only)."
    ),
    "restart": (
        "```o!restart```\n"
        "────────────────────────────────\n"
        "Restart the bot (owner only)."
    ),
    "usage": (
        "```o!usage [vi|en] <command>```\n"
        "────────────────────────────────\n"
        "Show detailed usage of a command.\n\n"
        "## Note:\n"
        "- Default language: English\n"
        "- Add `vi` to show Vietnamese usage\n"
        "- Example: `o!usage decomp` or `o!usage vi decomp`"
    ),
    "h2p": (
        "```o!h2p <attachment>```\n"
        "───────────────\n"
        "Convert image to hex."
    ),
    "p2h": (
        "```o!p2h <hex/attachment>```\n"
        "───────────────\n"
        "Convert hex to image."
    ),
    "comp": (
        "```o!comp <code/attachment>```\n"
        "────────────────────────────────\n"
        "[Please read the details here](https://github.com/luongvantam/RAC-compiler/blob/main/Guide.md)"
    )
}