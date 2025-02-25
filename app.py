from flask import Flask, request, jsonify
import traceback
import re
import datetime

# 假设这些模块都在 modules/ 下
from modules.config_loader import ConfigLoader
from modules.room_config_manager import RoomConfigManager
from modules.battery_tracker import BatteryTracker
from modules.gift_sender import GiftSender
from modules.danmaku_sender import DanmakuSender


class DanmakuGiftApp:
    def __init__(self, config_path="config.json", room_config_path="room_id_config.json"):
        # 初始化 Flask
        self.app = Flask(__name__)

        # ---------- 初始化配置 ----------
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.get_config()

        # ---------- 初始化房间配置管理 ----------
        self.room_config_manager = RoomConfigManager(room_config_path, self.config)

        # ---------- 初始化电池统计管理 ----------
        self.battery_tracker = BatteryTracker(
            log_file=self.config["log_file"],
            reset_hour=self.config["reset_hour"]
        )

        # ---------- 初始化礼物发送器 ----------
        self.gift_sender = GiftSender("./missions/send_gift")

        # 注册路由
        self.register_routes()

    def register_routes(self):
        self.app.add_url_rule('/ticket', view_func=self.process_ticket, methods=['POST'])
        self.app.add_url_rule('/pk_wanzun', view_func=self.handle_pk_wanzun, methods=['POST'])

    @staticmethod
    def generate_target_number(power: int):
        """
        计算 (月 + 日 + 时)^power 的结果，并取最后 4 位
        """
        now = datetime.datetime.now()
        sum_value = now.month + now.day + now.hour
        computed_value = sum_value ** power
        return str(computed_value % 10000)

    def process_ticket(self):
        gift_id = "33988"  # 固定礼物ID
        print(f"[DEBUG] Received ticket request: {request.json}")
        try:
            data = request.json
            if not data or 'room_id' not in data or 'danmaku' not in data:
                return jsonify({"error": "Invalid request, missing 'room_id' or 'danmaku'"}), 400

            room_id = str(data['room_id'])
            danmaku = data['danmaku']
            notifee = DanmakuSender()

            # ---------- 根据弹幕关键字决定业务逻辑 ----------
            if "全境" in danmaku:
                power = 16
                is_special_all = True
            else:
                is_special_all = False
                if "泰坦" in danmaku:
                    power = 8
                    num = 100
                    account = "titan"
                elif "强袭" in danmaku:
                    power = 4
                    num = 10
                    account = "striker"
                else:
                    power = 2
                    num = 1
                    account = "ghost"

            # ---------- 计算密码并校验 ----------
            target_number = self.generate_target_number(power)
            print(f"[DEBUG] 计算得到的密码: {target_number}")

            if not re.search(target_number, danmaku):
                msg = f"danmaku 不包含 {target_number}, 无法触发脚本"
                notifee.send_danmaku(room_id, "口令错误！")
                print(f"[DEBUG] {msg}")
                return jsonify({"status": "failed", "reason": msg}), 400

            # ---------- 检查并更新电池用量 ----------
            with self.battery_tracker.lock:
                # 可能在整点或跨日时需要重置
                self.battery_tracker.reset_hourly_battery_unlocked()
                self.battery_tracker.reset_daily_battery_unlocked()

                max_hourly, max_daily = self.room_config_manager.get_room_limits(room_id)
                room_hourly_used = self.battery_tracker.hourly_battery_count.get(room_id, 0)
                room_daily_used = self.battery_tracker.daily_battery_count_by_room.get(room_id, 0)

                if is_special_all:
                    # 特殊逻辑：分发给三个账号
                    num_each = min(max_hourly // 3, 100)
                    total_need = num_each * 3

                    if room_hourly_used + total_need > max_hourly:
                        msg = f"房间 {room_id} 小时电池超上限 (已用:{room_hourly_used}, 计划:{total_need}, 上限:{max_hourly})"
                        print(f"[DEBUG] {msg}")
                        notifee.send_danmaku(room_id, f"小时配额上限！{room_hourly_used + total_need}/{max_hourly}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    if room_daily_used + total_need > max_daily:
                        msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{total_need}, 上限:{max_daily})"
                        print(f"[DEBUG] {msg}")
                        notifee.send_danmaku(room_id, f"当日配额上限！{room_daily_used + total_need}/{max_daily}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + total_need
                    self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + total_need

                    print(f"[DEBUG] [全境] 房间 {room_id} 更新用量：小时 {room_hourly_used+total_need}/{max_hourly}, 日 {room_daily_used+total_need}/{max_daily}")
                else:
                    if room_hourly_used + num > max_hourly:
                        msg = f"房间 {room_id} 小时电池超上限 (已用:{room_hourly_used}, 计划:{num}, 上限:{max_hourly})"
                        print(f"[DEBUG] {msg}")
                        notifee.send_danmaku(room_id, f"小时配额上限！{room_hourly_used}/{max_hourly}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    if room_daily_used + num > max_daily:
                        msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{num}, 上限:{max_daily})"
                        print(f"[DEBUG] {msg}")
                        notifee.send_danmaku(room_id, f"当日配额上限！{room_daily_used}/{max_daily}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + num
                    self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + num

                    print(f"[DEBUG] 房间 {room_id} 更新用量：小时 {room_hourly_used+num}/{max_hourly}, 日 {room_daily_used+num}/{max_daily}")
            
            # ---------- 发送礼物 ----------
            if is_special_all:
                num_each = min(max_hourly // 3, 100)
                accounts = ["titan", "striker", "ghost"]
                for acc in accounts:
                    self.gift_sender.send_gift(room_id, num_each, acc, gift_id)
                return jsonify({"status": "success", "message": "Gift sent successfully (全境)"}), 200
            else:
                self.gift_sender.send_gift(room_id, num, account, gift_id)
                return jsonify({"status": "success", "message": "Gift sent successfully"}), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": "Server error", "details": str(e)}), 500

    def handle_pk_wanzun(self):
        gift_id = "33988"  # 固定礼物ID
        data = request.json

        room_id = data.get("room_id")
        pk_data = data.get("pk_battle_process_new")
        token = data.get("token")
        print(f"[DEBUG] PK_BATTLE_PROCESS_NEW: {room_id}, {pk_data}, {token}")

        if not room_id or token != "8096":
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        room_id = str(data['room_id'])
        notifee = DanmakuSender()
        account = "ghost"

        with self.battery_tracker.lock:
            self.battery_tracker.reset_hourly_battery_unlocked()
            self.battery_tracker.reset_daily_battery_unlocked()

            max_hourly, max_daily = self.room_config_manager.get_room_limits(room_id)
            room_hourly_used = self.battery_tracker.hourly_battery_count.get(room_id, 0)
            room_daily_used = self.battery_tracker.daily_battery_count_by_room.get(room_id, 0)
            num = 1

            if room_hourly_used + num > max_hourly:
                msg = f"房间 {room_id} 小时电池超上限 (已用:{room_hourly_used}, 计划:{num}, 上限:{max_hourly})"
                print(f"[DEBUG] {msg}")
                notifee.send_danmaku(room_id, f"小时配额上限！{room_hourly_used}/{max_hourly}")
                return jsonify({"status": "failed", "reason": msg}), 400

            if room_daily_used + num > max_daily:
                msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{num}, 上限:{max_daily})"
                print(f"[DEBUG] {msg}")
                notifee.send_danmaku(room_id, f"当日配额上限！{room_daily_used}/{max_daily}")
                return jsonify({"status": "failed", "reason": msg}), 400

            self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + num
            self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + num

            print(f"[DEBUG] 房间 {room_id} 更新用量：小时 {room_hourly_used+num}/{max_hourly}, 日 {room_daily_used+num}/{max_daily}")

        try:
            self.gift_sender.send_gift(room_id, num, account, gift_id)
            return jsonify({"status": "success", "message": "Gift sent successfully"}), 200
        except TimeoutError:
            return jsonify({"error": "Failed to send gift (timeout)"}), 500
        except RuntimeError as e:
            return jsonify({"error": f"Failed to send gift: {str(e)}"}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": "Unknown error in subprocess", "details": str(e)}), 500

    def run(self, host='0.0.0.0', port=8081, debug=True):
        self.app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    app_instance = DanmakuGiftApp()
    app_instance.run()
else:
    # 当被 gunicorn 等 WSGI 服务器导入时，提供全局的 app 对象
    app_instance = DanmakuGiftApp()
    app = app_instance.app
