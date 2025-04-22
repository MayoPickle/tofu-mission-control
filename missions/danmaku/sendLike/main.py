#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
import time
import json
import os

def get_anchor_uid(room_id, headers, cookies):
    """获取直播间的主播 UID"""
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    response = requests.get(url, headers=headers, cookies=cookies, params={"room_id": room_id})

    if response.status_code == 200:
        data = response.json()
        if data["code"] == 0 and "data" in data and "uid" in data["data"]:
            ruid = data["data"]["uid"]
            print(f"[INFO] 直播间 {room_id} 主播 UID: {ruid}")
            return ruid
        else:
            print(f"[ERROR] API 响应异常: {data}")
    else:
        print(f"[ERROR] 获取主播 UID 失败，HTTP 状态码: {response.status_code}")

    return None

def get_self_uid(headers, cookies):
    """获取自己的 UID"""
    url = "https://api.bilibili.com/x/web-interface/nav"
    response = requests.get(url, headers=headers, cookies=cookies)

    if response.status_code == 200:
        data = response.json()
        if data["code"] == 0 and "data" in data and "mid" in data["data"]:
            uid = data["data"]["mid"]
            print(f"[INFO] 当前用户 UID: {uid}")
            return uid
        else:
            print(f"[ERROR] API 响应异常: {data}")
    else:
        print(f"[ERROR] 获取用户 UID 失败，HTTP 状态码: {response.status_code}")

    return None

def main():
    parser = argparse.ArgumentParser(description='Send Like to Bilibili Live Room.')
    parser.add_argument('--room-id', required=True, help='房间 ID')
    parser.add_argument('--cookie-path', default='../../account_cookies.json',
                        help='account_cookies.json 文件路径(默认为 ../../account_cookies.json)')
    parser.add_argument('--like-times', type=int, default=5, help='点赞次数(默认为5)')
    parser.add_argument('--accounts', type=str, default='all', help='使用的账号，多个账号用逗号分隔，或使用"all"表示所有账号')
    args = parser.parse_args()

    # 1) 读取 JSON 文件
    cookie_json_path = os.path.abspath(args.cookie_path)
    if not os.path.exists(cookie_json_path):
        print(f"[ERROR] 找不到指定的 JSON 文件: {cookie_json_path}")
        return

    with open(cookie_json_path, 'r', encoding='utf-8') as f:
        all_cookies_data = json.load(f)

    # 2) 确定要使用的账号列表
    if args.accounts.lower() == 'all':
        account_list = list(all_cookies_data.keys())
    else:
        account_list = [acc.strip() for acc in args.accounts.split(',')]

    # 检查账号列表是否在 cookie 文件中
    valid_accounts = [acc for acc in account_list if acc in all_cookies_data and 'cookie' in all_cookies_data[acc]]
    
    if not valid_accounts:
        print("[ERROR] 没有找到有效的账号信息。")
        return
    
    print(f"[INFO] 将使用以下账号为直播间 {args.room_id} 点赞: {', '.join(valid_accounts)}")

    # 对每个账号发送点赞
    success_count = 0
    for account in valid_accounts:
        # 3) 获取当前账号的 cookie 字符串
        cookie_str = all_cookies_data[account]['cookie'].strip()

        # 4) 将 cookie 字符串解析为 dict
        cookies = {}
        for c in cookie_str.split(';'):
            c = c.strip()
            if '=' in c:
                key, value = c.split('=', 1)
                cookies[key.strip()] = value.strip()

        # 5) 构造请求头
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://live.bilibili.com',
            'referer': f'https://live.bilibili.com/{args.room_id}',
            'sec-ch-ua': '"Google Chrome";v="133", "Chromium";v="133", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/133.0.0.0 Safari/537.36'
        }

        # 6) 获取主播 UID 和自己的 UID
        anchor_uid = get_anchor_uid(args.room_id, headers, cookies)
        self_uid = get_self_uid(headers, cookies)
        
        if not anchor_uid or not self_uid:
            print(f"[ERROR] 账号 {account} 获取UID失败，跳过点赞")
            continue

        # 7) 发送 POST 请求到 Bilibili 点赞接口 (V3)
        like_success = 0
        
        # 使用 V1 点赞接口
        url_v1 = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/interact/likeInteract'
        data_v1 = {
            'roomid': str(args.room_id),
            'csrf': cookies.get('bili_jct', ''),
            'csrf_token': cookies.get('bili_jct', ''),
            'visit_id': ''
        }
        
        # 使用 V3 点赞接口
        url_v3 = 'https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3'
        data_v3 = {
            'room_id': str(args.room_id),
            'anchor_id': str(anchor_uid),
            'uid': str(self_uid),
            'csrf': cookies.get('bili_jct', ''),
            'csrf_token': cookies.get('bili_jct', ''),
            'visit_id': '',
            'click_time': '1'
        }
        
        for i in range(args.like_times):
            try:
                # 先尝试 V3 接口
                response = requests.post(url_v3, headers=headers, cookies=cookies, data=data_v3)
                
                # 如果 V3 接口失败，尝试 V1 接口
                if response.status_code != 200 or response.json().get('code', -1) != 0:
                    print(f"[WARNING] 账号 {account} 使用 V3 接口点赞失败，尝试 V1 接口")
                    response = requests.post(url_v1, headers=headers, cookies=cookies, data=data_v1)
                
                # 检查结果
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get('code') == 0:
                        like_success += 1
                        print(f"[INFO] 账号 {account} 第 {i+1} 次点赞成功")
                    else:
                        print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞失败: {resp_json.get('message')}")
                else:
                    print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞请求失败, HTTP状态码: {response.status_code}")
                    print("响应内容:", response.text)
                
                # 短暂延迟，避免频率限制
                if i < args.like_times - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞发生异常: {str(e)}")
        
        if like_success > 0:
            success_count += 1
            print(f"[INFO] 账号 {account} 成功点赞 {like_success}/{args.like_times} 次")
    
    print(f"[INFO] 点赞任务完成，共有 {success_count}/{len(valid_accounts)} 个账号成功发送点赞")

if __name__ == '__main__':
    main() 