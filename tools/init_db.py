#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建礼物记录数据库表及索引
支持传入参数指定环境变量文件路径和表名
"""
import os
import sys
import argparse
import traceback
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到模块搜索路径
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

from modules.logger import get_logger, debug, info, warning, error, critical

def init_database(env_path, table_name="gift_records", drop_existing=False):
    """
    初始化数据库表结构
    
    Args:
        env_path: 环境变量文件路径
        table_name: 要创建的表名
        drop_existing: 是否删除已存在的表
        
    Returns:
        bool: 初始化是否成功
    """
    try:
        # 加载环境变量
        load_dotenv(env_path)
        
        # 数据库连接信息
        db_config = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASS"),
            "database": os.getenv("DB_NAME")
        }
        
        # 创建数据库连接
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 如果指定了删除表，先删除已存在的表
        if drop_existing:
            cursor.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
            info(f"Dropped existing table {table_name}")
        
        # 创建礼物记录表
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            room_id TEXT NOT NULL,
            uid BIGINT NOT NULL,
            uname TEXT NOT NULL,
            gift_id INTEGER NOT NULL,
            gift_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            gift_num INTEGER DEFAULT 1
        )
        ''')
        
        # 创建索引以加快查询速度
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_uid ON {table_name}(uid)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_room_id ON {table_name}(room_id)')
        
        conn.commit()
        info(f"Database table '{table_name}' and indexes initialized successfully")
        
        # 检查表是否创建成功
        cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            info(f"Confirmed table '{table_name}' exists")
        else:
            error(f"Failed to create table '{table_name}'")
            
        cursor.close()
        conn.close()
        
        return table_exists
        
    except Exception as e:
        error(f"Failed to initialize database: {e}")
        traceback.print_exc()
        return False

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="初始化礼物记录数据库")
    
    # 添加项目根目录到模块搜索路径
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    
    # 参数
    parser.add_argument("--env", default=str(root_dir / "missions/.env"), help="环境变量文件路径")
    parser.add_argument("--table", default="gift_records", help="表名")
    parser.add_argument("--drop", action="store_true", help="删除并重新创建表")
    parser.add_argument("--log-file", help="日志文件路径")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                        default="INFO", help="日志级别")
    
    # 解析参数
    args = parser.parse_args()
    
    # 配置日志级别
    log_level = getattr(logging, args.log_level)
    logger = get_logger("init_db", args.log_file, log_level)
    
    # 初始化数据库
    success = init_database(args.env, args.table, args.drop)
    
    # 设置退出码
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    import logging
    main() 