# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from itemadapter import ItemAdapter
from bilibili_spider.database import SessionLocal
from bilibili_spider.models import LiveRoom, UniqueRoomID
from bilibili_spider.items import LiveRoomItem, RoomIDItem
import logging

class BilibiliSpiderPipeline:
    """数据处理管道：负责处理抓取到的数据并保存到数据库"""
    
    def __init__(self):
        self.session = None
        self.logger = logging.getLogger('BilibiliSpiderPipeline')
    
    def open_spider(self, spider):
        """当爬虫开始时，创建数据库会话"""
        self.session = SessionLocal()
        self.logger.info("数据库会话已创建")
    
    def close_spider(self, spider):
        """当爬虫结束时，关闭数据库会话"""
        if self.session:
            self.session.close()
            self.logger.info("数据库会话已关闭")
    
    def process_item(self, item, spider):
        """处理抓取的数据项"""
        # 只处理LiveRoomItem类型的数据
        if not isinstance(item, LiveRoomItem):
            return item
            
        try:
            # 获取room_id用于查询
            room_id = item.get('room_id')
            
            if not room_id:
                self.logger.error("无效的数据项：缺少room_id字段")
                return item
                
            # 查找是否已有该直播间记录
            existing_room = self.session.query(LiveRoom).filter_by(room_id=room_id).first()
            
            if existing_room:
                # 更新现有记录
                for key, value in item.items():
                    if hasattr(existing_room, key):
                        setattr(existing_room, key, value)
                self.logger.info(f"更新直播间: {room_id}")
            else:
                # 创建新记录
                new_room = LiveRoom(**item)
                self.session.add(new_room)
                self.logger.info(f"新增直播间: {room_id}")
            
            # 提交事务
            self.session.commit()
            self.logger.info(f"数据已保存到数据库: {room_id}")
            
        except Exception as e:
            # 发生错误时回滚事务
            self.session.rollback()
            self.logger.error(f"保存数据失败: {e}")
            raise  # 添加这行来抛出异常，这样我们能看到具体的错误信息
            
        return item


class RoomIDPipeline:
    """处理房间ID的管道：将房间ID保存到unique_room_ids表"""
    
    def __init__(self):
        self.session = None
        self.logger = logging.getLogger('RoomIDPipeline')
    
    def open_spider(self, spider):
        """当爬虫开始时，创建数据库会话"""
        self.session = SessionLocal()
        self.logger.info("RoomID数据库会话已创建")
    
    def close_spider(self, spider):
        """当爬虫结束时，关闭数据库会话"""
        if self.session:
            self.session.close()
            self.logger.info("RoomID数据库会话已关闭")
    
    def process_item(self, item, spider):
        """处理房间ID数据项"""
        # 只处理RoomIDItem类型的数据
        if not isinstance(item, RoomIDItem):
            return item
            
        try:
            # 获取room_id
            room_id = item.get('room_id')
            
            if not room_id:
                self.logger.error("无效的房间ID数据项：缺少room_id字段")
                return item
                
            # 查找是否已有该房间ID记录
            existing_id = self.session.query(UniqueRoomID).filter_by(room_id=room_id).first()
            
            if existing_id:
                # 只更新last_checked时间
                existing_id.last_checked = item.get('last_checked')
                self.logger.info(f"更新房间ID记录: {room_id}")
            else:
                # 创建新记录
                new_id = UniqueRoomID(**item)
                self.session.add(new_id)
                self.logger.info(f"新增房间ID记录: {room_id}")
            
            # 提交事务
            self.session.commit()
            self.logger.info(f"房间ID已保存到数据库: {room_id}")
            
        except Exception as e:
            # 发生错误时回滚事务
            self.session.rollback()
            self.logger.error(f"保存房间ID失败: {e}")
            raise
            
        return item
