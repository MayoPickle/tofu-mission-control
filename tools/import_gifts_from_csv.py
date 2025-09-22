#!/usr/bin/env python3
"""
CSV 历史数据导入脚本 → gift_records

支持字段映射：
- uid, uname, time(UTC), gift_id, gift_name, gift_img → tag_image/gift_assets, gift_num
- gold/silver → 价格与币种（优先 gold，其次 silver）
- id → tid/rnd（用于去重）
- room_id

写入目标表：gift_records（或通过 --table 指定）

使用示例：
  python tools/import_gifts_from_csv.py --csv /path/to/xxx.csv --env missions/.env --skip-existing
"""
import os
import sys
import csv
import argparse
import traceback
import datetime as dt
from typing import Optional, Dict, Any

from dotenv import load_dotenv

# 将项目根目录加入 sys.path，便于导入模块
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from modules.db_handler import DBHandler
from modules.logger import get_logger, debug, info, warning, error, critical
from tools.init_db import init_database


def parse_args():
    parser = argparse.ArgumentParser(description="导入 CSV 到 gift_records")
    parser.add_argument("--csv", required=True, help="CSV 文件路径")
    parser.add_argument("--env", default=os.path.join(ROOT, "missions/.env"), help="环境变量文件路径")
    parser.add_argument("--table", default="gift_records", help="目标表名")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要写入的数据，不实际落库")
    parser.add_argument("--skip-existing", action="store_true", help="根据 tid 去重，已存在则跳过")
    parser.add_argument("--log-file", help="日志文件路径")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO")
    return parser.parse_args()


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except Exception:
        return default


def parse_time_to_epoch_utc(time_str: str) -> Optional[int]:
    """
    解析字符串时间为 epoch 秒（按 UTC 解释）。
    CSV 示例："2025-04-11 06:38:32"
    """
    if not time_str:
        return None
    try:
        # 按 UTC 解释
        dt_naive = dt.datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S")
        dt_aware = dt_naive.replace(tzinfo=dt.timezone.utc)
        return int(dt_aware.timestamp())
    except Exception:
        return None


def record_exists_by_tid(db: DBHandler, tid: str) -> bool:
    """简单去重：依据 tid 存在性"""
    if not tid:
        return False
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM {db.table_name} WHERE tid = %s LIMIT 1", (str(tid),))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def map_row_to_payload(row: Dict[str, str]) -> Dict[str, Any]:
    """
    将 CSV 行转换为 add_gift_record_v2 兼容的 payload
    """
    uid = to_int(row.get("uid"))
    uname = row.get("uname") or ""
    room_id = str(row.get("room_id") or "")
    gift_id = to_int(row.get("gift_id"))
    gift_name = row.get("gift_name") or ""
    gift_num = to_int(row.get("gift_num"), 1) or 1
    tid = str(row.get("id") or "") or None

    # 币种与价格：
    # - gold: 实际花费价格（购买盲盒的价格）
    # - normal_gold: 爆出礼物单价（揭示礼物的价值）
    # 导入策略：
    # - 非盲盒：price 使用 gold（或 silver）
    # - 盲盒：price 使用 normal_gold（与示例库保持一致）
    gold = to_int(row.get("gold"), 0) or 0
    normal_gold = to_int(row.get("normal_gold"), 0) or 0
    silver = to_int(row.get("silver"), 0) or 0

    # 初始 coin_type 判定（优先金币生态）
    coin_type = "gold" if gold or normal_gold else ("silver" if silver else None)

    # 盲盒判定：gold 与 normal_gold 同时存在且不相等
    is_blind = (gold > 0 and normal_gold > 0 and normal_gold != gold)

    if is_blind:
        price = normal_gold  # 与库中盲盒记录保持一致（以揭示礼物价计）
    else:
        if gold > 0:
            price = gold
        elif silver > 0:
            price = silver
        else:
            price = 0

    total_price = price * gift_num if price is not None else None

    # 时间：转为 epoch 秒，交给 add_gift_record_v2 的 "timestamp" 字段
    ts_epoch = parse_time_to_epoch_utc(row.get("time"))

    # 资源
    gift_img = row.get("gift_img") or None
    gift_assets = {"img_basic": gift_img} if gift_img else None
    tag_image = gift_img

    payload = {
        "timestamp": ts_epoch,  # add_gift_record_v2 会将 int(ts) 转为 datetime
        "room_id": room_id,
        "uid": uid,
        "uname": uname,
        "gift_id": gift_id,
        "gift_name": gift_name,
        "price": price,
        "gift_num": gift_num,
        "total_price": total_price,
        "coin_type": coin_type,
        "gift_type": 0,
        "action": "投喂",
        "is_blind_gift": is_blind,
        "tid": tid,
        "rnd": tid,
        "combo_total_coin": total_price,
        "total_coin": total_price,
        "gift_assets": gift_assets,
        "tag_image": tag_image,
    }

    # 盲盒详情
    if is_blind:
        diff = (normal_gold - gold)
        result = "profit" if diff > 0 else ("loss" if diff < 0 else "even")
        payload["blind_box"] = {
            "diff": diff,
            "result": result,
            "gift_tip_price": normal_gold,
            # CSV 中仅有揭示礼物 ID/名称，原始盲盒 ID/名称缺失，尽可能填充现有信息
            "original_gift_price": gold,
            "revealed_gift_price": normal_gold,
            "revealed_gift_id": gift_id,
            "revealed_gift_name": gift_name,
        }

    return payload


def main():
    args = parse_args()

    # 日志
    log_level = getattr(__import__("logging"), args.log_level)
    logger = get_logger("import_csv", args.log_file, log_level)

    # 环境与表
    load_dotenv(args.env)
    # 确保表结构存在（幂等）
    init_database(args.env, args.table, drop_existing=False)

    db = DBHandler(env_path=args.env, table_name=args.table)

    csv_path = os.path.abspath(args.csv)
    if not os.path.exists(csv_path):
        error(f"CSV 文件不存在: {csv_path}")
        sys.exit(1)

    total = 0
    success = 0
    skipped = 0
    failed = 0

    # 使用 utf-8-sig 去除可能存在的 BOM，避免首列出现 "\ufeffuid" 导致缺字段
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 规范化列名：移除 BOM 和首尾空白
            norm_row = { (k.replace("\ufeff", "").strip() if isinstance(k, str) else k): v for k, v in row.items() }
            total += 1
            try:
                payload = map_row_to_payload(norm_row)

                # 校验必需字段
                required = ["room_id", "uid", "uname", "gift_id", "gift_name"]
                if any(payload.get(k) in (None, "") for k in required):
                    warning(f"第{total}行缺少必要字段，已跳过: {norm_row}")
                    skipped += 1
                    continue

                if args.skip_existing and payload.get("tid") and record_exists_by_tid(db, payload["tid"]):
                    debug(f"已存在 tid={payload['tid']}，跳过。")
                    skipped += 1
                    continue

                if args.dry_run:
                    info(f"DRY-RUN 插入: {payload}")
                    success += 1
                else:
                    db.add_gift_record_v2(payload)
                    success += 1
            except Exception as e:
                failed += 1
                error(f"导入第{total}行失败: {e}")
                debug(f"行数据: {row}")
                traceback.print_exc()

    info(f"导入完成: 总计={total}, 成功={success}, 跳过={skipped}, 失败={failed}")
    print({
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
    })


if __name__ == "__main__":
    main()


