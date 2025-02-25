# config.py

class Config:
    """
    用来存储和管理全局配置信息
    """
    def __init__(self):
        self.ip_address = '127.0.0.1'
        self.start_port = 23330
        self.end_port = 23340
        self.filename = 'cookies.txt'
        self.fleet_size = 8

    def to_dict(self):
        """
        如果你需要以字典形式获取配置，可使用此方法
        """
        return {
            'ip_address': self.ip_address,
            'start_port': self.start_port,
            'end_port': self.end_port,
            'filename': self.filename,
            'fleet_size': self.fleet_size
        }
