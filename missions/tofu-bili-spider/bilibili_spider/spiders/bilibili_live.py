import scrapy
import json
import logging
from scrapy.http import Request
from datetime import datetime
from bilibili_spider.items import LiveRoomItem

class BilibiliLiveSpider(scrapy.Spider):
    name = "bilibili_live"
    allowed_domains = ["bilibili.com"]
    
    def __init__(self, room_ids=None, room_id=None, *args, **kwargs):
        super(BilibiliLiveSpider, self).__init__(*args, **kwargs)
        
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
        """构造 API 请求"""
        if not self.room_ids:
            self.logger.error("必须提供直播间ID(room_id或room_ids)参数")
            return
        
        # 添加指定的请求头
        headers = {
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        }
        
        for room_id in self.room_ids:
            url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id}"
            self.logger.info(f"开始爬取直播间 {room_id}")
            
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.errback_handler,
                meta={'room_id': room_id},
                headers=headers  # 使用自定义请求头
            )

    def parse(self, response):
        """解析 JSON 数据"""
        try:
            data = json.loads(response.text)
            if data["code"] != 0:
                self.logger.error(f"爬取失败，返回错误: {data['message']}")
                self.logger.error(f"完整响应内容: {response.text}")
                return

            # 提取所需的数据字段
            room_info = data["data"]["room_info"]
            anchor_info = data["data"]["anchor_info"]["base_info"]
            watched_show = data.get("data", {}).get("watched_show", {})
            
            # 构建基础URL
            live_url = f"https://live.bilibili.com/{room_info['room_id']}"

            # 创建直播间数据项
            item = LiveRoomItem()
            item['room_id'] = room_info["room_id"]
            item['uid'] = room_info["uid"]
            item['title'] = room_info["title"]
            item['uname'] = anchor_info["uname"]
            item['online'] = room_info["online"]
            item['user_cover'] = None  # API中未提供
            item['system_cover'] = None  # API中未提供
            item['cover'] = room_info["cover"]
            item['link'] = live_url
            item['face'] = anchor_info["face"]
            item['parent_id'] = room_info["parent_area_id"]
            item['parent_name'] = room_info["parent_area_name"]
            item['area_id'] = room_info["area_id"]
            item['area_name'] = room_info["area_name"]
            item['area_v2_id'] = room_info["area_id"]  # 假设V2分区ID与area_id相同
            item['area_v2_name'] = room_info["area_name"]  # 假设V2分区名称与area_name相同
            item['session_id'] = room_info.get("up_session")
            item['group_id'] = None  # API中未提供
            item['show_callback'] = None  # API中未提供
            item['click_callback'] = None  # API中未提供
            item['watched_num'] = watched_show.get("num")
            item['watched_text'] = watched_show.get("text_large")
            item['timestamp'] = datetime.utcnow()  # 添加当前时间戳

            # 记录日志
            self.logger.info(f"成功获取直播间 {item['room_id']} 的数据")
            
            # 输出一些关键信息
            self.logger.info(f"直播间标题: {item['title']}")
            self.logger.info(f"主播名称: {item['uname']}")
            self.logger.info(f"在线人数: {item['online']}")
            self.logger.info(f"分区: {item['parent_name']}/{item['area_name']}")
            
            # 将数据项返回给Pipeline处理
            yield item
            
        except Exception as e:
            self.logger.error(f"解析或处理数据时出错: {e}")
            raise
    
    def errback_handler(self, failure):
        """处理请求失败的情况"""
        request = failure.request
        self.logger.error(f"请求失败: {failure.value}")
        self.logger.error(f"请求URL: {request.url}")
        # 如果需要，可以在这里重试请求或进行其他错误处理
