#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import re
import os

# 配置
URL_CPU_LIST = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816

def safe_get_prices():
    """安全爬取，永远不崩溃"""
    price_map = {}
    try:
        print("[INFO] 开始获取价格...")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip, deflate",
        }
        resp = requests.get(URL_CPU_LIST, headers=headers, timeout=10)
        resp.raise_for_status()
        text = resp.text

        # 匹配 ￥数字
        results = re.findall(r'￥(\d+\.?\d*)', text)
        names = re.findall(r'([^\n\r：]+)：?￥\d+\.?\d*', text)

        for name, price in zip(names, results):
            name = name.strip()
            if len(name) > 1 and price.replace(".", "").isdigit():
                price_map[name] = price
                print(f"  → {name} = {price}")

        print(f"[INFO] 成功获取 {len(price_map)} 个价格")
    except Exception as e:
        print(f"[WARN] 爬取失败（不影响程序）: {str(e)[:50]}")
    return price_map

def safe_update_html(price_map):
    """安全替换HTML，永远不崩溃"""
    if not price_map:
        print("[INFO] 无价格数据，跳过更新")
        return

    try:
        if not os.path.exists(HTML_FILE):
            print(f"[ERROR] 文件不存在: {HTML_FILE}")
            return

        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = 0
        max_idx = min(END_LINE + 1, len(lines))

        for i in range(START_LINE, max_idx):
            line = lines[i]
            if "p:" not in line:
                continue

            # 匹配替换
            for name, price in price_map.items():
                if name in line:
                    lines[i] = re.sub(r"p:\s*\d+\.?\d*", f"p: {price}", line)
                    updated += 1
                    break

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"[INFO] 替换完成：{updated} 个价格已更新")

    except Exception as e:
        print(f"[WARN] 更新HTML失败（不影响程序）: {str(e)[:50]}")

if __name__ == "__main__":
    print("=" * 40)
    print("       价格自动更新工具")
    print("=" * 40)

    prices = safe_get_prices()
    safe_update_html(prices)

    print("\n[SUCCESS] 程序正常结束 ✅")
