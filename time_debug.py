#!/usr/bin/env python3
"""
时区诊断工具：检查系统时区和Python时间设置
用法：
    在容器内运行 python time_debug.py
"""

import os
import time
import datetime
import subprocess
import sys

print("==== 系统时区信息 ====")
print(f"系统TZ环境变量: {os.environ.get('TZ', '未设置')}")

try:
    timezone_file = "/etc/timezone"
    if os.path.exists(timezone_file):
        with open(timezone_file) as f:
            print(f"/etc/timezone 内容: {f.read().strip()}")
    else:
        print("/etc/timezone 文件不存在")
except Exception as e:
    print(f"读取 /etc/timezone 出错: {e}")

try:
    localtime_link = os.readlink("/etc/localtime")
    print(f"/etc/localtime 链接指向: {localtime_link}")
except Exception as e:
    print(f"读取 /etc/localtime 链接出错: {e}")

print("\n==== 系统时间命令输出 ====")
try:
    date_output = subprocess.check_output(["date"], text=True).strip()
    print(f"date命令输出: {date_output}")
except Exception as e:
    print(f"执行date命令出错: {e}")

try:
    timedatectl_output = subprocess.check_output(["timedatectl"], text=True).strip()
    print(f"timedatectl命令输出:\n{timedatectl_output}")
except Exception as e:
    print(f"执行timedatectl命令出错: {e}")

print("\n==== Python时间信息 ====")
print(f"Python版本: {sys.version}")

local_now = datetime.datetime.now()
print(f"datetime.now(): {local_now} (时区信息: {local_now.tzinfo})")

utc_now = datetime.datetime.utcnow()
print(f"datetime.utcnow(): {utc_now} (时区信息: {utc_now.tzinfo})")

try:
    # Python 3.11+
    utc_aware = datetime.datetime.now(datetime.UTC)
    print(f"datetime.now(datetime.UTC): {utc_aware} (时区信息: {utc_aware.tzinfo})")
except AttributeError:
    # 较老版本的Python
    utc_aware = datetime.datetime.now(datetime.timezone.utc)
    print(f"datetime.now(datetime.timezone.utc): {utc_aware} (时区信息: {utc_aware.tzinfo})")

# 计算时差
local_aware = local_now.replace(tzinfo=datetime.timezone.utc)
time_diff = (local_aware - utc_aware).total_seconds() / 3600
print(f"本地时间与UTC时间差: {time_diff} 小时")

print(f"time.time(): {time.time()}")
print(f"time.ctime(): {time.ctime()}")

print("\n==== 密码计算模拟 ====")
# 模拟密码计算
now = utc_aware
sum_value = now.month + now.day + now.hour
power = 2  # 默认power值
computed_value = sum_value ** power
password = computed_value % 10000

print(f"月({now.month}) + 日({now.day}) + 时({now.hour}) = {sum_value}")
print(f"{sum_value}^{power} = {computed_value}")
print(f"计算得到的密码: {password}") 