import requests
import argparse
import json
import os

API_URL = "https://api.live.bilibili.com/xlive/revenue/v1/gift/sendGold"

# 读取账号 Cookie 配置
account_config_file = "../account_cookies.json"
if not os.path.exists(account_config_file):
    print(f"❌ 账号配置文件 {account_config_file} 不存在！")
    exit(1)

with open(account_config_file, "r") as f:
    account_cookies = json.load(f)

# 读取礼物价格列表
price_list_file = "price_list.json"
if not os.path.exists(price_list_file):
    print(f"❌ 礼物价格列表文件 {price_list_file} 不存在！")
    exit(1)

with open(price_list_file, "r") as f:
    price_list = json.load(f)


def get_anchor_uid(room_id, headers):
    """获取直播间的主播 UID"""
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    response = requests.get(url, headers=headers, params={"room_id": room_id})

    if response.status_code == 200:
        data = response.json()
        if data["code"] == 0 and "data" in data and "uid" in data["data"]:
            ruid = data["data"]["uid"]
            print(f"✅ 直播间 {room_id} 主播 UID: {ruid}")
            return ruid
        else:
            print(f"❌ API 响应异常: {data}")
    else:
        print(f"❌ 获取主播 UID 失败，HTTP 状态码: {response.status_code}")

    return None


def send_gift(room_id, num, account, gift_id):
    """发送礼物"""
    if account not in account_cookies:
        print(f"❌ 账号 {account} 未找到，请检查 {account_config_file}！")
        return

    if str(gift_id) not in price_list:
        print(f"❌ 礼物 ID {gift_id} 不在 {price_list_file}，请检查！")
        return

    gift_price = price_list[str(gift_id)]

    # 获取账号 Cookie
    cookie = account_cookies[account]["cookie"]
    bili_jct = next((x.split("=")[1] for x in cookie.split("; ") if x.startswith("bili_jct=")), None)
    if not bili_jct:
        print(f"❌ 账号 {account} 的 cookie 配置有误，缺少 bili_jct！")
        return

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://live.bilibili.com",
        "referer": "https://live.bilibili.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "cookie": cookie,
    }

    ruid = get_anchor_uid(room_id, headers)
    if not ruid:
        print(f"❌ 无法获取直播间 {room_id} 的主播 UID！")
        return

    data = {
        "uid": ruid,
        "gift_id": gift_id,
        "ruid": ruid,
        "send_ruid": 0,
        "gift_num": num,
        "coin_type": "gold",
        "bag_id": 0,
        "platform": "pc",
        "biz_code": "Live",
        "biz_id": room_id,
        "storm_beat_id": 0,
        "metadata": "",
        "price": gift_price,
        "receive_users": "",
        "live_statistics": '{"pc_client":"pcWeb","jumpfrom":"82002","room_category":"0","source_event":0,"official_channel":{"program_room_id":"-99998","program_up_id":"-99998"}}',
        "statistics": '{"platform":5,"pc_client":"pcWeb","appId":100}',
        "csrf_token": bili_jct,
        "csrf": bili_jct,
        "visit_id": "",
    }

    response = requests.post(API_URL, headers=headers, data=data)

    if response.status_code == 200:
        result = response.json()
        if result["code"] == 0:
            print(f"✅ 成功送出 {num} 个礼物（ID: {gift_id}，单价 {gift_price}）到直播间 {room_id}！")
        else:
            print(f"❌ 送礼失败：{result['message']}")
    else:
        print(f"❌ 请求失败，HTTP 状态码: {response.status_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="B 站直播送礼 Python 脚本")
    parser.add_argument("--room-id", type=int, required=True, help="直播间 ID")
    parser.add_argument("--num", type=int, required=True, help="送礼数量")
    parser.add_argument("--account", type=str, required=True, help="使用的账号名称")
    parser.add_argument("--gift-id", type=int, required=True, help="送礼的礼物 ID")
    args = parser.parse_args()

    send_gift(args.room_id, args.num, args.account, args.gift_id)
