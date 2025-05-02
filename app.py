from flask import Flask, request, jsonify
import traceback
import re
import datetime
import os
import threading
import subprocess
import json
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import time

from modules.config_loader import ConfigLoader
from modules.room_config_manager import RoomConfigManager
from modules.battery_tracker import BatteryTracker
from modules.gift_sender import GiftSender
from modules.danmaku_sender import DanmakuSender
from modules.like_sender import LikeSender
from modules.db_handler import DBHandler
from modules.gift_api import gift_api_bp
from modules.logger import get_logger, debug, info, warning, error, critical
from tools.init_db import init_database
from modules.chatbot import ChatbotHandler

# 强制设置环境变量为UTC时区
os.environ['TZ'] = 'UTC'
try:
    time.tzset()  # 重置时区设置，仅在Unix系统有效
except AttributeError:
    # Windows系统不支持tzset
    pass

class DanmakuGiftApp:
    def __init__(self, config_path="config.json", room_config_path="room_id_config.json", table_name="gift_records", log_file=None, log_level=None):
        # 初始化 Flask
        self.app = Flask(__name__)

        # 加载环境变量
        env_path = "missions/.env"
        load_dotenv(env_path)
        
        # 设置环境变量供API模块使用
        os.environ['GIFT_ENV_PATH'] = env_path
        
        # 设置Flask配置
        self.app.config['GIFT_TABLE_NAME'] = table_name

        # ---------- 初始化配置 ----------
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.get_config()
        
        # 确保配置中不包含已移除的log_file配置项
        if "log_file" in self.config:
            del self.config["log_file"]

        # ---------- 初始化房间配置管理 ----------
        self.room_config_manager = RoomConfigManager(room_config_path, self.config)

        # ---------- 初始化电池统计管理 ----------
        self.battery_tracker = BatteryTracker(
            reset_hour=self.config["reset_hour"]
        )

        # ---------- 初始化礼物发送器 ----------
        self.gift_sender = GiftSender("./missions/send_gift")
        
        # ---------- 初始化礼物记录数据库 ----------
        self.table_name = table_name
        # 确保表存在但不强制重建
        init_database(env_path, table_name, drop_existing=False)
        
        # ---------- 初始化数据库处理器 ----------
        self.db_handler = DBHandler(env_path, table_name)
        
        # ---------- 注册蓝图 ----------
        self.app.register_blueprint(gift_api_bp)

        # 初始化chatbot处理器
        self.chatbot_handler = ChatbotHandler(env_path="missions/.env")

        # 注册路由
        self.register_routes()
        
        info(f"Gift API endpoints registered successfully (table: {table_name})")

    def _get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )

    def register_routes(self):
        self.app.add_url_rule('/ticket', view_func=self.process_ticket, methods=['POST'])
        self.app.add_url_rule('/pk_wanzun', view_func=self.handle_pk_wanzun, methods=['POST'])
        self.app.add_url_rule('/live_room_spider', view_func=self.start_live_room_spider, methods=['POST'])
        self.app.add_url_rule('/money', view_func=self.handle_money, methods=['POST'])
        self.app.add_url_rule('/setting', view_func=self.handle_setting, methods=['POST'])
        self.app.add_url_rule('/chatbot', view_func=self.handle_chatbot, methods=['POST'])
        self.app.add_url_rule('/sendlike', view_func=self.handle_sendlike, methods=['POST'])

    def handle_money(self):
        """
        处理来自直播间的礼物记录，并按时间顺序存储
        期望的请求格式：
        {
            "room_id": "房间ID",
            "uid": 用户ID,
            "uname": "用户名",
            "gift_id": 礼物ID,
            "gift_name": "礼物名称",
            "price": 礼物价格
        }
        """
        try:
            debug(f"Received money request: {request.json}")
            data = request.json
            
            # 验证必要字段
            required_fields = ["room_id", "uid", "uname", "gift_id", "gift_name", "price"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            # 使用 DBHandler 保存记录
            record_id = self.db_handler.add_gift_record(
                room_id=data["room_id"],
                uid=data["uid"],
                uname=data["uname"],
                gift_id=data["gift_id"],
                gift_name=data["gift_name"],
                price=data["price"]
            )
            
            info(f"Gift record saved with ID: {record_id}, from user: {data['uname']}, gift: {data['gift_name']}")
            
            return jsonify({
                "status": "success", 
                "message": "Gift record saved successfully",
                "record_id": record_id
            }), 200
            
        except psycopg2.Error as e:
            error(f"Database error: {e}")
            traceback.print_exc()
            return jsonify({"error": "Database error", "details": str(e)}), 500
        except Exception as e:
            error(f"Server error: {e}")
            traceback.print_exc()
            return jsonify({"error": "Server error", "details": str(e)}), 500
    
    @staticmethod
    def generate_target_number(power: int):
        """
        计算 (月 + 日 + 时)^power 的结果，并取最后 4 位
        使用UTC时间计算
        """
        # 打印系统当前时间信息用于调试
        local_time = datetime.datetime.now()
        debug(f"系统本地时间: {local_time}")
        
        # 打印原始utcnow结果用于比较
        utc_naive = datetime.datetime.utcnow()
        debug(f"原始utcnow时间: {utc_naive}")
        
        try:
            # Python 3.11+ 方式
            now = datetime.datetime.now(datetime.UTC)
        except AttributeError:
            # 旧版本 Python 兼容方式 - 使用 timezone 确保是真正的 UTC
            now = datetime.datetime.now(datetime.timezone.utc)
        
        # 打印当前使用的 UTC 时间进行调试
        debug(f"当前使用的UTC时间: {now}, tzinfo={now.tzinfo}")
        debug(f"时间差异对比: 本地时间小时={local_time.hour}, UTC时间小时={now.hour}, 差异={(local_time.hour - now.hour) % 24}小时")
        
        sum_value = now.month + now.day + now.hour
        debug(f"计算基础值: 月({now.month}) + 日({now.day}) + 时({now.hour}) = {sum_value}")
        
        computed_value = sum_value ** power
        debug(f"计算结果: {sum_value}^{power} = {computed_value}")
        
        result = str(computed_value % 10000)
        debug(f"最终密码: {result}")
        
        return result

    def process_ticket(self):
        gift_id = "33988"  # 固定礼物ID
        debug(f"Received ticket request: {request.json}")
        try:
            data = request.json
            if not data or 'room_id' not in data or 'danmaku' not in data:
                return jsonify({"error": "Invalid request, missing 'room_id' or 'danmaku'"}), 400

            room_id = str(data['room_id'])
            danmaku = data['danmaku']
            notifee = DanmakuSender()

            # ---------- 根据弹幕关键字决定业务逻辑 ----------
            if "全境" in danmaku:
                power = 5
                is_special_all = True
            else:
                is_special_all = False
                if "急急急" in danmaku:
                    power = 6
                    num = 1
                    account = "sentry"
                elif "泰坦" in danmaku:
                    power = 4
                    num = 100
                    account = "titan"
                elif "强袭" in danmaku:
                    power = 3
                    num = 10
                    account = "striker"
                else:
                    power = 2
                    num = 1
                    account = "ghost"

            # ---------- 计算密码并校验 ----------
            target_number = self.generate_target_number(power)
            debug(f"计算得到的密码: {target_number}")

            if not re.search(target_number, danmaku):
                try:
                    # Python 3.11+ 方式
                    now = datetime.datetime.now(datetime.UTC)
                except AttributeError:
                    # 旧版本 Python 兼容方式 - 使用 timezone 确保是真正的 UTC
                    now = datetime.datetime.now(datetime.timezone.utc)
                sum_value = now.month + now.day + now.hour
                msg = f"密码错误! 弹幕 '{danmaku}' 不包含正确密码 {target_number}，无法触发脚本。UTC时间：{now}，基础值：{sum_value}，幂次：{power}"
                error(msg)  # 使用error级别确保一定会打印
                notifee.send_danmaku(room_id, "喵喵喵！喵！")
                debug(msg)
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
                    # 特殊逻辑：计算剩余可用额度，分发给三个账号
                    remaining_hourly = max_hourly - room_hourly_used
                    num_each = max(1, remaining_hourly // 3)  # 每个账号至少分配1个，否则平均分配
                    total_need = num_each * 3  # 总共需要的电池数量

                    if total_need <= 0:
                        msg = f"房间 {room_id} 小时电池已用完 (已用:{room_hourly_used}, 上限:{max_hourly})"
                        debug(msg)
                        notifee.send_danmaku(room_id, f"喵喵，小时电池已用完喵")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    if room_daily_used + total_need > max_daily:
                        msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{total_need}, 上限:{max_daily})"
                        debug(msg)
                        notifee.send_danmaku(room_id, f"喵喵，天{room_daily_used + total_need}喵{max_daily}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + total_need
                    self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + total_need

                    debug(f"[全境] 房间 {room_id} 更新用量：小时 {room_hourly_used+total_need}/{max_hourly}, 日 {room_daily_used+total_need}/{max_daily}, 每个账号分配 {num_each} 个")
                else:
                    if room_hourly_used + num > max_hourly:
                        msg = f"房间 {room_id} 小时电池超上限 (已用:{room_hourly_used}, 计划:{num}, 上限:{max_hourly})"
                        debug(msg)
                        notifee.send_danmaku(room_id, f"喵喵，小时{room_hourly_used}喵{max_hourly}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    if room_daily_used + num > max_daily:
                        msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{num}, 上限:{max_daily})"
                        debug(msg)
                        notifee.send_danmaku(room_id, f"喵喵，天{room_daily_used}喵{max_daily}")
                        return jsonify({"status": "failed", "reason": msg}), 400

                    self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + num
                    self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + num

                    debug(f"房间 {room_id} 更新用量：小时 {room_hourly_used+num}/{max_hourly}, 日 {room_daily_used+num}/{max_daily}")
            
            # ---------- 发送礼物 ----------
            if is_special_all:
                # 获取当前可用电池，平均分配给三个账号
                accounts = ["titan", "striker", "ghost"]
                for acc in accounts:
                    self.gift_sender.send_gift(room_id, num_each, acc, gift_id)
                return jsonify({"status": "success", "message": f"Gift sent successfully (全境), 每账号 {num_each} 个"}), 200
            else:
                self.gift_sender.send_gift(room_id, num, account, gift_id)
                return jsonify({"status": "success", "message": "Gift sent successfully"}), 200

        except Exception as e:
            error(f"处理ticket请求失败: {e}")
            traceback.print_exc()
            return jsonify({"error": "Server error", "details": str(e)}), 500

    def handle_pk_wanzun(self):
        gift_id = "33988"  # 固定礼物ID
        data = request.json

        room_id = data.get("room_id")
        pk_data = data.get("pk_battle_process_new")
        token = data.get("token")
        debug(f"PK_BATTLE_PROCESS_NEW: {room_id}, {pk_data}, {token}")

        if not room_id or token != "8096":
            return jsonify({"status": "error", "message": "Invalid data"}), 400

        room_id = str(data['room_id'])
        notifee = DanmakuSender()
        account = "ghost"
        
        # 检查房间是否开启了加强模式
        youxiao = self.room_config_manager.get_room_youxiao(room_id)
        # 根据房间状态决定礼物数量
        num = 10 if youxiao else 1

        with self.battery_tracker.lock:
            self.battery_tracker.reset_hourly_battery_unlocked()
            self.battery_tracker.reset_daily_battery_unlocked()

            max_hourly, max_daily = self.room_config_manager.get_room_limits(room_id)
            room_hourly_used = self.battery_tracker.hourly_battery_count.get(room_id, 0)
            room_daily_used = self.battery_tracker.daily_battery_count_by_room.get(room_id, 0)

            if room_hourly_used + num > max_hourly:
                msg = f"房间 {room_id} 小时电池超上限 (已用:{room_hourly_used}, 计划:{num}, 上限:{max_hourly})"
                debug(msg)
                notifee.send_danmaku(room_id, f"喵喵，小时{room_hourly_used}喵{max_hourly}")
                return jsonify({"status": "failed", "reason": msg}), 400

            if room_daily_used + num > max_daily:
                msg = f"房间 {room_id} 日电池超上限 (已用:{room_daily_used}, 计划:{num}, 上限:{max_daily})"
                debug(msg)
                notifee.send_danmaku(room_id, f"喵喵，天{room_daily_used}喵{max_daily}")
                return jsonify({"status": "failed", "reason": msg}), 400

            self.battery_tracker.hourly_battery_count[room_id] = room_hourly_used + num
            self.battery_tracker.daily_battery_count_by_room[room_id] = room_daily_used + num

            debug(f"房间 {room_id} 更新用量：小时 {room_hourly_used+num}/{max_hourly}, 日 {room_daily_used+num}/{max_daily}, 加强模式: {youxiao}")

        try:
            self.gift_sender.send_gift(room_id, num, account, gift_id)
            return jsonify({"status": "success", "message": "Gift sent successfully"}), 200
        except TimeoutError:
            error("Failed to send gift (timeout)")
            return jsonify({"error": "Failed to send gift (timeout)"}), 500
        except RuntimeError as e:
            error(f"Failed to send gift: {str(e)}")
            return jsonify({"error": f"Failed to send gift: {str(e)}"}), 500
        except Exception as e:
            error(f"Unknown error in subprocess: {e}")
            traceback.print_exc()
            return jsonify({"error": "Unknown error in subprocess", "details": str(e)}), 500

    def start_live_room_spider(self):
        """
        API endpoint to start a Bilibili live room spider with the provided room IDs.
        接受两种格式的请求:
        1. {"room_ids": [房间ID列表]}
        2. {"room_id": 房间ID, "stop_live_room_list": 包含房间ID的数据}
        """
        try:
            debug(f"Received live_room_spider request: {request.json}")
            data = request.json
            
            # 处理第一种格式：直接提供room_ids列表
            if data and 'room_ids' in data and isinstance(data['room_ids'], list):
                room_ids = data['room_ids']
            # 处理第二种格式：提供room_id和stop_live_room_list
            elif data and 'room_id' in data and 'stop_live_room_list' in data:
                # 从stop_live_room_list中提取房间ID
                stop_live_rooms = data.get('stop_live_room_list', {})
                debug(f"Extracted stop_live_room_list: {stop_live_rooms}")
                
                # 如果stop_live_room_list是字典，我们尝试从中提取房间ID列表
                if isinstance(stop_live_rooms, dict):
                    # 假设stop_live_room_list的内容是以房间ID为键的字典
                    # 或者包含房间ID列表的字段
                    room_ids = []
                    
                    # 特别检查room_id_list字段（根据日志输出发现的关键字段）
                    if 'room_id_list' in stop_live_rooms and isinstance(stop_live_rooms['room_id_list'], list):
                        room_ids = stop_live_rooms['room_id_list']
                        debug(f"Found room_ids in 'room_id_list' field: {room_ids}")
                    # 尝试其他可能的数据结构
                    elif 'room_ids' in stop_live_rooms and isinstance(stop_live_rooms['room_ids'], list):
                        room_ids = stop_live_rooms['room_ids']
                    elif 'list' in stop_live_rooms and isinstance(stop_live_rooms['list'], list):
                        room_ids = stop_live_rooms['list']
                    else:
                        # 只有在无法找到任何房间ID列表字段时，才尝试使用键
                        try_keys = list(stop_live_rooms.keys())
                        # 检查键是否都是数字（即可能是房间ID）
                        if all(str(k).isdigit() for k in try_keys):
                            room_ids = try_keys
                        
                    debug(f"Extracted room_ids from stop_live_room_list: {room_ids[:5]}{'...' if len(room_ids) > 5 else ''} (total: {len(room_ids)})")
                
                # 如果stop_live_room_list已经是列表，直接使用
                elif isinstance(stop_live_rooms, list):
                    room_ids = stop_live_rooms
                else:
                    # 如果无法从数据中提取房间ID，使用请求中的room_id
                    room_ids = [data['room_id']]
            else:
                debug(f"Invalid request format: {data}")
                return jsonify({"error": "Invalid request format, expected 'room_ids' list or 'room_id' with 'stop_live_room_list'"}), 400
            
            # 确保room_ids不为空
            if not room_ids:
                return jsonify({"error": "No room IDs provided"}), 400
            
            # 移除可能的非整数ID
            room_ids = [room_id for room_id in room_ids if str(room_id).isdigit()]
            
            # 再次检查是否有有效的房间ID
            if not room_ids:
                return jsonify({"error": "No valid room IDs found"}), 400
            
            # Format the room_ids as a string for the spider command
            room_ids_str = json.dumps(room_ids)
            
            # Create a thread to run the spider
            spider_thread = threading.Thread(
                target=self._run_spider_command,
                args=(room_ids_str,),
                daemon=True
            )
            spider_thread.start()
            
            return jsonify({
                "status": "success", 
                "message": f"Spider started for {len(room_ids)} room(s)",
                "room_ids": room_ids
            }), 200
            
        except Exception as e:
            error(f"启动爬虫失败: {e}")
            traceback.print_exc()
            return jsonify({"error": "Server error", "details": str(e)}), 500
    
    def _run_spider_command(self, room_ids_str):
        """
        Run the Bilibili live room spider with the provided room IDs.
        This method runs in a separate thread.
        
        Args:
            room_ids_str: A JSON string of room IDs
        """
        try:
            spider_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "missions", "tofu-bili-spider")
            command = f"cd {spider_dir} && scrapy crawl bilibili_live -a room_ids='{room_ids_str}'"
            
            debug(f"Running spider command: {command}")
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete (optional)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                error(f"Spider process failed with code {process.returncode}")
                error(f"STDOUT: {stdout}")
                error(f"STDERR: {stderr}")
            else:
                info("Spider process completed successfully")
                
        except Exception as e:
            error(f"Failed to run spider: {str(e)}")
            traceback.print_exc()

    def handle_setting(self):
        """
        处理 /setting 接口，用于接收记仇机器人指令
        接受格式：{"room_id": "房间ID", "danmaku": "弹幕内容"}
        """
        try:
            debug(f"Received setting request: {request.json}")
            data = request.json
            
            # 验证必要字段
            if not data or 'room_id' not in data or 'danmaku' not in data:
                return jsonify({"error": "Invalid request, missing 'room_id' or 'danmaku'"}), 400
                
            room_id = str(data['room_id'])
            danmaku = data['danmaku']
            notifee = DanmakuSender()
            
            # 检查是否包含有效的记仇机器人指令
            if "记仇机器人有效299792" in danmaku:
                # 设置房间状态为启用
                self.room_config_manager.set_room_youxiao(room_id, True)
                info(f"房间 {room_id} 已启用加强模式")
                notifee.send_danmaku(room_id, "喵喵，加强模式已开启喵~")
                return jsonify({
                    "status": "success", 
                    "message": "Room enabled successfully",
                    "youxiao": True
                }), 200
                
            elif "记仇机器人挽尊299792" in danmaku:
                # 设置房间状态为禁用
                self.room_config_manager.set_room_youxiao(room_id, False)
                info(f"房间 {room_id} 已禁用加强模式")
                notifee.send_danmaku(room_id, "喵喵，加强模式已关闭喵~")
                return jsonify({
                    "status": "success", 
                    "message": "Room disabled successfully",
                    "youxiao": False
                }), 200
                
            else:
                # 不是有效的指令
                debug(f"非有效记仇机器人指令: {danmaku}")
                return jsonify({"status": "ignored", "message": "Not a valid setting command"}), 200
                
        except Exception as e:
            error(f"Setting error: {e}")
            traceback.print_exc()
            return jsonify({"error": "Server error", "details": str(e)}), 500

    def handle_chatbot(self):
        """
        处理 /chatbot 接口，使用ChatGPT生成弹幕回复
        接受格式：{"room_id": "房间ID", "message": "用户消息"}
        """
        try:
            debug(f"收到chatbot请求: {request.json}")
            data = request.json
            
            # 验证必要字段
            if not data or 'room_id' not in data or 'message' not in data:
                return jsonify({"error": "无效请求，缺少 'room_id' 或 'message'"}), 400
                
            room_id = str(data['room_id'])
            message = data['message']
            notifee = DanmakuSender()
            
            try:
                # 使用ChatGPT生成回复，传递room_id以支持上下文记忆
                response = self.chatbot_handler.generate_response(message, room_id=room_id)
                
                # 检查是否是冷却回复
                if response == "喵喵喵喵喵！！！":
                    # 判断是处于冷却中还是刚触发冷却
                    if time.time() < self.chatbot_handler.cooldown_until:
                        # 冷却中
                        remaining_time = int(self.chatbot_handler.cooldown_until - time.time())
                        info(f"房间 {room_id} API调用被限制：冷却中，剩余 {remaining_time} 秒")
                    else:
                        # 刚触发冷却
                        info(f"房间 {room_id} 触发API调用冷却: 3秒内超过1次请求，冷却30秒")
                else:
                    debug(f"ChatGPT生成回复: {response}")
                
                # 发送弹幕
                notifee.send_danmaku(room_id, response)
                
                return jsonify({
                    "status": "success", 
                    "message": "弹幕已发送",
                    "response": response,
                    "rate_limited": response == "喵喵喵喵喵！！！",
                    "with_context": self.chatbot_handler.context_enabled
                }), 200
                
            except Exception as e:
                error(f"生成或发送回复失败: {str(e)}")
                # 发送一个默认回复
                notifee.send_danmaku(room_id, "喵喵喵～")
                
                return jsonify({
                    "status": "partial_success",
                    "message": f"生成回复失败，已发送默认回复: {str(e)}",
                    "response": "喵喵喵～"
                }), 200
                
        except Exception as e:
            error(f"处理chatbot请求失败: {e}")
            traceback.print_exc()
            return jsonify({"error": "服务器错误", "details": str(e)}), 500

    def handle_sendlike(self):
        """
        处理 /sendlike 接口，对指定房间发送点赞
        接受格式：{"room_id": "房间ID", "message": "消息内容"}
        立即返回200状态码，不等待点赞操作完成
        """
        try:
            debug(f"收到sendlike请求: {request.json}")
            data = request.json
            
            # 验证必要字段
            if not data or 'room_id' not in data:
                return jsonify({"error": "无效请求，缺少 'room_id'"}), 400
                
            room_id = str(data['room_id'])
            message = data.get('message', '点赞请求')  # 消息内容，用于日志记录
            like_times = data.get('like_times', 1000)  # 可选参数，点赞次数，默认1000次
            accounts = data.get('accounts', 'all')  # 可选参数，指定账号，默认全部账号
            max_workers = data.get('max_workers', 5)  # 可选参数，最大并行线程数，默认5
            
            # 创建一个线程来执行点赞和发送弹幕的操作
            like_thread = threading.Thread(
                target=self._execute_like_task,
                args=(room_id, message, like_times, accounts, max_workers),
                daemon=True
            )
            
            # 启动线程
            like_thread.start()
            
            # 立即返回成功响应，不等待点赞操作完成
            return jsonify({
                "status": "success", 
                "message": "点赞请求已接收，正在处理中",
                "room_id": room_id,
                "like_times": like_times,
                "accounts": accounts,
                "max_workers": max_workers
            }), 200
                
        except Exception as e:
            error(f"处理sendlike请求失败: {e}")
            traceback.print_exc()
            return jsonify({"error": "服务器错误", "details": str(e)}), 500
            
    def _execute_like_task(self, room_id, message, like_times, accounts, max_workers=5):
        """
        在后台线程中执行点赞任务
        """
        notifee = DanmakuSender()
        like_sender = LikeSender()
        
        # 发送确认弹幕
        try:
            notifee.send_danmaku(room_id, "喵喵，收到点赞请求喵～")
        except Exception as e:
            # 如果发送弹幕失败，只记录日志但不影响后续点赞操作
            error(f"发送确认弹幕失败: {str(e)}")
        
        # 发送点赞
        try:
            like_sender.send_like(room_id, message, like_times, accounts, max_workers)
            info(f"成功向房间 {room_id} 发送点赞，消息: {message}, 点赞次数: {like_times}, 账号: {accounts}, 并行数: {max_workers}")
            
            # 发送完成弹幕
            try:
                notifee.send_danmaku(room_id, "咪，点赞任务已完成，蹭蹭观测站的大伙们喵～！")
            except Exception as e:
                error(f"发送完成弹幕失败: {str(e)}")
            
        except TimeoutError:
            error(f"发送点赞超时 (room_id: {room_id})")
            try:
                notifee.send_danmaku(room_id, "喵喵，点赞超时了喵...")
            except:
                pass
            
        except RuntimeError as e:
            error(f"发送点赞失败: {str(e)}")
            try:
                notifee.send_danmaku(room_id, "喵喵，点赞失败了喵...")
            except:
                pass
        
        except Exception as e:
            error(f"点赞任务执行异常: {str(e)}")
            traceback.print_exc()
            try:
                notifee.send_danmaku(room_id, "喵喵，点赞发生错误喵...")
            except:
                pass

    def run(self, host='0.0.0.0', port=8081, debug=True):
        self.app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    app_instance = DanmakuGiftApp()
    app_instance.run()
else:
    # 当被 gunicorn 等 WSGI 服务器导入时，提供全局的 app 对象
    app_instance = DanmakuGiftApp()
    app = app_instance.app
