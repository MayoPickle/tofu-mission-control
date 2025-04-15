# Tofu Mission Control

基于Flask的直播互动管理服务，包含礼物处理、弹幕处理和基于AI聊天机器人的自动回复功能。

## 功能特点

- 礼物追踪与管理
- 基于弹幕关键词的自动响应
- ChatGPT智能回复集成
- 直播间数据爬取能力
- PK对战管理
- 速率限制和冷却机制
- 上下文记忆功能

## 系统要求

- Python 3.10或更高版本
- PostgreSQL数据库
- requirements.txt中列出的依赖项

## 设置

### 环境配置

1. 复制环境变量示例文件：
   ```
   cp .env.example missions/.env
   ```

2. 编辑`missions/.env`并配置以下内容：
   - 数据库凭证
   - OpenAI API密钥和模型设置
   - 速率限制和冷却参数
   - 上下文记忆设置

### 安装

1. 安装所需依赖：
   ```
   pip install -r requirements.txt
   ```

2. 初始化数据库：
   ```
   python -c "from tools.init_db import init_database; init_database('missions/.env', 'gift_records')"
   ```

### 配置文件

- `config.json`：主应用程序配置
- `room_id_config.json`：房间特定设置

## 运行应用程序

### 开发模式

```
python app.py
```

### 生产部署

使用Gunicorn：
```
gunicorn -w 1 -b 0.0.0.0:8081 app:app
```

### Docker部署

构建并运行Docker容器：
```
docker build -t tofu-mission-control .
docker run -p 8081:8081 tofu-mission-control
```

## API接口

### `/ticket` - 处理特定弹幕请求

处理弹幕消息中的特殊命令并触发适当响应。

**方法：** POST

**请求示例：**
```json
{
  "room_id": "12345",
  "danmaku": "全境 1234"
}
```

**响应：**
```json
{
  "status": "success",
  "message": "操作已执行"
}
```

### `/money` - 记录礼物信息

记录发送到直播间的礼物信息。

**方法：** POST

**请求示例：**
```json
{
  "room_id": "12345",
  "uid": 67890,
  "uname": "用户名",
  "gift_id": 33988,
  "gift_name": "礼物名称",
  "price": 100
}
```

**响应：**
```json
{
  "status": "success",
  "message": "礼物记录保存成功",
  "record_id": 123
}
```

### `/chatbot` - AI聊天机器人集成

处理用户消息并生成AI回复。

**方法：** POST

**请求示例：**
```json
{
  "room_id": "12345",
  "message": "你好，机器人",
  "username": "用户名"
}
```

**响应：**
```json
{
  "status": "success",
  "response": "你好，用户名！有什么我可以帮助你的吗？",
  "room_id": "12345"
}
```

### `/pk_wanzun` - PK对战逻辑

管理主播之间的PK对战。

**方法：** POST

### `/live_room_spider` - 启动直播间爬虫

启动爬虫收集指定直播间的数据。

**方法：** POST

### `/setting` - 配置应用程序设置

更新应用程序设置。

**方法：** POST

## 架构

Tofu Mission Control采用模块化架构：

### 核心组件

1. **DanmakuGiftApp** - 集成所有组件的主应用程序类
2. **ConfigLoader** - 处理配置加载和管理
3. **RoomConfigManager** - 管理房间特定配置
4. **BatteryTracker** - 追踪礼物统计并按计划重置
5. **GiftSender** - 处理礼物发送操作
6. **DanmakuSender** - 管理向直播间发送消息
7. **DBHandler** - 处理礼物记录的数据库操作
8. **ChatbotHandler** - 管理AI聊天机器人交互

### 数据库结构

应用程序主要使用PostgreSQL数据库，包含以下表：

- **gift_records** - 存储礼物信息：
  - id (主键)
  - room_id (房间ID)
  - uid (用户ID)
  - uname (用户名)
  - gift_id (礼物ID)
  - gift_name (礼物名称)
  - price (价格)
  - created_at (创建时间)

## 环境变量

应用程序在`missions/.env`中使用以下环境变量：

