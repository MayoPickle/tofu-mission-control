"""
PostgreSQL 数据库处理模块
用于处理礼物记录相关的数据库操作和分析查询
"""
import os
import json
import psycopg2
import psycopg2.extras
import datetime
from dotenv import load_dotenv
from modules.logger import get_logger, debug, info, warning, error, critical

class DBHandler:
    def __init__(self, env_path="missions/.env", table_name="gift_records"):
        """
        初始化数据库处理器
        
        Args:
            env_path: 环境变量文件路径
            table_name: 要操作的表名
        """
        # 加载环境变量
        load_dotenv(env_path)
        
        # 数据库连接信息
        self.db_config = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASS"),
            "database": os.getenv("DB_NAME")
        }
        
        # 记录表名
        self.table_name = table_name
        
        info(f"数据库处理器初始化完成, 表名: {table_name}")
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            error(f"数据库连接失败: {e}")
            raise
    
    def add_gift_record(self, room_id, uid, uname, gift_id, gift_name, price, gift_num=1):
        """
        添加礼物记录
        
        Args:
            room_id: 房间ID
            uid: 用户ID
            uname: 用户名
            gift_id: 礼物ID
            gift_name: 礼物名称
            price: 礼物价格
            gift_num: 礼物数量，默认为1
            
        Returns:
            记录ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.datetime.now()
            debug(f"添加礼物记录: room_id={room_id}, uid={uid}, uname={uname}, gift={gift_name}, price={price}, num={gift_num}")
            
            cursor.execute(
                f'''
                INSERT INTO {self.table_name} 
                (timestamp, room_id, uid, uname, gift_id, gift_name, price, gift_num) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                ''', 
                (now, str(room_id), int(uid), uname, int(gift_id), gift_name, int(price), int(gift_num))
            )
            
            record_id = cursor.fetchone()[0]
            conn.commit()
            info(f"礼物记录添加成功, ID: {record_id}")
            return record_id
            
        except Exception as e:
            conn.rollback()
            error(f"添加礼物记录失败: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def add_gift_record_v2(self, payload: dict):
        """
        添加新版礼物记录（支持更多字段与 JSONB）。
        期望 payload 为来自 /money 的完整 JSON。
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 时间
            ts = payload.get("timestamp")
            if ts is None:
                now_dt = datetime.datetime.now()
            else:
                try:
                    now_dt = datetime.datetime.fromtimestamp(int(ts))
                except Exception:
                    now_dt = datetime.datetime.now()

            # 必需字段回退
            room_id = str(payload.get("room_id"))
            uid = int(payload.get("uid"))
            uname = str(payload.get("uname") or "")
            gift_id = int(payload.get("gift_id"))
            gift_name = str(payload.get("gift_name") or "")
            price = int(payload.get("price"))
            gift_num = int(payload.get("gift_num", 1))

            # 可选扩展字段
            total_price = payload.get("total_price")
            coin_type = payload.get("coin_type")
            gift_type = payload.get("gift_type")
            action = payload.get("action")
            is_blind_gift = payload.get("is_blind_gift")
            blind_box = payload.get("blind_box") or None
            sender = payload.get("sender") or None
            receiver = payload.get("receiver") or None
            tid = payload.get("tid")
            rnd = payload.get("rnd")
            batch_combo_id = payload.get("batch_combo_id")
            combo_total_coin = payload.get("combo_total_coin")
            total_coin = payload.get("total_coin")
            combo_id = payload.get("combo_id")

            debug(
                f"添加礼物记录V2: room_id={room_id}, uid={uid}, uname={uname}, gift={gift_name}, "
                f"price={price}, num={gift_num}, total_price={total_price}, coin_type={coin_type}, action={action}"
            )

            sql = f'''
                INSERT INTO {self.table_name}
                (
                    timestamp, room_id, uid, uname, gift_id, gift_name, price, gift_num,
                    total_price, coin_type, gift_type, action, is_blind_gift,
                    blind_box, sender, receiver,
                    tid, rnd, batch_combo_id, combo_total_coin, total_coin, combo_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                ) RETURNING id
            '''

            json_wrap = psycopg2.extras.Json
            cursor.execute(
                sql,
                (
                    now_dt, room_id, uid, uname, gift_id, gift_name, price, gift_num,
                    total_price if total_price is not None else None,
                    str(coin_type) if coin_type is not None else None,
                    int(gift_type) if gift_type is not None else None,
                    str(action) if action is not None else None,
                    bool(is_blind_gift) if is_blind_gift is not None else None,
                    json_wrap(blind_box) if blind_box is not None else None,
                    json_wrap(sender) if sender is not None else None,
                    json_wrap(receiver) if receiver is not None else None,
                    str(tid) if tid is not None else None,
                    str(rnd) if rnd is not None else None,
                    str(batch_combo_id) if batch_combo_id is not None else None,
                    int(combo_total_coin) if combo_total_coin is not None else None,
                    int(total_coin) if total_coin is not None else None,
                    str(combo_id) if combo_id is not None else None,
                )
            )

            record_id = cursor.fetchone()[0]
            conn.commit()
            info(f"礼物记录V2添加成功, ID: {record_id}")
            return record_id
        except Exception as e:
            conn.rollback()
            error(f"添加礼物记录V2失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_daily_summary(self, date=None):
        """
        获取指定日期的礼物汇总
        
        Args:
            date: 日期，格式为 YYYY-MM-DD 的字符串，默认为今天
            
        Returns:
            包含日汇总数据的字典列表
        """
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        debug(f"获取日汇总数据: date={date}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute(
                f'''
                SELECT 
                    room_id,
                    COUNT(*) as gift_count,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    DATE(timestamp) = %s
                GROUP BY 
                    room_id
                ORDER BY 
                    total_price DESC
                ''',
                (date,)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            info(f"日汇总数据获取成功: date={date}, 结果数量={len(results)}")
            return results
            
        except Exception as e:
            error(f"获取日汇总数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_weekly_summary(self, year=None, week=None):
        """
        获取指定周的礼物汇总
        
        Args:
            year: 年份，默认为当前年
            week: 周数，默认为当前周
            
        Returns:
            包含周汇总数据的字典列表
        """
        now = datetime.datetime.now()
        if year is None:
            year = now.year
        if week is None:
            week = now.isocalendar()[1]  # ISO周数
        
        debug(f"获取周汇总数据: year={year}, week={week}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute(
                f'''
                SELECT 
                    room_id,
                    COUNT(*) as gift_count,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    EXTRACT(YEAR FROM timestamp) = %s AND
                    EXTRACT(WEEK FROM timestamp) = %s
                GROUP BY 
                    room_id
                ORDER BY 
                    total_price DESC
                ''',
                (year, week)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            info(f"周汇总数据获取成功: year={year}, week={week}, 结果数量={len(results)}")
            return results
            
        except Exception as e:
            error(f"获取周汇总数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_monthly_summary(self, year=None, month=None):
        """
        获取指定月的礼物汇总
        
        Args:
            year: 年份，默认为当前年
            month: 月份，默认为当前月
            
        Returns:
            包含月汇总数据的字典列表
        """
        now = datetime.datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        debug(f"获取月汇总数据: year={year}, month={month}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            cursor.execute(
                f'''
                SELECT 
                    room_id,
                    COUNT(*) as gift_count,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    EXTRACT(YEAR FROM timestamp) = %s AND
                    EXTRACT(MONTH FROM timestamp) = %s
                GROUP BY 
                    room_id
                ORDER BY 
                    total_price DESC
                ''',
                (year, month)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            info(f"月汇总数据获取成功: year={year}, month={month}, 结果数量={len(results)}")
            return results
            
        except Exception as e:
            error(f"获取月汇总数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_user_contribution(self, uid):
        """
        获取指定用户的历史贡献
        
        Args:
            uid: 用户ID
            
        Returns:
            包含用户贡献数据的字典
        """
        debug(f"获取用户贡献数据: uid={uid}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            # 获取总贡献
            cursor.execute(
                f'''
                SELECT 
                    uid,
                    MAX(uname) as uname,
                    COUNT(*) as total_gifts,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    uid = %s
                GROUP BY 
                    uid
                ''',
                (uid,)
            )
            
            total_contribution = dict(cursor.fetchone() or {})
            
            # 获取按房间分类的贡献
            cursor.execute(
                f'''
                SELECT 
                    room_id,
                    COUNT(*) as gift_count,
                    SUM(price) as room_total
                FROM 
                    {self.table_name}
                WHERE 
                    uid = %s
                GROUP BY 
                    room_id
                ORDER BY 
                    room_total DESC
                ''',
                (uid,)
            )
            
            room_contribution = [dict(row) for row in cursor.fetchall()]
            
            # 获取按月份分类的贡献
            cursor.execute(
                f'''
                SELECT 
                    EXTRACT(YEAR FROM timestamp) as year,
                    EXTRACT(MONTH FROM timestamp) as month,
                    COUNT(*) as gift_count,
                    SUM(price) as month_total
                FROM 
                    {self.table_name}
                WHERE 
                    uid = %s
                GROUP BY 
                    year, month
                ORDER BY 
                    year DESC, month DESC
                ''',
                (uid,)
            )
            
            monthly_contribution = [dict(row) for row in cursor.fetchall()]
            
            result = {
                "total": total_contribution,
                "by_room": room_contribution,
                "by_month": monthly_contribution
            }
            
            info(f"用户贡献数据获取成功: uid={uid}, 房间数量={len(room_contribution)}, 月份数量={len(monthly_contribution)}")
            return result
            
        except Exception as e:
            error(f"获取用户贡献数据失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_top_contributors(self, room_id=None, limit=10, period=None):
        """
        获取顶级贡献者
        
        Args:
            room_id: 房间ID，可选，如果提供则只查询特定房间
            limit: 返回的记录数量
            period: 时间段，可选值："day", "week", "month", "year", None(所有时间)
            
        Returns:
            包含顶级贡献者数据的字典列表
        """
        debug(f"获取顶级贡献者: room_id={room_id}, limit={limit}, period={period}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            query = f'''
                SELECT 
                    uid,
                    MAX(uname) as uname,
                    COUNT(*) as gift_count,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    1=1
            '''
            params = []
            
            # 添加房间筛选条件
            if room_id:
                query += " AND room_id = %s"
                params.append(room_id)
            
            # 添加时间段筛选条件
            if period == "day":
                query += " AND DATE(timestamp) = CURRENT_DATE"
            elif period == "week":
                query += " AND timestamp >= date_trunc('week', CURRENT_DATE)"
            elif period == "month":
                query += " AND timestamp >= date_trunc('month', CURRENT_DATE)"
            elif period == "year":
                query += " AND timestamp >= date_trunc('year', CURRENT_DATE)"
            
            # 分组和排序
            query += '''
                GROUP BY 
                    uid
                ORDER BY 
                    total_price DESC
                LIMIT %s
            '''
            params.append(limit)
            
            cursor.execute(query, params)
            
            results = [dict(row) for row in cursor.fetchall()]
            info(f"顶级贡献者查询成功: room_id={room_id}, period={period}, 结果数量={len(results)}")
            return results
            
        except Exception as e:
            error(f"获取顶级贡献者失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
            
    def get_gift_trend(self, room_id=None, days=30):
        """
        获取礼物趋势数据（按天统计）
        
        Args:
            room_id: 房间ID，可选，如果提供则只查询特定房间
            days: 天数，查询最近多少天的数据
            
        Returns:
            包含每日礼物统计的字典列表
        """
        debug(f"获取礼物趋势: room_id={room_id}, days={days}")
        
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            query = f'''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as gift_count,
                    SUM(price) as total_price
                FROM 
                    {self.table_name}
                WHERE 
                    timestamp >= CURRENT_DATE - INTERVAL %s DAY
            '''
            params = [days]
            
            # 添加房间筛选条件
            if room_id:
                query += " AND room_id = %s"
                params.append(room_id)
            
            # 分组和排序
            query += '''
                GROUP BY 
                    date
                ORDER BY 
                    date ASC
            '''
            
            cursor.execute(query, params)
            
            results = [dict(row) for row in cursor.fetchall()]
            info(f"礼物趋势数据查询成功: room_id={room_id}, days={days}, 结果数量={len(results)}")
            return results
            
        except Exception as e:
            error(f"获取礼物趋势失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close() 