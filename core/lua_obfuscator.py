# -*- coding: utf-8 -*-
"""
Lua Anti-Theft & Stealth Obfuscation Engine
Mã hóa bảo vệ file Lua tạo ra để chống sao chép / đánh cắp mã nguồn:
1. Stealth Blank View: Khi người dùng mở file bằng Notepad hay Text Editor bất kỳ,
   file hiển thị hoàn toàn trắng tinh / trống rỗng.
2. Dynamic Byte Encryption: Toàn bộ logic mạng và cấu hình IP được mã hóa byte xoay vòng (Byte Shift / XOR).
3. Client Executor Compatibility: Các client như Arceus X, Delta, Codex, Fluxus, Wave, Solara...
   vẫn tự động giải mã trong bộ nhớ RAM và thực thi mượt mà 100%.
"""

import random
from typing import Optional

class LuaObfuscator:
    """Bộ mã hóa và tạo hiệu ứng tàng hình cho file Lua của Roblox"""

    @staticmethod
    def obfuscate_and_stealth(raw_lua_code: str, stealth_padding_lines: int = 350) -> str:
        """
        Mã hóa mã nguồn Lua thành chuỗi byte tự giải mã trong RAM
        và chèn đệm tàng hình để file nhìn như trắng tinh khi mở bình thường.
        """
        # 1. Sinh khóa dịch chuyển byte ngẫu nhiên (13 - 97)
        shift_key = random.randint(17, 89)
        raw_bytes = raw_lua_code.encode("utf-8")
        encrypted_bytes = [(b + shift_key) % 256 for b in raw_bytes]
        
        bytes_joined = ",".join(str(b) for b in encrypted_bytes)

        # 2. Tên biến ngẫu nhiên chống deobfuscate
        var_shift = f"_{random.randint(100, 999)}k"
        var_bytes = f"_{random.randint(100, 999)}d"
        var_chars = f"_{random.randint(100, 999)}s"
        var_idx = f"_{random.randint(100, 999)}i"
        var_runner = f"_{random.randint(100, 999)}x"

        # 3. Trình giải mã siêu nhẹ, tương thích mọi phiên bản Lua/Luau
        runtime_loader = (
            f"local {var_shift}={shift_key};"
            f"local {var_bytes}={{{bytes_joined}}};"
            f"local {var_chars}={{}};"
            f"for {var_idx}=1,#{var_bytes} do "
            f"{var_chars}[{var_idx}]=string.char(({var_bytes}[{var_idx}]-{var_shift}+256)%256) "
            f"end;"
            f"local {var_runner}=loadstring or load;"
            f"if {var_runner} then "
            f"local _f,_e={var_runner}(table.concat({var_chars}));"
            f"if _f then _f() else error(_e) end "
            f"end"
        )

        # 4. Chèn hàng trăm dòng trống (Stealth Padding) ở đầu file
        # Khi mở file bằng Notepad, màn hình sẽ trắng tinh
        stealth_header = "--[[ " + ("\n" * stealth_padding_lines) + " ]]\n"
        
        return stealth_header + runtime_loader
