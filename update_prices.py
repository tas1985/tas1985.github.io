import requests
import re
from fuzzywuzzy import fuzz, process
import os
from datetime import datetime

# ===================== 配置 ======================
URL_SOURCE = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 763
END_LINE = 953
MATCH_SCORE = 50  # 调低更容易匹配成功
# ==================================================

def get_source_prices():
    try:
        print(f"📅 获取价格列表: {datetime.now()}")
        resp = requests.get(URL_SOURCE, timeout=10)
        resp.encoding = "utf-8"
        lines = resp.text.splitlines()

        price_map = {}
        for line in lines:
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    price_part = parts[1].strip()
                    num = re.findall(r"\d+\.?\d*", price_part)
                    if num:
                        price_map[name] = num[0]
        print(f"✅ 获取到 {len(price_map)} 个商品价格")
        return price_map
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return {}

def update_prices():
    if not os.path.exists(HTML_FILE):
        print(f"❌ 找不到 {HTML_FILE}")
        return

    # 读取文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_source_prices()
    if not price_map:
        return

    print("🔍 开始匹配并更新价格...")
    count = 0

    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break
        original = lines[i]
        stripped = re.sub(r"<[^>]+>", "", original).strip()

        if len(stripped) < 2:
            continue

        # 模糊匹配
        best = process.extractOne(stripped, price_map.keys(), scorer=fuzz.ratio)
        if not best:
            continue

        match_name, score = best
        if score >= MATCH_SCORE:
            new_price = price_map[match_name]
            # 替换数字（只替换价格）
            new_line = re.sub(r"\d+", new_price, original)
            if new_line != original:
                lines[i] = new_line
                count += 1
                print(f"行 {i+1} → {match_name} = {new_price} 元")

    # 写回文件
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 成功更新 {count} 个价格！")

if __name__ == "__main__":
    update_prices()
