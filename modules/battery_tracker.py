# modules/battery_tracker.py
import datetime
import threading

class BatteryTracker:
    """
    负责每小时、每日电池计数的管理，以及相应的重置和日志记录。
    """
    def __init__(self, log_file, reset_hour):
        # 每小时以 room_id 为 key 的电池统计
        self.hourly_battery_count = {}
        # 每日以 room_id 为 key 的电池统计
        self.daily_battery_count_by_room = {}

        self.last_hour = None
        self.last_reset_day = None

        self.log_file = log_file      # 从配置中获取日志文件路径
        self.reset_hour = reset_hour  # 每天几点重置

        # 提供线程安全锁
        self.lock = threading.Lock()

    def log_data_unlocked(self):
        """
        将当天累计的所有房间日用量记录到日志文件中（可根据需求自由扩展）。
        """
        now = datetime.datetime.now()
        with open(self.log_file, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 当日各房间用量:\n")
            for room_id, used in self.daily_battery_count_by_room.items():
                log_file.write(f"  - room {room_id}: {used}\n")

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
                self.log_data_unlocked()
                self.daily_battery_count_by_room.clear()
                self.last_reset_day = current_day
