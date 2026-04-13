import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# -------------------------- 配置项（无需修改） --------------------------
# 爬取目标网站
SOURCE_URL = "http://0532.name/cpu_list"
# 要修改的HTML文件路径
HTML_FILE = "index.html"
# 锁定修改行号：761-817行（Python索引从0开始，所以是760-816）
START_LINE = 760
END_LINE = 816
# 模糊匹配阈值（越高越严格，80-90最佳）
MATCH_THRESHOLD = 80
# 请求头（防反爬）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# -------------------------- 1. 爬取配件价格 --------------------------
def fetch_latest_prices():
    """爬取网站A的所有配件名称和价格，返回字典：{配件名: 价格数字}"""
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # 获取页面所有文本，按行分割提取
        text = soup.get_text(separator="\n").strip()
        price_dict = {}

        # 正则匹配：配件名称 + ￥数字（支持整数/小数价格）
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            # 清理名称空格/换行符
            clean_name = re.sub(r"\s+", "", name.strip())
            if clean_name:
                price_dict[clean_name] = price

        print(f"✅ 成功爬取 {len(price_dict)} 个配件价格")
        return price_dict

    except Exception as e:
        print(f"❌ 爬取失败：{str(e)}")
        return {}

# -------------------------- 2. 模糊匹配价格 --------------------------
def fuzzy_match_price(target_name, price_dict):
    """模糊匹配：输入HTML中的配件名，返回最相似的实时价格"""
    if not price_dict:
        return None

    # 清理目标名称（去空格/特殊字符）
    target_clean = re.sub(r"\s+", "", target_name.strip())
    # 获取最佳匹配项
    best_match, score = process.extractOne(
        target_clean,
        price_dict.keys(),
        scorer=fuzz.ratio
    )

    if score >= MATCH_THRESHOLD:
        print(f"匹配成功：{target_clean} ←→ {best_match} (相似度:{score}%)")
        return price_dict[best_match]
    else:
        print(f"匹配失败：{target_clean} (相似度:{score}%，低于阈值)")
        return None

# -------------------------- 3. 修改HTML价格 --------------------------
def update_html_prices(price_dict):
    """读取HTML，仅修改761-817行的p:xxx价格，保存文件"""
    try:
        # 读取所有行
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 仅遍历指定行范围
        for i in range(START_LINE, END_LINE + 1):
            if i >= len(lines):
                break
            line = lines[i]
            # 匹配行内的价格格式：p:数字
            price_match = re.search(r"p:(\d+(?:\.\d+)?)", line)
            if not price_match:
                continue

            # 提取当前行的配件名称（去掉p:xxx和标签）
            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name:
                continue

            # 模糊匹配新价格
            new_price = fuzzy_match_price(item_name, price_dict)
            if new_price:
                # 替换p:后的数字
                new_line = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                lines[i] = new_line

        # 保存修改后的HTML
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print("✅ HTML文件价格更新完成！")

    except Exception as e:
        print(f"❌ 修改HTML失败：{str(e)}")

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 开始执行配件价格自动更新 =====")
    prices = fetch_latest_prices()
    if prices:
        update_html_prices(prices)
    print("===== 执行结束 =====")
