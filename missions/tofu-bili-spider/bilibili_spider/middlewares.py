# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
import random
import logging
import time
import json
import os
from dotenv import load_dotenv
from scrapy.http import HtmlResponse
from urllib.parse import urlparse
from base64 import b64encode

# 加载环境变量
load_dotenv()

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class BilibiliSpiderSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn't have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class BilibiliSpiderDownloaderMiddleware:
    # B站User-Agent列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    ]

    def __init__(self):
        # 获取代理配置
        self.proxy_host = os.getenv('PROXY_HOST')
        self.proxy_port = os.getenv('PROXY_PORT')
        self.proxy_user = os.getenv('PROXY_USER')
        self.proxy_pass = os.getenv('PROXY_PASS')
        
        # 构建代理URL（不包含认证信息）
        self.proxy = f"http://{self.proxy_host}:{self.proxy_port}"
        self.proxy_user_pass = f"{self.proxy_user}:{self.proxy_pass}"
        self.logger = logging.getLogger('BilibiliSpiderDownloaderMiddleware')
        self.logger.info(f"代理已配置: {self.proxy_host}:{self.proxy_port}")

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # 不再设置随机User-Agent，使用spider中指定的
        # ua = random.choice(self.USER_AGENTS)
        # request.headers['User-Agent'] = ua
        
        # 设置代理，使用与curl相同的方式
        if self.proxy_host and self.proxy_port:
            # 设置代理服务器
            request.meta['proxy'] = self.proxy
            
            # 如果有代理认证信息，单独设置
            if self.proxy_user and self.proxy_pass:
                # 设置代理认证，这与 curl --proxy-user 参数等效
                proxy_auth = b64encode(f"{self.proxy_user}:{self.proxy_pass}".encode()).decode()
                request.headers['Proxy-Authorization'] = f'Basic {proxy_auth}'
                
            spider.logger.debug(f"使用代理: {self.proxy}")
        
        # 不再为B站API请求添加额外的请求头
        # if 'api.live.bilibili.com' in request.url:
        #    # 添加请求头代码已移除
            
        return None

    def process_response(self, request, response, spider):
        # 处理响应
        if response.status in [412, 429]:
            spider.logger.warning(f"请求被限制，状态码: {response.status}, URL: {request.url}")
            # 睡眠一段时间
            time.sleep(random.uniform(3, 5))
            
            # 如果是412/429错误，可能需要更换headers后重试
            return request.replace(dont_filter=True)
        
        # 检查API响应是否正常
        if 'api.live.bilibili.com' in request.url:
            try:
                # 尝试解析JSON
                data = json.loads(response.text)
                if data.get('code') != 0:
                    # 如果返回的code不是0，记录错误
                    spider.logger.error(f"API返回错误: {data.get('code')}, URL: {request.url}")
                    spider.logger.error(f"错误信息: {data.get('message')}")
                    spider.logger.error(f"完整响应: {response.text}")
                    
                    # 如果是IP被限制的错误，可能需要暂停或提醒
                    if data.get('code') in [-412, -403, 412, 403]:
                        spider.logger.critical(f"IP可能被封禁或限制，错误码: {data.get('code')}")
                        # 增加更长的等待时间
                        time.sleep(random.uniform(10, 15))
                        # 重试请求
                        return request.replace(dont_filter=True)
            except json.JSONDecodeError:
                spider.logger.error(f"响应不是有效的JSON: {response.text[:100]}...")
        
        return response

    def process_exception(self, request, exception, spider):
        # 处理请求异常
        spider.logger.error(f"请求异常: {exception}, URL: {request.url}")
        # 等待一段时间后重试
        time.sleep(random.uniform(2, 5))
        return request.replace(dont_filter=True)

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
