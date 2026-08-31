# ⚡ ROBLOX MULTI-TAG NETWORK CONTROLLER & WATCHDOG SUPERVISOR ⚡
> Repository: `https://github.com/hyuttgg/tool-python-roblox-ip`

Hệ thống điều khiển mạng đa tiến trình chuyên nghiệp cho Roblox (Windows PC / Android / Termux / Giả lập / Cloud Phone):
- **Độc lập 100%**: Mỗi Tag nhận 1 IP, 1 HWID, 1 MAC, 1 Client-UUID, 1 User-Agent và 1 cặp DNS riêng biệt.
- **Nhúng sâu Java vào Python**: Tích hợp thuật toán Selection Sort Engine và Java Deep Network Engine (TCP Handshake & Socket Ping) cho độ trễ thấp nhất.
- **Roblox Game Selector & Auto-Join Hub**: Tích hợp danh sách game hot (Blox Fruits, King Legacy, PS99, Fisch, Blade Ball, MM2...) + hỗ trợ nhập Place ID / Job ID / VIP Server để mở thẳng vào game.
- **Tiêm Lua Heartbeat & Bắt lỗi Disconnect**: Mã Lua gửi nhịp tim định kỳ mỗi 2.5s và tự động bắt lỗi (Error 277, 268, Kicked, Teleport Failed).
- **Auto-Restart Watchdog (Tự động mở lại Tag khi bị tắt)**: Python Watchdog chạy nền tự động phát hiện cửa sổ bị tắt hoặc mất kết nối, lập tức khởi động lại và đưa đúng vào game mục tiêu với Dedicated IP riêng!

---

## 🚀 CÀI ĐẶT NHANH (ĐÚNG 2 LỆNH SHELL)

Mở Termux và dán 2 lệnh sau:

### 1️⃣ Lệnh 1: Cài đặt Tool 1-chạm
```bash
curl -sL https://raw.githubusercontent.com/hyuttgg/tool-python-roblox-ip/main/setup.sh | bash
```

### 2️⃣ Lệnh 2: Khởi chạy Tool (Bộ não duy nhất controller.py)
```bash
run
```
*(Hoặc dùng lệnh `rejoin` / `python controller.py`)*


---

## 💡 CÁC CÁCH CHẠY BỔ SUNG

### Cách 1: Chạy trên máy tính (PC / Windows / Linux)
```bash
python controller.py
```

### Cách 2: Chạy bằng lệnh tắt nhanh (Termux)
```bash
roblox-ip
```

### Cách 3: Chạy trực tiếp qua Script Runner
```bash
cd /sdcard/Download/tool-python-roblox-ip && bash run.sh
```

### Cách 4: Chạy Dashboard giám sát trực tiếp (Live Monitor)
```bash
python main.py
```

---

## 🎮 DANH MỤC 4 TRỤ CỘT TÍNH NĂNG NHẤT QUÁN & MASTER PIPELINE

```text
► [ TRỤ CỘT 1: ĐIỀU PHỐI, CHỌN GAME & KHỞI CHẠY 1-CHẠM ]
  [1]  🚀 FULL AUTO PIPELINE (1-Chạm: Quét + Sort IP Java + Bơm Autoexec + Launch + Watchdog)
  [2]  🎮 Cấu hình Game Roblox & Teleport Hub (Global hoặc Mỗi Tag 1 Game riêng)
  [3]  🛡️ Giám sát & Bật/Tắt Auto-Restart Watchdog (Tự động mở lại Tag khi văng/tắt)
  [4]  📊 Khởi chạy Live Dashboard Giám sát Real-Time (FPS, Ping, RAM chu kỳ 3s)

► [ TRỤ CỘT 2: TỐI ƯU MẠNG & THUẬT TOÁN JAVA ENGINE ]
  [5]  ⚡ Java Selection Sort Engine (Sắp xếp IP theo Ping thấp nhất trên JVM JRE 8)
  [6]  🔄 Cấp phát & Đổi dải IP Proxy Đa Quốc Gia (VN, JP, SG, HK, US, DE...)
  [7]  🌐 Quản lý Pool IP, ProxyScrape & Scrapestack API (5d1c5fb0...)
  [8]  🔍 Chẩn đoán mạng chuyên sâu (Java Handshake, Socket Ping, DNS, MTU)

► [ TRỤ CỘT 3: SCRIPT GAME & ĐỒNG BỘ AUTOEXEC ]
  [9]  📝 Cấu hình Script Game (Auto Farm Payload) tự động chạy cho mọi Tag
  [10] 📁 Quản lý & Đồng bộ thư mục Autoexec (Delta, Arceus X, Solara, Wave, Codex)
  [11] 📋 Xem Bảng Tổng Hợp Chi Tiết Tag (IP + Game + HWID + Status + PID)

► [ TRỤ CỘT 4: BẢO TRÌ & HỆ THỐNG ]
  [12] 🧹 Dọn dẹp Cache, Reset Autoexec, Script Lua & Khởi động lại Server
  [0]  ❌ Thoát chương trình an toàn
```

