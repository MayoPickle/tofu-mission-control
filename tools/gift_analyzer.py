#!/usr/bin/env python3
"""
礼物数据分析命令行工具
提供方便的命令行接口来查询和分析礼物数据
"""
import os
import sys
import argparse
import json
import datetime
import logging
from pathlib import Path

# 添加项目根目录到模块搜索路径
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

from modules.db_handler import DBHandler
from modules.logger import get_logger, debug, info, warning, error, critical, set_log_level

def format_output(data, format_type="table"):
    """格式化输出数据"""
    if not data:
        return "没有找到任何数据"
        
    if format_type == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    # 默认表格格式
    if isinstance(data, list) and len(data) > 0:
        # 获取表头
        headers = data[0].keys()
        # 计算每列宽度
        col_widths = {header: max(len(str(header)), max(len(str(row.get(header, ""))) for row in data)) for header in headers}
        
        # 构建表格
        header_row = " | ".join(f"{header:<{col_widths[header]}}" for header in headers)
        separator = "-+-".join("-" * col_widths[header] for header in headers)
        table = [header_row, separator]
        
        for row in data:
            table_row = " | ".join(f"{str(row.get(header, '')):<{col_widths[header]}}" for header in headers)
            table.append(table_row)
            
        return "\n".join(table)
    elif isinstance(data, dict):
        # 嵌套字典的情况，例如get_user_contribution返回的结构
        result = []
        for key, value in data.items():
            if isinstance(value, list):
                result.append(f"\n== {key} ==")
                result.append(format_output(value, format_type))
            elif isinstance(value, dict):
                result.append(f"\n== {key} ==")
                for k, v in value.items():
                    result.append(f"{k}: {v}")
            else:
                result.append(f"{key}: {value}")
        
        return "\n".join(result)
    else:
        return str(data)

def main():
    parser = argparse.ArgumentParser(description="礼物数据分析工具")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 每日统计
    daily_parser = subparsers.add_parser("daily", help="每日礼物统计")
    daily_parser.add_argument("--date", help="日期 (YYYY-MM-DD), 默认为今天")
    
    # 每周统计
    weekly_parser = subparsers.add_parser("weekly", help="每周礼物统计")
    weekly_parser.add_argument("--year", type=int, help="年份")
    weekly_parser.add_argument("--week", type=int, help="周数")
    
    # 每月统计
    monthly_parser = subparsers.add_parser("monthly", help="每月礼物统计")
    monthly_parser.add_argument("--year", type=int, help="年份")
    monthly_parser.add_argument("--month", type=int, help="月份")
    
    # 用户贡献
    user_parser = subparsers.add_parser("user", help="用户贡献统计")
    user_parser.add_argument("uid", type=int, help="用户ID")
    
    # 顶级贡献者
    top_parser = subparsers.add_parser("top", help="顶级贡献者")
    top_parser.add_argument("--room-id", help="房间ID")
    top_parser.add_argument("--limit", type=int, default=10, help="返回的记录数量")
    top_parser.add_argument("--period", choices=["day", "week", "month", "year"], help="时间段")
    
    # 礼物趋势
    trend_parser = subparsers.add_parser("trend", help="礼物趋势")
    trend_parser.add_argument("--room-id", help="房间ID")
    trend_parser.add_argument("--days", type=int, default=30, help="天数")
    
    # 房间统计
    room_parser = subparsers.add_parser("room", help="房间礼物统计")
    room_parser.add_argument("room_id", help="房间ID")
    room_parser.add_argument("--period", choices=["day", "week", "month", "year"], help="时间段")
    
    # 全局选项
    parser.add_argument("--format", choices=["table", "json"], default="table", help="输出格式")
    parser.add_argument("--env", default=str(root_dir / "missions/.env"), help="环境变量文件路径")
    parser.add_argument("--table", default="gift_records", help="要查询的表名")
    parser.add_argument("--log-file", help="日志文件路径")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], 
                       default="INFO", help="日志级别")
    parser.add_argument("--quiet", action="store_true", help="安静模式，不输出详细日志")
    
    # 解析参数
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level)
    logger = get_logger("gift_analyzer", args.log_file, log_level)
    
    # 如果是安静模式，将日志级别调整为ERROR
    if args.quiet:
        set_log_level(logging.ERROR)
    
    # 初始化DBHandler
    db_handler = DBHandler(args.env, args.table)
    
    try:
        # 执行命令
        if args.command == "daily":
            info(f"执行每日统计命令: date={args.date}")
            result = db_handler.get_daily_summary(args.date)
            print(format_output(result, args.format))
        elif args.command == "weekly":
            info(f"执行每周统计命令: year={args.year}, week={args.week}")
            result = db_handler.get_weekly_summary(args.year, args.week)
            print(format_output(result, args.format))
        elif args.command == "monthly":
            info(f"执行每月统计命令: year={args.year}, month={args.month}")
            result = db_handler.get_monthly_summary(args.year, args.month)
            print(format_output(result, args.format))
        elif args.command == "user":
            info(f"执行用户贡献统计命令: uid={args.uid}")
            result = db_handler.get_user_contribution(args.uid)
            print(format_output(result, args.format))
        elif args.command == "top":
            info(f"执行顶级贡献者命令: room_id={args.room_id}, limit={args.limit}, period={args.period}")
            result = db_handler.get_top_contributors(args.room_id, args.limit, args.period)
            print(format_output(result, args.format))
        elif args.command == "trend":
            info(f"执行礼物趋势命令: room_id={args.room_id}, days={args.days}")
            result = db_handler.get_gift_trend(args.room_id, args.days)
            print(format_output(result, args.format))
        elif args.command == "room":
            info(f"执行房间统计命令: room_id={args.room_id}, period={args.period}")
            # 根据时间段获取数据
            if args.period == 'day':
                result = db_handler.get_daily_summary()
            elif args.period == 'week':
                result = db_handler.get_weekly_summary()
            elif args.period == 'month':
                result = db_handler.get_monthly_summary()
            else:
                # 默认获取所有时间
                result = db_handler.get_top_contributors(room_id=args.room_id, limit=9999)
            
            # 过滤出当前房间的数据
            room_data = next((item for item in result if str(item.get('room_id', '')) == str(args.room_id)), {})
            
            # 获取该房间的顶级贡献者
            top_users = db_handler.get_top_contributors(room_id=args.room_id, limit=10)
            
            # 获取礼物趋势
            trend = db_handler.get_gift_trend(room_id=args.room_id, days=30)
            
            data = {
                "stats": room_data,
                "top_users": top_users,
                "trend": trend
            }
            
            print(format_output(data, args.format))
        else:
            parser.print_help()
    except Exception as e:
        error(f"命令执行失败: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 