### 数据库配置
```
DB_HOST=你的数据库主机
DB_PORT=你的数据库端口
DB_USER=你的数据库用户名
DB_PASS=你的数据库密码
DB_NAME=你的数据库名称
```

### OpenAI配置
```
OPENAI_API_KEY=你的OpenAI API密钥
OPENAI_MODEL=gpt-4o
```

### 速率限制配置
```
RATE_LIMIT_WINDOW=3
MAX_REQUESTS_PER_WINDOW=5
COOLDOWN_DURATION=30
```

### 上下文记忆配置
```
CONTEXT_ENABLED=true
MAX_CONTEXT_MESSAGES=50
CONTEXT_EXPIRY=7200
```

## 使用示例

### 处理弹幕消息

当用户发送包含特殊关键词和有效安全代码的弹幕消息时，应用程序可以触发各种自动响应：

1. **全境模式** - 激活所有连接系统的特殊功能
2. **急急急** - 触发高优先级哨兵响应
3. **泰坦** - 激活泰坦级响应（100单位）
4. **强袭** - 激活强袭级响应（10单位）
5. **默认** - 标准幽灵级响应（1单位）

### AI聊天机器人集成

系统使用OpenAI的模型为用户查询提供智能响应。聊天机器人会在可配置的时间段内（默认：2小时）维护对话上下文，并限制请求以防止API滥用。

## 故障排除

### 常见问题

1. **数据库连接错误**
   - 验证`missions/.env`中的数据库凭证
   - 确保PostgreSQL服务器正在运行

2. **OpenAI API错误**
   - 验证您的API密钥是否有效并有足够的额度
   - 检查所选模型是否在您的账户上可用

3. **速率限制问题**
   - 调整`RATE_LIMIT_WINDOW`、`MAX_REQUESTS_PER_WINDOW`和`COOLDOWN_DURATION`设置

## 贡献指南

欢迎贡献！请按照以下步骤操作：

1. Fork仓库
2. 创建特性分支：`git checkout -b new-feature`
3. 提交更改：`git commit -am '添加某功能'`
4. 推送分支：`git push origin new-feature`
5. 提交拉取请求

## 性能优化

### 数据库性能

1. **索引优化**
   
   为常用查询列添加索引，提高查询性能：
   
   ```sql
   CREATE INDEX idx_gift_records_room_id ON gift_records(room_id);
   CREATE INDEX idx_gift_records_uid ON gift_records(uid);
   CREATE INDEX idx_gift_records_created_at ON gift_records(created_at);
   ```

2. **连接池**
   
   实现连接池以重用数据库连接：
   
   ```python
   from psycopg2 import pool
   
   # 创建连接池
   connection_pool = pool.SimpleConnectionPool(
       1,  # 最小连接数
       20, # 最大连接数
       host=os.getenv("DB_HOST"),
       port=os.getenv("DB_PORT"),
       user=os.getenv("DB_USER"),
       password=os.getenv("DB_PASS"),
       database=os.getenv("DB_NAME")
   )
   ```

### API性能

1. **响应缓存**
   
   对频繁访问的数据实现缓存：
   
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_room_config(room_id):
       # 实现
       pass
   ```

2. **批处理**
   
   使用批处理进行批量操作：
   
   ```python
   def add_gift_records_batch(records):
       # 批量插入实现
       pass
   ```

### 内存优化

1. **上下文内存管理**
   
   优化上下文内存使用：
   
   ```python
   # 限制上下文大小
   MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", 50))
   
   # 实现旧上下文清理
   def clean_expired_contexts():
       # 实现
       pass
   ```

2. **高效数据结构**
   
   为高容量操作使用高效数据结构：
   
   ```python
   # 使用集合进行快速查找
   active_rooms = set()
   
   # 使用双端队列进行固定大小队列
   from collections import deque
   message_queue = deque(maxlen=100)
   ```

## 完整安装指南

### 前提条件

在安装Tofu Mission Control之前，请确保具备以下条件：

- Python 3.10或更高版本
- PostgreSQL 12+已安装并运行
- Git（用于克隆仓库）
- pip（Python包管理器）
- Docker（可选，用于容器化部署）

### 逐步安装

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/tofu-mission-control.git
cd tofu-mission-control
```

