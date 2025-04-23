#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
import time
import json
import os
import threading
import concurrent.futures

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

def perform_like_for_account(account, cookies, headers, room_id, like_times):
    """为单个账号执行点赞任务"""
    # 获取主播 UID 和自己的 UID
    anchor_uid = get_anchor_uid(room_id, headers, cookies)
    self_uid = get_self_uid(headers, cookies)
    
    if not anchor_uid or not self_uid:
        print(f"[ERROR] 账号 {account} 获取UID失败，跳过点赞")
        return 0
    
    # 使用 V1 点赞接口
    url_v1 = 'https://api.live.bilibili.com/xlive/web-ucenter/v1/interact/likeInteract'
    data_v1 = {
        'roomid': str(room_id),
        'csrf': cookies.get('bili_jct', ''),
        'csrf_token': cookies.get('bili_jct', ''),
        'visit_id': ''
    }
    
    # 使用 V3 点赞接口
    url_v3 = 'https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3'
    data_v3 = {
        'room_id': str(room_id),
        'anchor_id': str(anchor_uid),
        'uid': str(self_uid),
        'csrf': cookies.get('bili_jct', ''),
        'csrf_token': cookies.get('bili_jct', ''),
        'visit_id': '',
        'click_time': '1'
    }
    
    batch_size = 100  # 每100次点赞显示一次进度
    like_success = 0
    
    print(f"[INFO] 账号 {account} 开始点赞，计划点赞 {like_times} 次")
    
    for i in range(like_times):
        try:
            # 只在每批次开始或结束时显示进度
            if i % batch_size == 0 or i == like_times - 1:
                print(f"[INFO] 账号 {account} 正在点赞: {i+1}/{like_times}")
            
            # 先尝试 V3 接口
            response = requests.post(url_v3, headers=headers, cookies=cookies, data=data_v3)
            
            # 如果 V3 接口失败，尝试 V1 接口
            if response.status_code != 200 or response.json().get('code', -1) != 0:
                if i % batch_size == 0:  # 只在每批次开始时记录警告
                    print(f"[WARNING] 账号 {account} 使用 V3 接口点赞失败，尝试 V1 接口")
                response = requests.post(url_v1, headers=headers, cookies=cookies, data=data_v1)
            
            # 检查结果
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('code') == 0:
                    like_success += 1
                    # 只在特定位置显示成功信息，避免大量日志输出
                    if i % batch_size == 0 or i == like_times - 1:
                        print(f"[INFO] 账号 {account} 第 {i+1} 次点赞成功")
                else:
                    # 只在特定位置显示错误信息
                    if i % batch_size == 0:
                        print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞失败: {resp_json.get('message')}")
            else:
                # 只在特定位置显示错误信息
                if i % batch_size == 0:
                    print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞请求失败, HTTP状态码: {response.status_code}")
                    print("响应内容:", response.text)
            
            # 短暂延迟，避免频率限制
            if i < like_times - 1:
                time.sleep(0.1)  # 减少延迟以加快点赞速度
                
        except Exception as e:
            # 只在特定位置显示错误信息
            if i % batch_size == 0:
                print(f"[ERROR] 账号 {account} 第 {i+1} 次点赞发生异常: {str(e)}")
    
    print(f"[INFO] 账号 {account} 完成点赞任务，成功 {like_success}/{like_times} 次")
    return like_success

def main():
    parser = argparse.ArgumentParser(description='Send Like to Bilibili Live Room.')
    parser.add_argument('--room-id', required=True, help='房间 ID')
    parser.add_argument('--cookie-path', default='../../account_cookies.json',
                        help='account_cookies.json 文件路径(默认为 ../../account_cookies.json)')
    parser.add_argument('--like-times', type=int, default=1000, help='点赞次数(默认为1000)')
    parser.add_argument('--accounts', type=str, default='all', help='使用的账号，多个账号用逗号分隔，或使用"all"表示所有账号')
    parser.add_argument('--max-workers', type=int, default=5, help='最大并行线程数(默认为5)')
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
    
    # 多线程执行点赞任务
    futures = []
    max_workers = min(args.max_workers, len(valid_accounts))  # 限制最大线程数
    print(f"[INFO] 使用 {max_workers} 个线程同时执行点赞任务")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for account in valid_accounts:
            # 获取当前账号的 cookie 字符串
            cookie_str = all_cookies_data[account]['cookie'].strip()

            # 将 cookie 字符串解析为 dict
            cookies = {}
            for c in cookie_str.split(';'):
                c = c.strip()
                if '=' in c:
                    key, value = c.split('=', 1)
                    cookies[key.strip()] = value.strip()

            # 构造请求头
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
            
            # 提交任务到线程池
            future = executor.submit(
                perform_like_for_account,
                account,
                cookies,
                headers,
                args.room_id,
                args.like_times
            )
            futures.append((account, future))
    
    # 收集结果
    success_count = 0
    for account, future in futures:
        like_success = future.result()
        if like_success > 0:
            success_count += 1
    
    print(f"[INFO] 所有点赞任务完成，共有 {success_count}/{len(valid_accounts)} 个账号成功发送点赞")

if __name__ == '__main__':
    main() 