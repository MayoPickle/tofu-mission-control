import subprocess
import os
import traceback

class LikeSender:
    """
    用于通过子进程执行发送点赞脚本。
    """
    def __init__(self, workdir="./missions/danmaku/sendLike"):
        """
        :param workdir: 存放 sendLike 脚本的目录
        """
        self.workdir = os.path.expanduser(workdir)

    def send_like(self, room_id, message=None, like_times=1000, accounts='all', max_workers=5):
        """
        调用 sendLike 脚本发送点赞
        
        :param room_id: 直播间 ID
        :param message: 可选，消息内容（为日志记录目的）
        :param like_times: 每个账号点赞次数，默认为 1000
        :param accounts: 指定账号，可以是 'all' 或者逗号分隔的账号名称，默认为 'all'
        :param max_workers: 最大并行线程数，默认为 5
        """
        try:
            cmd = [
                "python",
                "main.py",
                "--room-id", str(room_id),
                "--like-times", str(like_times),
                "--accounts", accounts,
                "--max-workers", str(max_workers)
            ]
            
            subprocess.run(
                cmd,
                cwd=self.workdir,
                check=True,
                timeout=600  # 增加超时时间到10分钟，以适应大量点赞
            )
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"运行 sendLike 超时: {str(e)}")
        except subprocess.CalledProcessError as e:
            # 当脚本返回非0码时抛出此异常
            raise RuntimeError(f"sendLike 返回非0状态: {str(e)}")
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"调用子进程异常: {str(e)}") 