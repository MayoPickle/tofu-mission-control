# Tofu Mission Control

[English](README.md) | [中文](README-zh.md)

A Flask-based service for managing live streaming interactions, including gift handling, danmaku (chat) processing, and automated responses with AI chatbot integration.

## Features

- Gift tracking and management
- Automated responses based on danmaku keywords
- ChatGPT integration for intelligent responses
- Live room spider capability
- PK battle management
- Rate limiting and cooldown mechanisms
- Context memory for conversation history

## Requirements

- Python 3.10 or higher
- PostgreSQL database
- Dependencies listed in requirements.txt

## Setup

### Environment Configuration

1. Copy the example environment file:
   ```
   cp .env.example missions/.env
   ```

2. Edit `missions/.env` with your specific configuration:
   - Database credentials
   - OpenAI API key and model settings
   - Rate limiting and cooldown parameters
   - Context memory settings

### Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Initialize the database:
   ```
   python -c "from tools.init_db import init_database; init_database('missions/.env', 'gift_records')"
   ```

### Configuration Files

- `config.json`: Main application configuration
- `room_id_config.json`: Room-specific settings

## Running the Application

### Development Mode

```
python app.py
```

### Production Deployment

Using Gunicorn:
```
gunicorn -w 1 -b 0.0.0.0:8081 app:app
```

### Docker Deployment

Build and run the Docker container:
```
docker build -t tofu-mission-control .
docker run -p 8081:8081 tofu-mission-control
```

## API Endpoints

### `/ticket` - Process Ticket Requests

Handles special commands in danmaku messages and triggers appropriate responses.

**Method:** POST

**Request Example:**
```json
{
  "room_id": "12345",
  "danmaku": "全境 1234"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "操作已执行"
}
```

### `/money` - Record Gift Information

Records gift information sent to the live room.

**Method:** POST

**Request Example:**
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

**Response:**
```json
{
  "status": "success",
  "message": "Gift record saved successfully",
  "record_id": 123
}
```

### `/chatbot` - AI Chatbot Integration

Processes user messages and generates AI responses.

**Method:** POST

**Request Example:**
```json
{
  "room_id": "12345",
  "message": "你好，机器人",
  "username": "用户名"
}
```

**Response:**
```json
{
  "status": "success",
  "response": "你好，用户名！有什么我可以帮助你的吗？",
  "room_id": "12345"
}
```

### `/pk_wanzun` - PK Battle Logic

Manages PK battles between streamers.

**Method:** POST

### `/live_room_spider` - Start Live Room Spider

Initiates the spider to collect data from specified live rooms.

**Method:** POST

### `/setting` - Configure Application Settings

Updates application settings.

**Method:** POST

## Architecture

Tofu Mission Control is built with a modular architecture:

### Core Components

1. **DanmakuGiftApp** - Main application class that integrates all components
2. **ConfigLoader** - Handles configuration loading and management
3. **RoomConfigManager** - Manages room-specific configurations
4. **BatteryTracker** - Tracks gift statistics and resets on schedule
5. **GiftSender** - Handles gift sending operations
6. **DanmakuSender** - Manages sending messages to live rooms
7. **DBHandler** - Handles database operations for gift records
8. **ChatbotHandler** - Manages AI chatbot interactions

### Database Schema

The application primarily uses a PostgreSQL database with the following tables:

- **gift_records** - Stores gift information:
  - id (PK)
  - room_id
  - uid
  - uname
  - gift_id
  - gift_name
  - price
  - created_at

## Environment Variables

The application uses the following environment variables in `missions/.env`:

### Database Configuration
```
DB_HOST=your_db_host
DB_PORT=your_db_port
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
```

### OpenAI Configuration
```
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
```

### Rate Limiting Configuration
```
RATE_LIMIT_WINDOW=3
MAX_REQUESTS_PER_WINDOW=5
COOLDOWN_DURATION=30
```

### Context Memory Configuration
```
CONTEXT_ENABLED=true
MAX_CONTEXT_MESSAGES=50
CONTEXT_EXPIRY=7200
```

## Usage Examples

### Processing Danmaku Messages

When a user sends a danmaku message containing special keywords and a valid security code, the application can trigger various automated responses:

1. **全境模式** - Activates special functionality across all connected systems
2. **急急急** - Triggers high-priority Sentry response
3. **泰坦** - Activates Titan-level response (100 units)
4. **强袭** - Activates Striker-level response (10 units)
5. **默认** - Standard Ghost-level response (1 unit)

