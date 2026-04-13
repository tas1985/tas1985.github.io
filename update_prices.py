import requests
import re
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz, process
import os
from datetime import datetime

# ===================== 配置参数 ======================
URL_SOURCE = "http://0532.name/cpu_list"
URL_TARGET = "https://tas1985.github.io/"
START_LINE = 763
END_LINE = 953
MATCH_SCORE = 70
# ====================================================

def get_source_prices():
    try:
        print(f"[{datetime.now()}] 获取A网站价格...")
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

        print(f"✅ 获取到 {len(price_dict)} 个价格")
        return price_dict

    except Exception as e:
        print(f"❌ 获取价格失败: {e}")
        return {}

def download_target_html():
    try:
        print(f"[{datetime.now()}] 下载目标页面...")
        resp = requests.get(URL_TARGET, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ 下载页面失败: {e}")
        return None

def fuzzy_match_replace(lines, price_dict):
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
                print(f"行 {line_num+1} | {best_match} → {new_price} 元")

    print(f"✅ 共更新 {match_count} 个价格")
    return updated_lines

def main():
    print("=" * 50)
    print("  GitHub 自动价格更新程序")
    print("=" * 50)

    source_prices = get_source_prices()
    if not source_prices:
        return

    target_html = download_target_html()
    if not target_html:
        return

    original_lines = target_html.splitlines(keepends=True)
    new_lines = fuzzy_match_replace(original_lines, source_prices)

    with open("index.html", "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print("\n🎉 index.html 已自动更新完成！")

if __name__ == "__main__":
    main()