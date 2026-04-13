import requests
import re
import os
from fuzzywuzzy import fuzz, process

# ===================== 配置 ======================
URL_SOURCE = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 763
END_LINE = 953
MATCH_SCORE = 50
# ==================================================

def get_source_prices():
    try:
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
                    price_str = parts[1].strip()
                    num_match = re.search(r"\d+", price_str)
                    if num_match:
                        price_map[name] = num_match.group()

        print(f"✅ 成功获取 {len(price_map)} 个商品价格")
        return price_map
    except Exception as e:
        print(f"❌ 获取价格失败: {e}")
        return {}

def update_html():
    if not os.path.exists(HTML_FILE):
        print("❌ 找不到 index.html")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_source_prices()
    if not price_map:
        return

    count = 0
    print("🔍 开始更新 p: 后面的价格...")

    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break

        line = lines[i]
        pure_text = re.sub(r"<[^>]+>", "", line).strip()

        if len(pure_text) < 2:
            continue

        # 模糊匹配配件名
        best = process.extractOne(
            pure_text,
            price_map.keys(),
            scorer=fuzz.partial_ratio
        )

        if best and best[1] >= MATCH_SCORE:
            new_price = price_map[best[0]]
            # ==============================================
            # 🔥 只替换 p: 后面的数字（绝对精准！）
            # ==============================================
            new_line = re.sub(r'p:\s*\d+', f'p: {new_price}', line)

            if new_line != line:
                lines[i] = new_line
                count += 1
                print(f"✅ 行 {i+1} → p: {new_price}")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 全部完成！成功更新 {count} 个 p: 价格！")

if __name__ == "__main__":
    update_html()
