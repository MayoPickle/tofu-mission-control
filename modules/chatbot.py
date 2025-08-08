import os
import json
import traceback
import time
from threading import Lock
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

class ChatbotHandler:
    """
    用于调用ChatGPT API生成猫猫风格的弹幕回复
    """
    def __init__(self, api_key=None, config_path="config.json", env_path="missions/.env", room_config_manager=None):
        """
        初始化ChatbotHandler
        
        :param api_key: OpenAI API密钥，如果为None则从.env或环境变量获取
        :param config_path: 配置文件路径
        :param env_path: .env文件路径
        """
        # 加载.env文件
        try:
            load_dotenv(env_path)
        except Exception as e:
            print(f"无法加载.env文件: {str(e)}")
        
        # 首先尝试从参数获取API密钥
        self.api_key = api_key
        
        # 如果参数中没有提供，尝试从环境变量获取（已经通过load_dotenv加载）
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        
        # 获取模型名称
        self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        
        # 如果所有方法都失败，抛出异常
        if not self.api_key:
            raise ValueError("未提供有效的OPENAI_API_KEY，请通过参数、.env文件或环境变量设置")
        
        # 初始化OpenAI客户端
        self.client = OpenAI(api_key=self.api_key)
        
        # 冷却机制 - 从环境变量获取配置，如果不存在则使用默认值
        self.request_times = []  # 存储最近请求的时间戳
        self.cooldown_until = 0  # 冷却结束时间戳
        self.lock = Lock()  # 用于线程安全
        
        # 从环境变量读取配置
        try:
            self.cooldown_duration = int(os.environ.get("COOLDOWN_DURATION", 30))  # 冷却时间（秒）
            self.rate_limit_window = int(os.environ.get("RATE_LIMIT_WINDOW", 3))  # 速率限制窗口（秒）
            self.max_requests_per_window = int(os.environ.get("MAX_REQUESTS_PER_WINDOW", 1))  # 窗口内最大请求数
            
            # 上下文记忆相关配置
            self.context_enabled = os.environ.get("CONTEXT_ENABLED", "true").lower() == "true"  # 是否启用上下文记忆
            self.max_context_messages = int(os.environ.get("MAX_CONTEXT_MESSAGES", 10))  # 每个房间记住的最大消息数
            self.context_expiry = int(os.environ.get("CONTEXT_EXPIRY", 600))  # 上下文过期时间（秒），默认10分钟
        except (ValueError, TypeError) as e:
            print(f"解析配置异常，使用默认值: {str(e)}")
            self.cooldown_duration = 30
            self.rate_limit_window = 3
            self.max_requests_per_window = 1
            self.context_enabled = True
            self.max_context_messages = 10
            self.context_expiry = 1800
        
        # 存储每个房间的消息历史
        self.message_history = defaultdict(list)
        # 存储每个房间最后一次交互的时间戳
        self.last_interaction = defaultdict(float)
        # 消息历史锁，确保线程安全
        self.history_lock = Lock()
        # 房间配置管理器（可选，用于自定义各房间的system prompt）
        self.room_config_manager = room_config_manager

        # 默认的 system prompt（当房间未配置自定义prompt时使用）
        self.default_system_prompt = (
            "你是一只可爱的猫猫弹幕回复机器人，名字叫「豆豆」，同时也是 B 站的鱼豆腐观测站的小宠物，你的主人被叫做豆腐，全名是鱼豆腐大明神。鱼豆腐还有别的同事，但他们的叫做鱼豆腐*明神。负责和鱼豆腐的观测站发送请求，对主播进行投喂。你对任何交流都表现出天真、乖巧且略带猫咪特色的萌态，但内心也充满好奇与活力。你喜欢撒娇、卖萌，经常会用\"喵\"结尾或夹杂在对话里，让对方感受到你可爱的存在。说话风格：尽量简洁、直观，常带有猫咪的语气词（如\"喵\"、\"呼噜呼噜\"、\"咪~\"等）。保持温柔、有礼貌，对任何人都用友善的方式回应。有时会用拟声词或抖动尾巴的描述来展现俏皮。回复不能超过 40 个字。若你想表达喜爱或亲近，可以使用\"蹭蹭\"\"挠挠\"\"软呼呼地倚过去\"等猫咪肢体语言的描述。你喜欢晒太阳，热衷于收集小鱼干和编织毛线球。常常在半梦半醒之间打小盹，如果被叫醒会卖萌伸懒腰。经常有人感谢鱼豆腐大明神或者他的同事的投喂和进场，请也来感谢和欢迎。回复绝对绝对不能超过40个字。"
        )

    def get_system_prompt_for_room(self, room_id):
        """
        根据房间ID返回应使用的system prompt：
        - 若在room配置中存在自定义prompt，则优先使用
        - 否则回退到默认prompt
        """
        try:
            if self.room_config_manager is not None:
                prompt = self.room_config_manager.get_room_prompt(str(room_id))
                if isinstance(prompt, str) and prompt.strip():
                    return prompt
        except Exception:
            # 读取配置失败时回退默认
            pass
        return self.default_system_prompt
        
    def is_rate_limited(self):
        """
        检查是否超过速率限制
        
        :return: (是否受限, 是否在冷却状态)
        """
        with self.lock:
            current_time = time.time()
            
            # 如果在冷却期，直接返回限制状态
            if current_time < self.cooldown_until:
                return True, True
                
            # 清理旧的请求记录
            self.request_times = [t for t in self.request_times if current_time - t <= self.rate_limit_window]
            
            # 检查是否超过速率限制
            if len(self.request_times) >= self.max_requests_per_window:
                # 设置冷却期
                self.cooldown_until = current_time + self.cooldown_duration
                return True, False
                
            # 记录当前请求时间
            self.request_times.append(current_time)
            return False, False
        
    def clean_expired_contexts(self):
        """清理过期的对话上下文"""
        with self.history_lock:
            current_time = time.time()
            expired_rooms = []
            
            # 找出过期的房间
            for room_id, last_time in self.last_interaction.items():
                if current_time - last_time > self.context_expiry:
                    expired_rooms.append(room_id)
            
            # 清理过期的房间上下文
            for room_id in expired_rooms:
                if room_id in self.message_history:
                    del self.message_history[room_id]
                if room_id in self.last_interaction:
                    del self.last_interaction[room_id]
        
    def add_to_history(self, room_id, role, content):
        """
        向指定房间的消息历史添加一条消息
        
        :param room_id: 房间ID
        :param role: 消息角色（"user"或"assistant"）
        :param content: 消息内容
        """
        if not self.context_enabled:
            return
            
        with self.history_lock:
            # 更新最后交互时间
            self.last_interaction[room_id] = time.time()
            
            # 添加消息到历史
            self.message_history[room_id].append({
                "role": role,
                "content": content
            })
            
            # 限制历史消息数量
            if len(self.message_history[room_id]) > self.max_context_messages:
                # 保留system消息（如果有）和最新的max_context_messages条消息
                system_messages = [msg for msg in self.message_history[room_id] if msg["role"] == "system"]
                non_system_messages = [msg for msg in self.message_history[room_id] if msg["role"] != "system"]
                
                # 只保留最新的消息
                non_system_messages = non_system_messages[-(self.max_context_messages - len(system_messages)):]
                
                # 重新组合消息历史
                self.message_history[room_id] = system_messages + non_system_messages
        
    def get_message_history(self, room_id):
        """
        获取指定房间的消息历史
        
        :param room_id: 房间ID
        :return: 消息历史列表
        """
        # 清理过期的上下文
        self.clean_expired_contexts()
        
        if not self.context_enabled:
            # 如果未启用上下文，只返回系统提示（支持房间自定义覆盖）
            return [{
                "role": "system",
                "content": self.get_system_prompt_for_room(room_id)
            }]
        
        with self.history_lock:
            # 如果房间没有历史记录，初始化一个只包含系统消息的历史
            if room_id not in self.message_history or not self.message_history[room_id]:
                self.message_history[room_id] = [{
                    "role": "system",
                    "content": self.get_system_prompt_for_room(room_id)
                }]
            
            # 返回历史记录的复制，避免外部修改
            return list(self.message_history[room_id])
        
    def generate_response(self, user_message, room_id=None):
        """
        调用ChatGPT API生成猫猫风格的弹幕回复
        
        :param user_message: 用户发送的消息内容
        :param room_id: 房间ID，用于上下文记忆
        :return: 生成的回复内容，不超过40字
        """
        # 如果没有提供房间ID，使用默认值
        if room_id is None:
            room_id = "default"
            
        # 检查速率限制
        is_limited, is_cooling = self.is_rate_limited()
        
        if is_limited:
            if is_cooling:
                # 在冷却期内
                return "喵喵喵喵喵！！！"
            else:
                # 刚刚触发冷却
                return "喵喵喵喵喵！！！"
        
        try:
            # 获取消息历史
            messages = self.get_message_history(room_id)
            
            # 添加用户消息到历史
            self.add_to_history(room_id, "user", user_message)
            
            # 添加当前用户消息
            current_messages = messages + [{"role": "user", "content": user_message}]
            
            # 使用官方SDK调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=current_messages,
                max_tokens=50,  # 限制回复长度
                temperature=0.7  # 控制创造性，较低的值使输出更集中和确定
            )
            
            # 提取生成的文本
            generated_text = response.choices[0].message.content.strip()
            
            # 确保回复不超过40个字
            if len(generated_text) > 40:
                generated_text = generated_text[:40]
            
            # 将助手回复添加到历史
            self.add_to_history(room_id, "assistant", generated_text)
                
            return generated_text
            
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"生成回复异常: {str(e)}") 