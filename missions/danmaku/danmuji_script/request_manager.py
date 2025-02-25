# request_manager.py

import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

class RequestManager:
    def __init__(self, config):
        """
        :param config: config.py 中的 Config 实例
        """
        self.config = config

    def send_request(self, url, method='get', data=None, headers=None, delay=0):
        """
        发送指定类型的HTTP请求。

        :param url: 完整URL
        :param method: HTTP方法 get/post/put/delete 等
        :param data: POST/PUT请求携带的数据
        :param headers: 请求头
        :param delay: 请求前等待秒数
        :return: 返回字符串描述 (可自定义更多信息)
        """
        if delay:
            time.sleep(delay)
        try:
            method_lower = method.lower()
            if method_lower == 'get':
                response = requests.get(url, headers=headers)
            elif method_lower == 'post':
                response = requests.post(url, data=data, headers=headers)
            elif method_lower == 'put':
                response = requests.put(url, data=data, headers=headers)
            elif method_lower == 'delete':
                response = requests.delete(url, headers=headers)
            else:
                return f"Unsupported HTTP method: {method}"

            result_info = f"URL: {url}, Status: {response.status_code}, Response: {response.text}"
            print(result_info)
            return result_info

        except requests.RequestException as e:
            error_info = f"Error connecting to {url}: {e}"
            print(error_info)
            return error_info

    def handle_requests_concurrent(self, request_urls):
        results = []
        with ThreadPoolExecutor(max_workers=len(request_urls)) as executor:
            future_to_url = {executor.submit(self.send_request, url): url for url in request_urls}
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
        return results

    def handle_requests(self, request_urls):
        results = []
        for url in request_urls:
            result = self.send_request(url)
            results.append(result)
        return results

    def process_requests(self, single_threaded, ports, endpoint=None, param=""):
        """
        根据 single_threaded 决定是否并发请求；拼接端口、endpoint、param生成完整URL。
        """
        request_urls = [f"http://{self.config.ip_address}:{port}/{endpoint}" for port in ports]
        if param:
            request_urls = [url + f"?{param}" for url in request_urls]

        if single_threaded:
            self.handle_requests(request_urls)
        else:
            self.handle_requests_concurrent(request_urls)

    def send_quit_request(self, port):
        url = f"http://{self.config.ip_address}:{port}/quit"
        response = requests.get(url)
        print(f"Sent /quit to port {port}: {response.status_code}")

    def send_requests_in_parallel(self, ports, config_file_data_true_list, config_file_data_false, single_threaded):
        """
        按照你原有逻辑，将多次 config 更新请求并发/串行地发送出去
        """
        if single_threaded:
            # 单线程
            if len(config_file_data_true_list) == 1:
                for port in ports:
                    request_url = f"http://{self.config.ip_address}:{port}/sendSet"
                    config_data_true = config_file_data_true_list[0]
                    self.send_request(request_url, "post", {'set': config_data_true})
                    time.sleep(5)
                    self.send_request(request_url, "post", {'set': config_file_data_false})
            else:
                config_file_index = 0
                ports_index = 0
                while config_file_index < len(config_file_data_true_list):
                    if ports_index >= len(ports):
                        ports_index = 0
                    request_url = f"http://{self.config.ip_address}:{ports[ports_index]}/sendSet"

                    config_data_true = config_file_data_true_list[config_file_index]
                    self.send_request(request_url, "post", {'set': config_data_true})
                    time.sleep(5)
                    self.send_request(request_url, "post", {'set': config_file_data_false})

                    ports_index += 1
                    config_file_index += 1
        else:
            # 多线程
            with ThreadPoolExecutor(max_workers=len(ports)) as executor:
                future_to_url = {}
                if len(config_file_data_true_list) == 1:
                    for port in ports:
                        request_url = f"http://{self.config.ip_address}:{port}/sendSet"
                        config_data_true = config_file_data_true_list[0]
                        f1 = executor.submit(self.send_request, request_url, "post", {'set': config_data_true})
                        future_to_url[f1] = request_url
                        f2 = executor.submit(self.send_request, request_url, "post", {'set': config_file_data_false}, delay=5)
                        future_to_url[f2] = request_url
                else:
                    config_file_index = 0
                    ports_index = 0
                    while config_file_index < len(config_file_data_true_list):
                        if ports_index >= len(ports):
                            ports_index = 0
                        request_url = f"http://{self.config.ip_address}:{ports[ports_index]}/sendSet"
                        
                        f1 = executor.submit(self.send_request, request_url, "post", {'set': config_file_data_true_list[config_file_index]})
                        future_to_url[f1] = request_url
                        f2 = executor.submit(self.send_request, request_url, "post", {'set': config_file_data_false}, delay=5)
                        future_to_url[f2] = request_url

                        ports_index += 1
                        config_file_index += 1

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        print(result)
                    except Exception as exc:
                        print(f"{url} generated an exception: {exc}")
