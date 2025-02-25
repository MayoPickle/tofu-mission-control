#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
import time
import json
import os

def main():
    parser = argparse.ArgumentParser(description='Send Danmaku to Bilibili Live Room.')
    parser.add_argument('--room-id', required=True, help='房间 ID')
    parser.add_argument('--danmaku', required=True, help='发送的弹幕内容')
    parser.add_argument('--cookie-path', default='../../account_cookies.json',
                        help='account_cookies.json 文件路径(默认为 ../../account_cookies.json)')
    args = parser.parse_args()

    # 1) 读取 JSON 文件
    cookie_json_path = os.path.abspath(args.cookie_path)
    if not os.path.exists(cookie_json_path):
        print(f"[ERROR] 找不到指定的 JSON 文件: {cookie_json_path}")
        return

    with open(cookie_json_path, 'r', encoding='utf-8') as f:
        all_cookies_data = json.load(f)

    # 2) 检查是否存在 "sentry" 字段，以及其中的 "cookie"
    if 'sentry' not in all_cookies_data or 'cookie' not in all_cookies_data['sentry']:
        print("[ERROR] JSON 文件中不存在 'sentry.cookie' 字段，请检查文件内容。")
        return

    # 3) 获取 sentry 对应的 cookie 字符串
    sentry_cookie_str = all_cookies_data['sentry']['cookie'].strip()

    # 4) 将 cookie 字符串解析为 dict（以 "; " 分割，然后以 "=" 分割键值）
    #    示例: "SESSDATA=xxx; bili_jct=xxx" -> {"SESSDATA": "xxx", "bili_jct": "xxx"}
    cookies = {}
    for c in sentry_cookie_str.split(';'):
        c = c.strip()
        if '=' in c:
            key, value = c.split('=', 1)
            cookies[key.strip()] = value.strip()

    # 5) 构造请求头（根据需要微调）
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'origin': 'https://live.bilibili.com',
        'referer': f'https://live.bilibili.com/{args.room_id}',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/131.0.0.0 Safari/537.36'
    }

    # 6) 构造表单数据
    #    这里 rnd 可用 int(time.time()) 或自己生成；csrf 与 csrf_token 同为 cookies['bili_jct']
    data = {
        'bubble': '0',
        'msg': args.danmaku,
        'color': '16777215',
        'mode': '1',
        'fontsize': '25',
        'rnd': str(int(time.time())),
        'room_type': '0',
        'jumpfrom': '77002',
        'reply_mid': '0',
        'reply_attr': '0',
        'replay_dmid': '',
        'statistics': '{"appId":100,"platform":5}',
        'reply_type': '0',
        'reply_uname': '',
        'roomid': str(args.room_id),
        'csrf': cookies.get('bili_jct', ''),
        'csrf_token': cookies.get('bili_jct', '')
    }

    # 7) 发送 POST 请求到 Bilibili 弹幕接口
    url = 'https://api.live.bilibili.com/msg/send'
    response = requests.post(url, headers=headers, cookies=cookies, data=data)

    # 8) 检查结果
    if response.status_code == 200:
        print("[INFO] 弹幕发送成功:", args.danmaku)
    else:
        print("[ERROR] 弹幕发送失败, HTTP状态码:", response.status_code)
        print("响应内容:", response.text)


if __name__ == '__main__':
    main()