#### 2. 创建并激活虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# Windows上激活
venv\Scripts\activate

# macOS/Linux上激活
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example missions/.env

# 编辑设置
nano missions/.env
```

#### 5. 初始化数据库

```bash
# 确保PostgreSQL正在运行
python -c "from tools.init_db import init_database; init_database('missions/.env', 'gift_records')"
```

#### 6. 验证安装

```bash
# 以开发模式运行
python app.py

# 应该看到服务器运行在http://0.0.0.0:8081的输出
```

### 高级安装选项

#### 使用Docker Compose安装

创建一个`docker-compose.yml`文件：

```yaml
version: '3'

services:
  tofu-app:
    build: .
    ports:
      - "8081:8081"
    volumes:
      - ./missions/.env:/app/missions/.env
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:14
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

使用Docker Compose运行：

```bash
docker-compose up -d
```

## 项目结构

```
tofu-mission-control/
├── .env.example              # 环境变量示例
├── .git/                     # Git仓库数据
├── .github/                  # GitHub工作流配置
├── .gitignore                # Git忽略模式
├── Dockerfile                # Docker构建指令
├── README.md                 # 项目文档
├── __init__.py               # Python包标识
├── app.py                    # 主应用程序入口点
├── config.json               # 应用程序配置
├── missions/                 # 任务特定代码和配置
│   └── .env                  # 环境变量（由用户创建）
├── modules/                  # 核心应用程序模块
│   ├── battery_tracker.py    # 礼物统计追踪
│   ├── chatbot.py            # AI聊天机器人实现
│   ├── config_loader.py      # 配置加载工具
│   ├── danmaku_sender.py     # 发送弹幕消息
│   ├── db_handler.py         # 数据库操作
│   ├── gift_api.py           # 礼物API接口
│   ├── gift_sender.py        # 礼物发送功能
│   ├── logger.py             # 日志工具
│   └── room_config_manager.py # 房间配置管理
├── requirements.txt          # Python依赖
├── room_id_config.json       # 房间特定配置
└── tools/                    # 实用工具和脚本
    └── init_db.py            # 数据库初始化
```

## 集成示例

### 与Webhook集成

```python
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    event_type = data.get('event_type')
    
    if event_type == 'new_follower':
        # 处理新粉丝
        room_id = data.get('room_id')
        follower = data.get('username')
        notifee = DanmakuSender()
        notifee.send_danmaku(room_id, f"感谢 {follower} 的关注！")
    
    # 处理其他事件
    
    return jsonify({"status": "success"}), 200
```

### 与外部API集成

```python
def fetch_weather(location):
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"https://api.weather.com/v1/location/{location}/forecast?apiKey={api_key}"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None
```

## 联系与支持

对于bug、功能请求或一般咨询：

- GitHub Issues: [创建问题](https://github.com/yourusername/tofu-mission-control/issues)
- 电子邮件: support@example.com

## 安全考虑

### API认证

虽然应用程序没有内置认证，但建议为生产部署实现API密钥或OAuth2。考虑使用API网关或实现基于JWT的认证以确保安全访问。

### 环境变量

应用程序在环境变量中使用敏感信息。遵循以下安全做法：

1. 永远不要将`.env`文件提交到版本控制
2. 为开发和生产环境使用不同的API密钥
3. 定期轮换API密钥
4. 对`.env`文件设置限制性文件权限

### 速率限制

应用程序包含内置速率限制以防止滥用：

- `RATE_LIMIT_WINDOW`：计数请求的时间窗口（秒）（默认：3）
- `MAX_REQUESTS_PER_WINDOW`：时间窗口内允许的最大请求数（默认：5）
- `COOLDOWN_DURATION`：超过限制后客户端必须等待的时间（秒）（默认：30）

根据预期流量和服务器容量调整这些设置。

## 致谢

- 使用Flask和PostgreSQL构建
- 由OpenAI的GPT模型提供支持
- 特别感谢所有贡献者 