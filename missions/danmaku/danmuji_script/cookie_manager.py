# cookie_manager.py

import requests

class CookieManager:
    def __init__(self, config):
        """
        :param config: config.py 中的 Config 实例
        """
        self.config = config

    def send_post_request(self, port, cookie_data):
        url = f"http://{self.config.ip_address}:{port}/customCookie"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'cookie': cookie_data}
        response = requests.post(url, headers=headers, data=data)
        print(f"Response from server on port {port}: {response.status_code} - {response.text}")

    def read_and_send_cookies(self, filename, start_port, end_port):
        """
        从文件里读取两行一组(用户备注 + cookie_data)，然后依次发送到指定端口范围
        """
        with open(filename, 'r', encoding="utf-8") as file:
            lines = file.readlines()

        port = start_port
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                user_remark = lines[i].strip()
                cookie_data = lines[i+1].strip()
                if port <= end_port:
                    self.send_post_request(port, cookie_data)
                    print(f"Sent data for {user_remark} to port {port} with {cookie_data}")
                    port += 1
