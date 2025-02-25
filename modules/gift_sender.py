import subprocess
import os
import traceback

class GiftSender:
    """
    用于通过子进程执行送礼物脚本。
    """
    def __init__(self, workdir="./missions/send_gift"):
        # 脚本所在目录
        self.workdir = os.path.expanduser(workdir)

    def send_gift(self, room_id, num, account, gift_id):
        """
        调用sendGold.py脚本发送礼物
        """
        try:
            # 这里的sendGold.py需在self.workdir目录下存在
            subprocess.run(
                [
                    "python",
                    "sendGold.py",
                    "--room-id", str(room_id),
                    "--num", str(num),
                    "--account", account,
                    "--gift-id", gift_id
                ],
                cwd=self.workdir,
                check=True,
                timeout=15  # 防止卡死
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"运行 sendGold.py 超时: {str(e)}")
        except subprocess.CalledProcessError as e:
            # 当脚本返回非0码时抛出此异常
            raise RuntimeError(f"sendGold.py 返回非0状态: {str(e)}")
        except Exception as e:
            # 其他未知错误
            traceback.print_exc()
            raise RuntimeError(f"调用子进程异常: {str(e)}")