### AI Chatbot Integration

The system uses OpenAI's models to provide intelligent responses to user queries. The chatbot maintains conversation context for a configurable period (default: 2 hours) and limits requests to prevent API abuse.

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify your database credentials in `missions/.env`
   - Ensure the PostgreSQL server is running

2. **OpenAI API Errors**
   - Verify your API key is valid and has sufficient credits
   - Check that the selected model is available on your account

3. **Rate Limiting Issues**
   - Adjust `RATE_LIMIT_WINDOW`, `MAX_REQUESTS_PER_WINDOW`, and `COOLDOWN_DURATION` settings

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin new-feature`
5. Submit a pull request

## Performance Optimization

### Database Performance

1. **Index Optimization**
   
   For improved query performance, consider adding indexes to frequently queried columns:
   
   ```sql
   CREATE INDEX idx_gift_records_room_id ON gift_records(room_id);
   CREATE INDEX idx_gift_records_uid ON gift_records(uid);
   CREATE INDEX idx_gift_records_created_at ON gift_records(created_at);
   ```

2. **Connection Pooling**
   
   Implement connection pooling to reuse database connections:
   
   ```python
   from psycopg2 import pool
   
   # Create a connection pool
   connection_pool = pool.SimpleConnectionPool(
       1,  # Minimum connections
       20, # Maximum connections
       host=os.getenv("DB_HOST"),
       port=os.getenv("DB_PORT"),
       user=os.getenv("DB_USER"),
       password=os.getenv("DB_PASS"),
       database=os.getenv("DB_NAME")
   )
   ```

### API Performance

1. **Response Caching**
   
   Implement caching for frequently accessed data:
   
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_room_config(room_id):
       # Implementation
       pass
   ```

2. **Batch Processing**
   
   Use batch processing for bulk operations:
   
   ```python
   def add_gift_records_batch(records):
       # Implementation for batch insertion
       pass
   ```

### Memory Optimization

1. **Context Memory Management**
   
   Optimize context memory usage:
   
   ```python
   # Limit context size
   MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", 50))
   
   # Implement cleanup for old contexts
   def clean_expired_contexts():
       # Implementation
       pass
   ```

2. **Efficient Data Structures**
   
   Use efficient data structures for high-volume operations:
   
   ```python
   # Use sets for fast lookups
   active_rooms = set()
   
   # Use deque for fixed-size queues
   from collections import deque
   message_queue = deque(maxlen=100)
   ```

## Comprehensive Installation Guide

### Prerequisites

Before installing Tofu Mission Control, ensure you have the following prerequisites:

- Python 3.10 or higher
- PostgreSQL 12+ installed and running
- Git (for cloning the repository)
- pip (Python package manager)
- Docker (optional, for containerized deployment)

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tofu-mission-control.git
cd tofu-mission-control
```

#### 2. Create and Activate Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example missions/.env

# Edit the file with your settings
nano missions/.env
```

#### 5. Initialize Database

```bash
# Ensure PostgreSQL is running
python -c "from tools.init_db import init_database; init_database('missions/.env', 'gift_records')"
```

#### 6. Verify Installation

```bash
# Run in development mode
python app.py

# You should see output indicating the server is running on http://0.0.0.0:8081
```

### Advanced Installation Options

#### Installing with Docker Compose

Create a `docker-compose.yml` file:

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

Run with Docker Compose:

```bash
docker-compose up -d
```

## Project Structure

```
tofu-mission-control/
├── .env.example              # Example environment variables
├── .git/                     # Git repository data
├── .github/                  # GitHub workflow configurations
├── .gitignore                # Git ignore patterns
├── Dockerfile                # Docker build instructions
├── README.md                 # Project documentation
├── __init__.py               # Python package indicator
├── app.py                    # Main application entry point
├── config.json               # Application configuration
├── missions/                 # Mission-specific code and configuration
│   └── .env                  # Environment variables (created by user)
├── modules/                  # Core application modules
│   ├── battery_tracker.py    # Tracks gift statistics
│   ├── chatbot.py            # AI chatbot implementation
│   ├── config_loader.py      # Configuration loading utilities
│   ├── danmaku_sender.py     # Sends danmaku messages
│   ├── db_handler.py         # Database operations
│   ├── gift_api.py           # Gift API endpoints
│   ├── gift_sender.py        # Gift sending capabilities
│   ├── logger.py             # Logging utilities
│   └── room_config_manager.py # Room configuration management
├── requirements.txt          # Python dependencies
├── room_id_config.json       # Room-specific configurations
└── tools/                    # Utility scripts and tools
    └── init_db.py            # Database initialization
```

