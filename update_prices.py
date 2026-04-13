import requests
import re
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz, process
import os
from datetime import datetime

# ===================== 配置参数 ======================
URL_SOURCE = "http://0532.name/cpu_list"
START_LINE = 763    # 开始行
END_LINE = 953     # 结束行
MATCH_SCORE = 70   # 匹配精度
# ====================================================

def get_source_prices():
    """从 A 网站获取价格"""
    try:
        print(f"[{datetime.now()}] 正在获取配件价格...")
        resp = requests.get(URL_SOURCE, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        price_dict = {}
        items = soup.find_all("tr")

        for item in items:
            tds = item.find_all("td")
            if len(tds) >= 2:
                name = tds[0].get_text(strip=True)
                price_text = tds[1].get_text(strip=True)
                price_num = re.search(r"(\d+\.?\d*)", price_text)
                if name and price_num:
                    price_dict[name] = price_num.group(1)

        print(f"✅ 成功获取 {len(price_dict)} 个配件价格")
        return price_dict

    except Exception as e:
        print(f"❌ 获取价格失败: {e}")
        return {}

def fuzzy_match_replace(lines, price_dict):
    """只替换 763-953 行的价格数字"""
    updated_lines = lines.copy()
    match_count = 0

    for line_num in range(START_LINE - 1, END_LINE):
        if line_num >= len(updated_lines):
            break

        line = updated_lines[line_num]
        clean_line = re.sub(r"<[^>]+>", "", line).strip()
        if len(clean_line) < 2:
            continue

        best_match, score = process.extractOne(
            clean_line,
            price_dict.keys(),
            scorer=fuzz.partial_ratio
        )

        if score >= MATCH_SCORE:
            new_price = price_dict[best_match]
            new_line = re.sub(r"\d+\.?\d*", new_price, line)
            if new_line != line:
                updated_lines[line_num] = new_line
                match_count += 1
                print(f"行 {line_num+1} | 匹配成功: {best_match} → {new_price} 元")

    print(f"✅ 价格更新完成，共更新 {match_count} 个配件")
    return updated_lines

def main():
    print("=" * 60)
    print(" GitHub 自动更新 index.html 价格程序")
    print(" 作用：仅修改根目录 index.html 763~953 行价格")
    print("=" * 60)

    # 1. 获取价格
    source_prices = get_source_prices()
    if not source_prices:
        print("❌ 未获取到价格，程序退出")
        return

    # 2. 读取 仓库根目录的 index.html
    html_path = "index.html"
    if not os.path.exists(html_path):
        print(f"❌ 未找到 {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 3. 只修改 763~953 行
    new_lines = fuzzy_match_replace(lines, source_prices)

    # 4. 直接覆盖写回 index.html
    with open(html_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("\n🎉 成功！已直接更新仓库根目录的 index.html")

if __name__ == "__main__":
    main()
