# modules/battery_tracker.py
import datetime
import threading
import os  # 添加os模块导入

class BatteryTracker:
    """
    负责每小时、每日电池计数的管理，以及相应的重置和日志记录。
    """
    def __init__(self, reset_hour):
        # 每小时以 room_id 为 key 的电池统计
        self.hourly_battery_count = {}
        # 每日以 room_id 为 key 的电池统计
        self.daily_battery_count_by_room = {}

        self.last_hour = None
        self.last_reset_day = None

        self.log_base_dir = "data"  # 基础日志目录
        self.reset_hour = reset_hour  # 每天几点重置

        # 提供线程安全锁
        self.lock = threading.Lock()

    def get_log_path(self):
        """
        根据当前日期生成日志文件路径，格式为 data/年/月/日/report.txt
        """
        now = datetime.datetime.now()
        year_dir = str(now.year)
        month_dir = f"{now.month:02d}"  # 补零确保两位数
        day_dir = f"{now.day:02d}"  # 补零确保两位数
        
        log_path = os.path.join(self.log_base_dir, year_dir, month_dir, day_dir, "report.txt")
        return log_path

    def log_data_unlocked(self):
        """
        将当天累计的所有房间日用量记录到日志文件中（可根据需求自由扩展）。
        使用格式: data/年/月/日/report.txt
        """
        now = datetime.datetime.now()
        log_path = self.get_log_path()
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 写入或追加日志内容
        mode = "a" if os.path.exists(log_path) else "w"
        with open(log_path, mode, encoding="utf-8") as log_file:
            log_file.write(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 当日各房间电池用量统计:\n")
            for room_id, used in self.daily_battery_count_by_room.items():
                log_file.write(f"  - 房间 {room_id}: {used} 电池\n")

    def reset_hourly_battery_unlocked(self):
        """
        每个整点重置房间的小时电池计数（不加锁版本，调用者需要先获取锁）
        """
        now = datetime.datetime.now()
        current_hour = now.hour

        if self.last_hour is None or self.last_hour != current_hour:
            self.hourly_battery_count.clear()
            self.last_hour = current_hour

    def reset_daily_battery_unlocked(self):
        """
        每天reset_hour之后重置每日总电池（不加锁版本，调用者需要先获取锁）
        """
        now = datetime.datetime.now()
        current_day = now.day

        if self.last_reset_day is None or self.last_reset_day != current_day:
            # 只有在 >= reset_hour 时才进行重置
            if now.hour >= self.reset_hour:
                # 在重置前记录当天的数据
                self.log_data_unlocked()
                self.daily_battery_count_by_room.clear()
                self.last_reset_day = current_day
