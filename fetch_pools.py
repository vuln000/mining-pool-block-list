import os
import csv
import requests
import sys
from datetime import datetime, timedelta

# 从环境变量中获取 API KEY，避免硬编码
API_KEY = os.environ.get("FOFA_KEY")
if not API_KEY:
    print("错误: 未设置 FOFA_KEY 环境变量。")
    sys.exit(1)

OUTPUT_FILE = "mining_pools.csv"
# FOFA API URL
API_URL = f"https://fofa.info/api/v1/search/all?key={API_KEY}&qbase64=YmFubmVyPSJtaW5pbmcubm90aWZ5Ig==&size=200&fields=lastupdatetime,ip,port"

def fetch_fofa_data(url):
    """请求 FOFA API 并返回结果列表"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("error"):
            print(f"FOFA API 返回错误: {data.get('errmsg', '未知错误')}")
            sys.exit(1)
            
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"请求 FOFA API 失败: {e}")
        sys.exit(1)

def main():
    print("开始从 FOFA 拉取最新数据...")
    new_results = fetch_fofa_data(API_URL)

    if not new_results:
        print("警告: 未获取到任何数据。")
        sys.exit(0)

    pools_dict = {}

    # 1. 如果本地 CSV 文件存在，先读取原有数据
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 3:
                    lastupdatetime, ip, port = row
                    pools_dict[(ip, port)] = lastupdatetime

    # 2. 合并新数据并去重、更新时间
    # 逻辑：以 (ip, port) 作为字典的 key。
    # 字符串格式的日期 (YYYY-MM-DD HH:MM:SS) 可以直接用 > 比较大小
    for row in new_results:
        if len(row) == 3:
            lastupdatetime, ip, port = row
            key = (ip, port)
            
            # 如果是新 IP:Port，或者新数据的时间比记录的时间更晚，则更新
            if key not in pools_dict or lastupdatetime > pools_dict[key]:
                pools_dict[key] = lastupdatetime

    # 3. 计算365天前的时间点，用于过滤过期数据
    cutoff_time = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")

    # 4. 将字典转回列表，过滤掉超过365天的数据，并按时间倒序排序 (最新的排在最上面)
    filtered_pools = [
        [time, ip, port] for (ip, port), time in pools_dict.items() if time >= cutoff_time
    ]

    sorted_pools = sorted(
        filtered_pools,
        key=lambda x: x[0],
        reverse=True
    )

    # 5. 将最终结果覆写回 CSV 文件
    with open(OUTPUT_FILE, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(sorted_pools)

    print(f"更新完成！当前矿池总数: {len(sorted_pools)}")

if __name__ == "__main__":
    main()