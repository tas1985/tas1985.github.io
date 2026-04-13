import requests
import re
import os
from fuzzywuzzy import fuzz, process

# ===================== 配置 ======================
URL_SOURCE = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 763
END_LINE = 953
MATCH_SCORE = 40
# ==================================================

def get_price_data():
    try:
        resp = requests.get(URL_SOURCE, timeout=10)
        resp.encoding = "utf-8"
        lines = resp.text.splitlines()
        price_dict = {}

        for line in lines:
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    price_str = parts[1].strip()
                    num = re.search(r"\d+", price_str)
                    if num:
                        price_dict[name] = num.group()

        print(f"✅ 获取到 {len(price_dict)} 个商品价格")
        return price_dict
    except:
        print("❌ 获取价格失败")
        return {}

def main():
    if not os.path.exists(HTML_FILE):
        print("❌ 找不到 index.html")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_price_data()
    if not price_map:
        return

    count = 0
    print("\n🔍 开始更新价格（只修改 p: 后面的数字）...\n")

    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break

        line = lines[i]
        clean_line = re.sub(r"<[^>]+>", "", line).strip()

        if len(clean_line) < 2:
            continue

        best_match, score = process.extractOne(
            clean_line,
            price_map.keys(),
            scorer=fuzz.partial_ratio
        )

        if score >= MATCH_SCORE:
            new_price = price_map[best_match]

            # ==============================================
            # 🔥 🔥 🔥 这里是关键：只替换 p:数字
            # ==============================================
            new_line = re.sub(r'p:\d+', f'p:{new_price}', line)
            new_line = re.sub(r'p:\s\d+', f'p: {new_price}', new_line)

            if new_line != line:
                lines[i] = new_line
                count += 1
                print(f"✅ 第 {i+1} 行 → 价格更新为 p:{new_price}")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 成功！一共更新了 {count} 个价格！")

if __name__ == "__main__":
    main()
