import json
import os

class RoomConfigManager:
    def __init__(self, room_config_path="room_id_config.json", global_config=None):
        """
        :param room_config_path: 存储room_id的配置文件
        :param global_config: 全局配置字典，用来初始化默认值
        """
        self.room_config_path = room_config_path
        self.global_config = global_config  # 用于获取 max_hourly_battery_per_room / max_daily_battery
        # 如果文件不存在则创建空文件
        if not os.path.exists(self.room_config_path):
            with open(self.room_config_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4, ensure_ascii=False)

        # 读取已有配置
        with open(self.room_config_path, "r", encoding="utf-8") as f:
            self.room_config = json.load(f)

    def save_room_config(self):
        """
        保存 room_config
        """
        with open(self.room_config_path, "w", encoding="utf-8") as f:
            json.dump(self.room_config, f, indent=4, ensure_ascii=False)

    def get_room_limits(self, room_id):
        """
        获取指定房间的 (max_hourly_battery, max_daily_battery)。
        如果尚未定义，则写入默认值并保存。
        """
        if room_id not in self.room_config:
            self.room_config[room_id] = {
                "max_hourly_battery": self.global_config["max_hourly_battery_per_room"],
                "max_daily_battery": self.global_config["max_daily_battery"]
            }
            self.save_room_config()

        return (
            self.room_config[room_id]["max_hourly_battery"],
            self.room_config[room_id]["max_daily_battery"]
        )
