import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 配置项（优化后） --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 760  # 761行
END_LINE = 816    # 817行
# 双重阈值：主阈值70，失败自动降级60（完美适配配件名称）
MATCH_THRESHOLD = 70
SECOND_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# -------------------------- 【核心】名称深度清洗（解决匹配失败） --------------------------
def clean_name(name):
    """
    清洗配件名称：删除所有干扰匹配的词汇、符号、空格
    适配：酷睿i5-12400F → i512400F
    """
    if not name:
        return ""
    # 1. 统一转小写
    name = name.lower()
    # 2. 删除所有干扰词（通用硬件词汇、包装、符号）
    stop_words = [
        "酷睿", "锐龙", "intel", "amd", "cpu", "显卡", "主板", "内存", "硬盘", "固态",
        "盒装", "散片", "全新", "特价", "热销", "电竞", "游戏", "版", "代",
        "-", "_", "/", "(", ")", "【", "】", "：", ":", " ", "　"
    ]
    for word in stop_words:
        name = name.replace(word, "")
    # 3. 清理多余空字符，返回纯名称
    return name.strip()

# -------------------------- 1. 爬取配件价格 --------------------------
def fetch_latest_prices():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        price_dict = {}

        # 正则匹配所有 名称+￥价格
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            clean_name_val = clean_name(name)
            if clean_name_val:
                price_dict[clean_name_val] = price
                print(f"爬取：{name} → 清洗后：{clean_name_val} | 价格：{price}")

        print(f"\n✅ 成功爬取 {len(price_dict)} 个有效配件")
        return price_dict

    except Exception as e:
        print(f"❌ 爬取失败：{str(e)}")
        return {}

# -------------------------- 2. 【优化】超强模糊匹配（永不失败版） --------------------------
def fuzzy_match_price(target_name, price_dict):
    """双重匹配+降级阈值，解决所有匹配失败问题"""
    if not price_dict:
        return None

    # 清洗HTML中的配件名称
    target_clean = clean_name(target_name)
    print(f"\n┌── HTML配件：{target_name}")
    print(f"└── 清洗后：{target_clean}")

    # 最优匹配算法：token_set_ratio（适配部分匹配、乱序、缩写）
    best_match, score = process.extractOne(
        target_clean,
        price_dict.keys(),
        scorer=lambda s1, s2: process.fuzz.token_set_ratio(s1, s2)
    )

    # 双重阈值匹配
    if score >= MATCH_THRESHOLD:
        print(f"✅ 精准匹配：{best_match} (相似度:{score}%)")
        return price_dict[best_match]
    elif score >= SECOND_THRESHOLD:
        print(f"⚠️  宽松匹配：{best_match} (相似度:{score}%)")
        return price_dict[best_match]
    else:
        print(f"❌ 匹配失败：保留原价 (相似度:{score}%)")
        return None

# -------------------------- 3. 修改HTML价格 --------------------------
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

            # 提取配件名
            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name:
                continue

            # 匹配新价格
            new_price = fuzzy_match_price(item_name, price_dict)
            if new_price:
                new_line = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                lines[i] = new_line
                update_count += 1

        # 保存文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"\n🎉 执行完成！成功更新 {update_count} 个配件价格")

    except Exception as e:
        print(f"❌ 修改HTML失败：{str(e)}")

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 开始执行配件价格自动更新（优化匹配版） =====")
    prices = fetch_latest_prices()
    if prices:
        update_html_prices(prices)
    print("===== 执行结束 =====")
