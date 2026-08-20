import time
import sys
from core.manager import CoreManager
from database.repository import InstanceRepository
from cli.status import DashboardRenderer
from config.logging import setup_logger

logger = setup_logger("main")

def main():
    logger.info("Starting Roblox Multi-Instance Network Manager...")
    manager = CoreManager()
    
    try:
        while True:
            # Chạy chu kỳ kiểm tra
            manager.run_check_cycle()
            
            # Lấy danh sách instances mới nhất và render dashboard
            instances = InstanceRepository.get_all_instances()
            DashboardRenderer.render(instances)
            
            # Chờ 3 giây trước lần làm mới tiếp theo
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n[!] Dừng hệ thống Network Manager. Tạm biệt!")
        sys.exit(0)

if __name__ == "__main__":
    main()
