import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Database
DB_PATH = DATA_DIR / "network_manager.db"

# Network Monitoring Defaults
DEFAULT_CHECK_INTERVAL_SEC = 5
DEFAULT_PING_TIMEOUT_SEC = 2.0
DEFAULT_DNS_SERVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
TARGET_HOSTS_FOR_PING = [
    "1.1.1.1",
    "8.8.8.8",
    "www.roblox.com"
]

# Health Thresholds
LATENCY_GOOD_MS = 60.0
LATENCY_WARN_MS = 150.0
PACKET_LOSS_WARN_PCT = 5.0

# Proxy & Scrapestack API Configuration
SCRAPESTACK_API_KEY = os.getenv("SCRAPESTACK_API_KEY", "5d1c5fb06ff44e84a97fcc7e2720fd3f")
SCRAPESTACK_BASE_URL = "http://api.scrapestack.com/scrape"
SCRAPESTACK_ENABLED = True
SCRAPESTACK_TIMEOUT_SEC = 8.0

