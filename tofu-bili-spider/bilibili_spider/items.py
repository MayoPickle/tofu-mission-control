# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BilibiliSpiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class LiveRoomItem(scrapy.Item):
    """B站直播间数据项"""
    room_id = scrapy.Field()
    uid = scrapy.Field()
    title = scrapy.Field()
    uname = scrapy.Field()
    online = scrapy.Field()
    user_cover = scrapy.Field()
    system_cover = scrapy.Field()
    cover = scrapy.Field()
    link = scrapy.Field()
    face = scrapy.Field()
    parent_id = scrapy.Field()
    parent_name = scrapy.Field()
    area_id = scrapy.Field()
    area_name = scrapy.Field()
    area_v2_id = scrapy.Field()
    area_v2_name = scrapy.Field()
    session_id = scrapy.Field()
    group_id = scrapy.Field()
    show_callback = scrapy.Field()
    click_callback = scrapy.Field()
    watched_num = scrapy.Field()
    watched_text = scrapy.Field()
    timestamp = scrapy.Field()
