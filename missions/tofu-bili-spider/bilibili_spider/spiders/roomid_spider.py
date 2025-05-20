import scrapy
import json
import logging
from datetime import datetime, timezone
from bilibili_spider.items import RoomIDItem

class RoomIDSpider(scrapy.Spider):
    name = "roomid_spider"
    
    def __init__(self, room_ids=None, room_id=None, *args, **kwargs):
        super(RoomIDSpider, self).__init__(*args, **kwargs)
        
        # 处理单个room_id或多个room_ids
        if room_ids:
            # 如果提供了room_ids参数，解析为列表
            if isinstance(room_ids, str):
                try:
                    self.room_ids = json.loads(room_ids)
                except json.JSONDecodeError:
                    # 如果不是有效的JSON，尝试以逗号分隔的字符串处理
                    self.room_ids = [rid.strip() for rid in room_ids.split(',')]
            else:
                self.room_ids = room_ids
        elif room_id:
            # 向后兼容：如果只提供了单个room_id
            self.room_ids = [room_id]
        else:
            self.room_ids = []

    def start_requests(self):
        """处理房间ID"""
        if not self.room_ids:
            self.logger.error("必须提供直播间ID(room_id或room_ids)参数")
            return
        
        # 记录每个房间ID并生成item
        for room_id in self.room_ids:
            self.logger.info(f"处理房间ID: {room_id}")
            
            # 创建Item对象
            item = RoomIDItem()
            item['room_id'] = int(room_id)
            item['first_seen'] = datetime.now(timezone.utc)
            item['last_checked'] = datetime.now(timezone.utc)
            item['source'] = 'api_spider'
            item['note'] = 'Added via spider API'
            
            # 直接将Item传递给Pipeline处理
            yield item 