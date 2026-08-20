class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    # 7 Sắc Cầu Vồng (Rainbow Colors)
    C_RED = "\033[38;5;196m"      # 1. Đỏ
    C_ORANGE = "\033[38;5;208m"   # 2. Cam
    C_YELLOW = "\033[38;5;226m"   # 3. Vàng
    C_GREEN = "\033[38;5;46m"     # 4. Lục
    C_CYAN = "\033[38;5;51m"      # 5. Lam
    C_BLUE = "\033[38;5;39m"      # 6. Chàm
    C_PURPLE = "\033[38;5;141m"   # 7. Tím
    C_MAGENTA = "\033[38;5;201m"  # Hồng cánh sen

    # Backward compatibility
    RED = C_RED
    DARK_RED = "\033[38;5;124m"
    LIGHT_RED = "\033[38;5;203m"
    ORANGE = C_ORANGE
    YELLOW = C_YELLOW
    GREEN = C_GREEN
    LIGHT_GREEN = "\033[38;5;120m"
    CYAN = C_CYAN
    LIGHT_CYAN = "\033[38;5;123m"
    BLUE = C_BLUE
    PURPLE = C_PURPLE
    MAGENTA = C_MAGENTA
    GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"

    RAINBOW = [C_RED, C_ORANGE, C_YELLOW, C_GREEN, C_CYAN, C_BLUE, C_PURPLE]

    @staticmethod
    def rainbow_text(text: str) -> str:
        """Tô 7 màu cầu vồng chuyển sắc mượt mà từng ký tự"""
        palette = [
            "\033[38;5;196m", # Đỏ
            "\033[38;5;202m", # Đỏ cam
            "\033[38;5;208m", # Cam
            "\033[38;5;214m", # Vàng cam
            "\033[38;5;226m", # Vàng
            "\033[38;5;118m", # Lục sáng
            "\033[38;5;46m",  # Lục
            "\033[38;5;49m",  # Xanh ngọc
            "\033[38;5;51m",  # Lam
            "\033[38;5;39m",  # Xanh dương
            "\033[38;5;69m",  # Chàm
            "\033[38;5;141m", # Tím
            "\033[38;5;201m", # Hồng
        ]
        result = []
        for i, char in enumerate(text):
            if char in [" ", "\n", "\t"]:
                result.append(char)
            else:
                color = palette[i % len(palette)]
                result.append(f"{color}{char}")
        result.append(Colors.RESET)
        return "".join(result)

    @staticmethod
    def colorize_status(status: str) -> str:
        if status == "ONLINE":
            return f"{Colors.GREEN}{Colors.BOLD}ONLINE{Colors.RESET}"
        elif status == "DEGRADED":
            return f"{Colors.YELLOW}{Colors.BOLD}DEGRADED{Colors.RESET}"
        else:
            return f"{Colors.RED}{Colors.BOLD}OFFLINE{Colors.RESET}"
