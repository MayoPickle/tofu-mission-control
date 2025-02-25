import subprocess
import os
import traceback

class DanmakuSender:
    """
    用于通过子进程执行发送弹幕脚本。
    """
    def __init__(self, workdir="./missions/danmaku/sendDanmaku"):
        """
        :param workdir: 存放 sendDanmaku.py 脚本的目录
        """
        self.workdir = os.path.expanduser(workdir)

    def send_danmaku(self, room_id, danmaku):
        """
        调用 sendDanmaku.py 脚本发送弹幕
        """
        try:
            # 确保 sendDanmaku.py 存在于 self.workdir 目录下
            subprocess.run(
                [
                    "python",
                    "main.py",
                    "--room-id", str(room_id),
                    "--danmaku", danmaku
                ],
                cwd=self.workdir,
                check=True,
                timeout=15  # 防止脚本卡死
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"运行 sendDanmaku 超时: {str(e)}")
        except subprocess.CalledProcessError as e:
            # 当脚本返回非0码时抛出此异常
            raise RuntimeError(f"sendDanmaku 返回非0状态: {str(e)}")
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"调用子进程异常: {str(e)}")
