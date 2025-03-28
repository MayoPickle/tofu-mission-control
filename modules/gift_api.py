"""
礼物数据 API 模块
提供礼物数据分析和查询的API路由
"""
from flask import Blueprint, request, jsonify, current_app
from modules.db_handler import DBHandler
import os

# 创建蓝图
gift_api_bp = Blueprint('gift_api', __name__)

def get_db_handler():
    """获取数据库处理器实例，从app实例中获取表名"""
    app = current_app
    table_name = getattr(app, 'config', {}).get('GIFT_TABLE_NAME', 'gift_records')
    env_path = os.environ.get('GIFT_ENV_PATH', 'missions/.env')
    return DBHandler(env_path=env_path, table_name=table_name)

@gift_api_bp.route('/api/gift/daily', methods=['GET'])
def get_daily_stats():
    """获取每日礼物统计"""
    try:
        date = request.args.get('date')  # 可选参数，默认为今天
        db_handler = get_db_handler()
        result = db_handler.get_daily_summary(date)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/weekly', methods=['GET'])
def get_weekly_stats():
    """获取每周礼物统计"""
    try:
        year = request.args.get('year')
        if year:
            year = int(year)
            
        week = request.args.get('week')
        if week:
            week = int(week)
            
        db_handler = get_db_handler()
        result = db_handler.get_weekly_summary(year, week)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/monthly', methods=['GET'])
def get_monthly_stats():
    """获取每月礼物统计"""
    try:
        year = request.args.get('year')
        if year:
            year = int(year)
            
        month = request.args.get('month')
        if month:
            month = int(month)
            
        db_handler = get_db_handler()
        result = db_handler.get_monthly_summary(year, month)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/user/<int:uid>', methods=['GET'])
def get_user_contribution(uid):
    """获取用户贡献"""
    try:
        db_handler = get_db_handler()
        result = db_handler.get_user_contribution(uid)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/top', methods=['GET'])
def get_top_contributors():
    """获取顶级贡献者"""
    try:
        room_id = request.args.get('room_id')
        limit = request.args.get('limit', 10, type=int)
        period = request.args.get('period')  # 可选值: day, week, month, year, null(所有时间)
        
        db_handler = get_db_handler()
        result = db_handler.get_top_contributors(room_id, limit, period)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/trend', methods=['GET'])
def get_gift_trend():
    """获取礼物趋势"""
    try:
        room_id = request.args.get('room_id')
        days = request.args.get('days', 30, type=int)
        
        db_handler = get_db_handler()
        result = db_handler.get_gift_trend(room_id, days)
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@gift_api_bp.route('/api/gift/room/<room_id>', methods=['GET'])
def get_room_stats(room_id):
    """获取房间礼物统计"""
    try:
        # 获取期间礼物总数和总价值
        period = request.args.get('period')  # day, week, month, year, all
        
        db_handler = get_db_handler()
        
        # 基于不同时间段获取数据
        if period == 'day':
            result = db_handler.get_daily_summary()
        elif period == 'week':
            result = db_handler.get_weekly_summary()
        elif period == 'month':
            result = db_handler.get_monthly_summary()
        else:
            # 默认获取所有时间
            result = db_handler.get_top_contributors(room_id=room_id, limit=9999)
            
        # 过滤出当前房间的数据
        room_data = next((item for item in result if str(item['room_id']) == str(room_id)), {})
        
        # 获取该房间的顶级贡献者
        top_users = db_handler.get_top_contributors(room_id=room_id, limit=10)
        
        # 获取礼物趋势
        trend = db_handler.get_gift_trend(room_id=room_id, days=30)
        
        return jsonify({
            "status": "success",
            "data": {
                "stats": room_data,
                "top_users": top_users,
                "trend": trend
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 