## Performance Optimization

### Database Performance

1. **Index Optimization**
   
   For improved query performance, consider adding indexes to frequently queried columns:
   
   ```sql
   CREATE INDEX idx_gift_records_room_id ON gift_records(room_id);
   CREATE INDEX idx_gift_records_uid ON gift_records(uid);
   CREATE INDEX idx_gift_records_created_at ON gift_records(created_at);
   ```

2. **Connection Pooling**
   
   Implement connection pooling to reuse database connections:
   
   ```python
   from psycopg2 import pool
   
   # Create a connection pool
   connection_pool = pool.SimpleConnectionPool(
       1,  # Minimum connections
       20, # Maximum connections
       host=os.getenv("DB_HOST"),
       port=os.getenv("DB_PORT"),
       user=os.getenv("DB_USER"),
       password=os.getenv("DB_PASS"),
       database=os.getenv("DB_NAME")
   )
   ```

### API Performance

1. **Response Caching**
   
   Implement caching for frequently accessed data:
   
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_room_config(room_id):
       # Implementation
       pass
   ```

2. **Batch Processing**
   
   Use batch processing for bulk operations:
   
   ```python
   def add_gift_records_batch(records):
       # Implementation for batch insertion
       pass
   ```

### Memory Optimization

1. **Context Memory Management**
   
   Optimize context memory usage:
   
   ```python
   # Limit context size
   MAX_CONTEXT_SIZE = int(os.getenv("MAX_CONTEXT_SIZE", 50))
   
   # Implement cleanup for old contexts
   def clean_expired_contexts():
       # Implementation
       pass
   ```

2. **Efficient Data Structures**
   
   Use efficient data structures for high-volume operations:
   
   ```python
   # Use sets for fast lookups
   active_rooms = set()
   
   # Use deque for fixed-size queues
   from collections import deque
   message_queue = deque(maxlen=100)
   ```

## Integration Examples

### Integrating with Webhooks

```python
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    event_type = data.get('event_type')
    
    if event_type == 'new_follower':
        # Handle new follower
        room_id = data.get('room_id')
        follower = data.get('username')
        notifee = DanmakuSender()
        notifee.send_danmaku(room_id, f"感谢 {follower} 的关注！")
    
    # Handle other events
    
    return jsonify({"status": "success"}), 200
```

### Integrating with External APIs

```python
def fetch_weather(location):
    api_key = os.getenv("WEATHER_API_KEY")
    url = f"https://api.weather.com/v1/location/{location}/forecast?apiKey={api_key}"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None
```

## Contact and Support

For bugs, feature requests, or general inquiries:

- GitHub Issues: [Create an issue](https://github.com/yourusername/tofu-mission-control/issues)
- Email: support@example.com

## Project Structure

```
tofu-mission-control/
├── .env.example              # Example environment variables
├── .git/                     # Git repository data
├── .github/                  # GitHub workflow configurations
├── .gitignore                # Git ignore patterns
├── Dockerfile                # Docker build instructions
├── README.md                 # Project documentation
├── __init__.py               # Python package indicator
├── app.py                    # Main application entry point
├── config.json               # Application configuration
├── missions/                 # Mission-specific code and configuration
│   └── .env                  # Environment variables (created by user)
├── modules/                  # Core application modules
│   ├── battery_tracker.py    # Tracks gift statistics
│   ├── chatbot.py            # AI chatbot implementation
│   ├── config_loader.py      # Configuration loading utilities
│   ├── danmaku_sender.py     # Sends danmaku messages
│   ├── db_handler.py         # Database operations
│   ├── gift_api.py           # Gift API endpoints
│   ├── gift_sender.py        # Gift sending capabilities
│   ├── logger.py             # Logging utilities
│   └── room_config_manager.py # Room configuration management
├── requirements.txt          # Python dependencies
├── room_id_config.json       # Room-specific configurations
└── tools/                    # Utility scripts and tools
    └── init_db.py            # Database initialization
```

## Acknowledgments

- Built with Flask and PostgreSQL
- Powered by OpenAI's GPT models
- Special thanks to all contributors 