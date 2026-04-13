import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 配置项 --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/532.36"
}

# -------------------------- 【核心】提取硬件纯型号 --------------------------
def extract_hardware_model(name):
    if not name:
        return ""
    name = re.sub(r'[{n:"\",}]', '', name)
    name = name.lower().replace(" ", "").replace("-", "")
    pattern = re.compile(
        r'(i[3579]\d+[a-z0-9]*)|'
        r'(r[3579]\d+[a-z0-9]*)|'
        r'(rtx\d+[a-z0-9]*)|'
        r'(gtx\d+[a-z0-9]*)|'
        r'(amd\d+[a-z0-9]*)|'
        r'(\d+gb)|'
        r'(\d+[a-z]+\d*)'
    )
    match = pattern.search(name)
    if match:
        return [m for m in match.groups() if m][0]
    return name

# -------------------------- 1. 爬取价格 --------------------------
def fetch_latest_prices():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        price_dict = {}

        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            model = extract_hardware_model(name)
            if model:
                price_dict[model] = price
                print(f"源站：{name} → 纯型号：{model} | 价格：{price}")

        print(f"\n✅ 成功爬取 {len(price_dict)} 个配件")
        return price_dict

    except Exception as e:
        print(f"❌ 爬取失败：{str(e)}")
        return {}

# -------------------------- 2. 匹配+【定制加价：锐龙R5-5600 +50】 --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict:
        return None

    target_model = extract_hardware_model(target_name)
    print(f"\n┌── HTML原始：{target_name}")
    print(f"└── 提取纯型号：{target_model}")

    best_match, score = process.extractOne(
        target_model,
        price_dict.keys(),
        scorer=process.fuzz.token_set_ratio
    )

    if score >= MATCH_THRESHOLD:
        original_price = price_dict[best_match]
        # ====================== 定制加价逻辑 ======================
        # 仅 锐龙R5-5600 (型号：r55600) 自动+50元
        if target_model == "r55600":
            new_price = str(float(original_price) + 50)
            print(f"✅ 匹配成功：{best_match} (相似度:{score}%)")
            print(f"💰 特殊加价：原价{original_price} → +50 → 新价{new_price}")
            return new_price
        # ==========================================================
        print(f"✅ 匹配成功：{best_match} (相似度:{score}%)")
        return original_price
    else:
        print(f"❌ 匹配失败：保留原价")
        return None

# -------------------------- 3. 更新HTML --------------------------
def update_html_prices(price_dict):
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        update_count = 0
        for i in range(START_LINE, END_LINE + 1):
            if i >= len(lines):
                break
            line = lines[i]
            price_match = re.search(r"p:(\d+(?:\.\d+)?)", line)
            if not price_match:
                continue

            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name:
                continue

            new_price = fuzzy_match_price(item_name, price_dict)
            if new_price:
                new_line = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                lines[i] = new_line
                update_count += 1

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"\n🎉 更新完成！成功更新 {update_count} 个配件价格！")

    except Exception as e:
        print(f"❌ 修改失败：{str(e)}")

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 硬件纯型号匹配版 - 价格自动更新 =====")
    prices = fetch_latest_prices()
    if prices:
        update_html_prices(price_dict=prices)
    print("===== 执行结束 =====")
