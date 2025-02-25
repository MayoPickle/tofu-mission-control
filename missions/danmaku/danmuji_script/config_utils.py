# config_utils.py

import os
import json
import inquirer

class ConfigUtils:
    @staticmethod
    def list_config_files(directory):
        """列出指定目录中的所有 JSON 文件."""
        return [f for f in os.listdir(directory) if f.endswith('.json')]

    @staticmethod
    def choose_config_file(directory='./config'):
        """让用户从列表中选择一个配置文件."""
        files = ConfigUtils.list_config_files(directory)
        if not files:
            print("No configuration files found.")
            return None
        question = [inquirer.List('config', message="Choose a configuration file", choices=files)]
        answer = inquirer.prompt(question)
        return os.path.join(directory, answer['config'])

    @staticmethod
    def update_config_from_file(config_path):
        """从指定的 JSON 文件读取内容并返回其字符串形式."""
        with open(config_path, 'r', encoding='utf-8') as file:
            file_config = json.load(file)
        # 将字典转换为 JSON 字符串
        json_string = json.dumps(file_config)
        return json_string

    @staticmethod
    def update_advert_in_config(config_path, new_advert_text, is_enabled):
        """
        更新 JSON 配置文件中的 'advert' 参数，包括文本和启用状态。
        返回更新后的 JSON 字符串，不会直接写回文件。
        """
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = json.load(file)

        # 检查 'advert' 字段并更新
        if 'advert' in config_data:
            if 'adverts' in config_data['advert']:
                config_data['advert']['adverts'] = new_advert_text
            config_data['advert']['is_open'] = is_enabled

        updated_json_string = json.dumps(config_data, indent=4)
        return updated_json_string
