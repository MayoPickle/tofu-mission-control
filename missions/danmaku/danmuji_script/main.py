# main.py

import sys
import time
import argparse

# 导入自己的模块
from config import Config
from config_utils import ConfigUtils
from room_data_manager import RoomDataManager
from cookie_manager import CookieManager
from request_manager import RequestManager

def get_fleet_nums(config):
    """
    让用户输入需要调度的 fleet 编号 (如 '1,2,3'),
    若输入0或空则返回全部可用 fleet 范围。
    """
    fleet_nums_input = input("Enter the fleet numbers to dispatch (e.g., '1,2,3'), or '0' for all fleets: ")
    if not fleet_nums_input or fleet_nums_input == '0':
        total_fleets = (config.end_port - config.start_port + 1) // config.fleet_size
        return list(range(1, total_fleets + 1))
    return [int(num.strip()) for num in fleet_nums_input.split(',')]

def calculate_ports(config, fleet_nums):
    """根据 fleet_nums 计算出对应的端口列表"""
    if not fleet_nums or fleet_nums == '0':
        fleet_nums = list(range(1, (config.end_port - config.start_port + 1) // config.fleet_size + 1))

    ports = []
    for num in fleet_nums:
        start_port = config.start_port + (num - 1) * config.fleet_size
        end_port = start_port + config.fleet_size - 1
        ports.extend(range(start_port, end_port + 1))
    return ports

def main():
    parser = argparse.ArgumentParser(description="Control connection operations.")
    parser.add_argument('-d', '--disconnect', action='store_true', help='Only send disconnect requests')
    parser.add_argument('-s', '--single', action='store_true', help='Use single-threaded mode for requests')
    parser.add_argument('-q', '--quiet', action='store_true', help='Send /quit GET request to all ports')
    parser.add_argument('-l', '--login', action='store_true', help='Send login requests with cookies data to ports')
    parser.add_argument('-c', '--config', nargs='?', const=None, default=-1,
                        help='Optional: Sleep for specified seconds and then load the default configuration file')
    parser.add_argument('-m', '--message', type=str, help='Store a custom message')
    args = parser.parse_args()

    # 初始化全局配置
    config = Config()
    # 初始化辅助类
    request_manager = RequestManager(config)
    cookie_manager = CookieManager(config)
    room_manager = RoomDataManager()

    # 询问 fleet_nums & 计算对应端口
    fleet_nums = get_fleet_nums(config)
    ports = calculate_ports(config, fleet_nums)

    try:
        if args.config != -1:
            # 用户希望先选一个 config 文件并发送
            config_file = ConfigUtils.choose_config_file()
            if config_file:
                config_file_data = ConfigUtils.update_config_from_file(config_file)
                # 逐个发送
                for port in ports:
                    request_url = f"http://{config.ip_address}:{port}/sendSet"
                    data = {'set': config_file_data}
                    request_manager.send_request(request_url, method='post', data=data, headers=None)
            else:
                print("No config file selected or available.")

            # 如果 -c 后面跟了数字, 就 sleep 并发送默认配置
            if args.config is not None and str(args.config).isdigit() and int(args.config) > 0:
                time.sleep(int(args.config))
                config_file = "./config/set-default-idle.json"
                config_file_data = ConfigUtils.update_config_from_file(config_file)
                for port in ports:
                    request_url = f"http://{config.ip_address}:{port}/sendSet"
                    data = {'set': config_file_data}
                    request_manager.send_request(request_url, method='post', data=data, headers=None)
            return
        
    except KeyboardInterrupt:
        print("Interrupt received, updating default configuration...")
        config_file = "./config/set-default-idle.json"
        config_file_data = ConfigUtils.update_config_from_file(config_file)
        for port in ports:
            request_url = f"http://{config.ip_address}:{port}/sendSet"
            data = {'set': config_file_data}
            request_manager.send_request(request_url, method='post', data=data, headers=None)
        print("Default configuration updated on interrupt.")
        sys.exit(0)

    # 如果指定了 -m --message，则处理广告更新逻辑
    if args.message:
        config_file_path = "./config/set-custom-ad-template.json"
        config_file_data_false = ConfigUtils.update_advert_in_config(config_file_path, "", False)
        config_file_data_true_list = []

        if '+' in args.message:
            # 如果消息里包含 '+' 则拆分多段
            splitted = args.message.split('+')
            for msg_piece in splitted:
                cfg_data_true = ConfigUtils.update_advert_in_config(config_file_path, msg_piece, True)
                config_file_data_true_list.append(cfg_data_true)
        else:
            # 否则，就只对端口数量重复相同消息
            for _ in ports:
                cfg_data_true = ConfigUtils.update_advert_in_config(config_file_path, args.message, True)
                config_file_data_true_list.append(cfg_data_true)
        
        request_manager.send_requests_in_parallel(ports, config_file_data_true_list, config_file_data_false, args.single)
        return

    # 如果 -q --quiet 为 True，则调用 /quiet
    if args.quiet:
        request_manager.process_requests(args.single, ports, endpoint="quiet", param=None)
        return

    # 如果 -d --disconnect 为 True，则调用 /disconnectRoom
    if args.disconnect:
        request_manager.process_requests(args.single, ports, endpoint="disconnectRoom", param=None)
        return

    # 如果 -l --login 为 True，发送 cookies
    if args.login:
        cookie_manager.read_and_send_cookies(config.filename, ports[0], ports[-1])
        return

    # =============== 默认操作：选择房间并连接 ===============

    room_data = room_manager.load_room_data()
    chosen_room_id = room_manager.get_user_choice(room_data)

    # 先断开，再连接
    request_manager.process_requests(args.single, ports, endpoint="disconnectRoom", param=None)
    param = f"roomid={chosen_room_id}"
    request_manager.process_requests(args.single, ports, endpoint="connectRoom", param=param)


if __name__ == "__main__":
    main()