---

## 📁 Cấu trúc thư mục

```text
├── SetupRobloxIP              # Script cài đặt 1 chạm nhanh cho Android / Termux
├── run.sh                     # Trình điều khiển CLI Runner trung tâm
├── controller.py              # MASTER CONTROLLER: Menu điều khiển trung tâm toàn bộ tool
├── main.py                    # Entrypoint chạy trực tiếp Live Dashboard
├── requirements.txt           # Danh sách thư viện Python yêu cầu
├── config/
│   ├── settings.py            # Cấu hình chung, timeouts, paths
│   ├── devices.py             # Khai báo loại thiết bị & cấu hình Region (Japan, HK, SG, VN)
│   ├── profiles.py            # Định nghĩa cấu hình network profiles
│   └── logging.py             # Cấu hình Logger & log rotation
├── database/
│   ├── sqlite.py              # SQLite Connection Manager & Auto Migrations
│   ├── models.py              # Cấu trúc bảng (Instances, Snapshots, Events)
│   └── repository.py          # CRUD operations & Query helpers
├── core/
│   ├── game_selector.py       # Quản lý danh bạ game Roblox, Place ID, URI generator
│   ├── watchdog_supervisor.py # Daemon giám sát Heartbeat & tự động mở lại Tag bị tắt
│   ├── java_sort_bridge.py    # Cầu nối Java Engine (Selection Sort & Network Prober)
│   ├── SelectionSortEngine.java # Thuật toán Selection Sort Java hiệu năng cao
│   ├── autoexec_manager.py    # Tự động nạp script vào Autoexec folders
│   ├── clone_scanner.py       # Quét bản clone / giả lập trên ổ đĩa
│   ├── lua_generator.py       # Sinh script Lua độc lập, Heartbeat & Error Hook
│   └── scanner.py             # Quét cửa sổ và tiến trình Roblox thực tế
├── network/
│   ├── deep_interceptor.py    # Module can thiệp sâu DNS/IP (Sing-Box Wintun TUN & Android IPTables TPROXY)
│   ├── bridge_server.py       # Local HTTP Bridge Server (Heartbeat, Tag Status, Target Game)
│   ├── proxy_fetcher.py       # Tải Live Proxy đa quốc gia
│   ├── scrapestack_client.py  # Kết nối Scrapestack Proxy API
│   ├── connectivity.py        # Kiểm tra Public IP & kết nối
│   └── dns.py                 # Phân giải DNS & đo thời gian query
└── tests/
    ├── test_deep_interceptor.py # Test suite kiểm thử can thiệp mạng sâu (Windows & Android)
    └── test_all.py            # Test suite tự động kiểm thử toàn bộ hệ thống
```

---

## 🛡️ CAN THIỆP MẠNG SÂU (DEEP NETWORK & DNS INTERCEPTION)

1. **Windows PC (Wintun & Sing-Box TUN Engine)**:
   - Tự động sinh file cấu hình chuẩn `sing-box` TUN mode (`data/singbox_roblox_config.json`).
   - Định tuyến Per-Process: Chỉ chuyển hướng luồng mạng của `RobloxPlayerBeta.exe`, `Bloxstrap.exe` qua Proxy/DNS riêng biệt, các app khác đi Direct.
   - Hỗ trợ cơ chế **DNS Fake-IP** (`198.18.0.0/15`) và **DoH / DoT** chống rò rỉ DNS 100%.

2. **Android / Giả lập / Cloud Phone (Stealth TPROXY & IPTables Engine)**:
   - Tự động nhận diện UID của app `com.roblox.client` qua Android ADB.
   - Bơm các quy tắc `iptables` / `nftables` TPROXY chuyển hướng toàn bộ TCP và DNS Port 53 sang Proxy mà **hoàn toàn không hiện icon VPN** trên thanh thông báo.
   - Hỗ trợ khôi phục mạng gốc an toàn 1-chạm khi ngắt kết nối.

