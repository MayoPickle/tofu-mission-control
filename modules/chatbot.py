import os
import json
import traceback
import time
from threading import Lock
from typing import Any, Dict, Optional
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
        # 用户记忆：按房间 -> 用户键 -> 记忆字典
        self.user_memory_by_room: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self.user_memory_lock = Lock()
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

        # 同步清理过期的用户记忆（基于房间最后活跃时间或用户自身last_seen）
        with self.user_memory_lock:
            current_time = time.time()
            rooms_to_delete = []
            for room_id, user_map in self.user_memory_by_room.items():
                users_to_delete = []
                for user_key, mem in user_map.items():
                    last_seen = mem.get("last_seen", 0)
                    if current_time - last_seen > self.context_expiry:
                        users_to_delete.append(user_key)
                for user_key in users_to_delete:
                    del user_map[user_key]
                if not user_map:
                    rooms_to_delete.append(room_id)
            for room_id in rooms_to_delete:
                del self.user_memory_by_room[room_id]

    @staticmethod
    def _get_user_key(user_profile: Optional[Dict[str, Any]]) -> Optional[str]:
        """仅当 sender.uid > 0 时生成用户键；uid==0 或缺失则不记录（不回退 uname）。"""
        if not user_profile:
            return None
        sender = user_profile.get("sender") or {}
        uname = user_profile.get("uname") or sender.get("uname")
        try:
            uid = int(sender.get("uid")) if sender.get("uid") is not None else 0
        except Exception:
            uid = 0
        if uid and uid > 0:
            return f"uid:{uid}"
        # 匿名或无uid时不记录任何个体记忆
        return None

    @staticmethod
    def _extract_banned_words_from_message(text: str) -> list[str]:
        """
        从用户消息中抽取类似“不要说X/别说X/别提X”的禁用词（粗糙规则）。
        返回去重后的词列表。
        """
        try:
            import re
            candidates = []
            # 常见否定表达
            patterns = [
                r"不要说([\w\u4e00-\u9fa5·\.\-＿_]+)",
                r"别说([\w\u4e00-\u9fa5·\.\-＿_]+)",
                r"别提([\w\u4e00-\u9fa5·\.\-＿_]+)",
                r"不要提([\w\u4e00-\u9fa5·\.\-＿_]+)"
            ]
            for p in patterns:
                for m in re.findall(p, text):
                    if m:
                        candidates.append(m.strip())
            # 基于标点进一步裁剪明显结尾
            cleaned = []
            for w in candidates:
                w = w.strip("，,。.!！?？ ")
                if w:
                    cleaned.append(w)
            # 去重保持顺序
            seen = set()
            result = []
            for w in cleaned:
                if w not in seen:
                    seen.add(w)
                    result.append(w)
            return result
        except Exception:
            return []

    def _update_user_memory(self, room_id: str, user_key: str, user_profile: Dict[str, Any], latest_message: str):
        """合并/更新用户画像与偏好（禁用词、勋章、守护等）。"""
        if not room_id or not user_key:
            return
        with self.user_memory_lock:
            memory = self.user_memory_by_room[room_id].get(user_key, {})
            # 基础档案
            sender = user_profile.get("sender") or {}
            medal = user_profile.get("medal") or {}
            uname = user_profile.get("uname") or sender.get("uname") or ""
            memory["uname"] = uname
            memory["wealth_level"] = sender.get("wealth_level")
            memory["guard_level"] = sender.get("guard_level")
            memory["is_captain"] = bool(sender.get("is_captain")) or (int(sender.get("guard_level") or 0) > 0)
            # 勋章信息
            if medal:
                memory["medal_name"] = medal.get("name")
                memory["medal_level"] = medal.get("level")
            # 偏好：禁用词
            banned_words = set(memory.get("banned_words", []))
            for w in self._extract_banned_words_from_message(latest_message or ""):
                banned_words.add(w)
            memory["banned_words"] = sorted(banned_words)
            # 最近活跃时间
            memory["last_seen"] = time.time()
            # 存回
            self.user_memory_by_room[room_id][user_key] = memory

    def _build_user_memory_prompt(self, room_id: str, user_key: Optional[str]) -> str:
        """将用户记忆压缩为简短中文说明，作为 system message 注入。"""
        if not room_id or not user_key:
            return ""
        with self.user_memory_lock:
            mem = self.user_memory_by_room.get(room_id, {}).get(user_key)
            if not mem:
                return ""
            parts = ["关于当前说话用户的记忆（请严格遵守）："]
            uname = mem.get("uname")
            if uname:
                parts.append(f"- 昵称：{uname}")
            if mem.get("medal_name"):
                parts.append(f"- 勋章：{mem.get('medal_name')} Lv{mem.get('medal_level')}")
            if mem.get("is_captain"):
                parts.append("- 身份：舰长/守护")
            banned = mem.get("banned_words") or []
            if banned:
                parts.append(f"- 避免提及：{ '、'.join(banned) }")
            parts.append("请在≤40字中文回复中尊重其偏好与禁用词。")
            text = "\n".join(parts)
            # 控制长度（避免占用过多上下文）
            return text[:400]
        
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
        
    def generate_response(self, user_message, room_id=None, user_profile: Optional[Dict[str, Any]] = None):
        """
        调用ChatGPT API生成猫猫风格的弹幕回复
        
        :param user_message: 用户发送的消息内容
        :param room_id: 房间ID，用于上下文记忆
        :param user_profile: 用户信息（可选），用于维护个体记忆并注入到历史
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

            # 如提供用户信息，先更新用户记忆，并构造记忆提示
            user_key = self._get_user_key(user_profile)
            if user_key:
                try:
                    self._update_user_memory(room_id, user_key, user_profile or {}, user_message or "")
                except Exception:
                    # 记忆失败不影响主流程
                    pass
            memory_prompt = self._build_user_memory_prompt(room_id, user_key) if user_key else ""

            # 在首个system之后插入用户记忆的system message（仅注入，不写入持久历史）
            messages_with_memory = list(messages)
            if memory_prompt:
                if messages_with_memory and messages_with_memory[0].get("role") == "system":
                    messages_with_memory = [messages_with_memory[0], {"role": "system", "content": memory_prompt}] + messages_with_memory[1:]
                else:
                    messages_with_memory = [
                        {"role": "system", "content": self.get_system_prompt_for_room(room_id)},
                        {"role": "system", "content": memory_prompt},
                    ] + messages_with_memory

            # 添加用户消息到历史（持久）
            self.add_to_history(room_id, "user", user_message)

            # 当前请求的messages（含用户记忆注入）
            current_messages = messages_with_memory + [{"role": "user", "content": user_message}]
            
            # 使用官方SDK调用API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=current_messages,
                # max_tokens=50,  # 限制回复长度
                # temperature=0.7  # 控制创造性，较低的值使输出更集中和确定
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

    def describe_avatar(self, image_url: str) -> str:
        """
        使用支持视觉的模型简要描述头像（中文，尽量不超过20字）。

        :param image_url: 头像图片的URL
        :return: 简短的头像描述；失败时返回空字符串
        """
        try:
            if not image_url or not isinstance(image_url, str):
                return ""

            # 使用视觉模型；若未配置则默认 gpt-4o-mini
            vision_model = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini")

            messages = [
                {
                    "role": "system",
                    "content": "你是图像描述助手。仅用中文简要描述头像的角色名字，如果不确定就描述主体与风格，避免臆测。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请用不超过20字描述这张头像："},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]

            response = self.client.chat.completions.create(
                model=vision_model,
                messages=messages,
                max_tokens=60,
                temperature=0.2
            )

            desc = (response.choices[0].message.content or "").strip()
            if len(desc) > 30:
                desc = desc[:30]
            return desc
        except Exception:
            # 失败时静默降级
            return ""

    def generate_welcome_message(self, uname: str, is_captain: bool, avatar_desc: str | None = None) -> str:
        """
        生成欢迎文案（中文，猫猫风格，单句，尽量不超过30字；舰长需特别致意）。

        :param uname: 用户名
        :param is_captain: 是否为舰长（或同等守护）
        :param avatar_desc: 头像描述（可选）
        :return: 欢迎语
        """
        try:
            if not uname:
                uname = "小伙伴"

            base_model = self.model or os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

            system_prompt = (
                "你是直播间欢迎助手，以可爱猫猫风格写欢迎语。"
                "要求：仅输出一句中文欢迎语，包含对方昵称；"
                "若其为舰长需特别致意；可以自然融入头像特征；"
                "不输出引号与解释；尽量≤30字。"
            )

            user_text_parts = [
                f"昵称：{uname}",
                f"身份：{'舰长' if is_captain else '普通观众'}"
            ]
            if avatar_desc:
                user_text_parts.append(f"头像：{avatar_desc}")
            user_text_parts.append("请直接给出最终欢迎语。")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "；".join(user_text_parts)}
            ]

            response = self.client.chat.completions.create(
                model=base_model,
                messages=messages,
                max_tokens=60,
                temperature=0.7
            )

            text = (response.choices[0].message.content or "").strip()
            if len(text) > 40:
                text = text[:40]
            return text or (f"欢迎{uname}喵～" if not is_captain else f"欢迎舰长{uname}喵～")
        except Exception:
            # 降级为固定短句
            return f"欢迎{uname}喵～" if not is_captain else f"欢迎舰长{uname}喵～"
