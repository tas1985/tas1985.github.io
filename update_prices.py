import requests
from bs4 import BeautifulSoup
import re

# -------------------------- 配置区（无需改动）--------------------------
# 价格来源网站
URL_CPU_LIST = "http://0532.name/cpu_list"
# 需要替换的 HTML 文件路径
HTML_FILE = "index.html"

# ----------------------------------------------------------------------

def get_prices():
    """
    从 0532.name 爬取所有配件名称 + 价格（纯数字）
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(URL_CPU_LIST, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        price_map = {}
        # 匹配：任意文字 + ￥数字 的结构
        pattern = re.compile(r"(.+?)：?￥(\d+\.?\d*)")

        for line in soup.get_text().splitlines():
            line = line.strip()
            match = pattern.search(line)
            if match:
                name = match.group(1).strip()
                price = match.group(2).strip()
                # 过滤无效名称
                if len(name) > 1 and price.replace(".", "").isdigit():
                    price_map[name] = price

        print(f"✅ 成功爬取 {len(price_map)} 个价格")
        return price_map

    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        return {}

def update_html(price_map):
    """
    替换 index.html 761–817 行内 p: 后面的数字
    """
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = 0
        # 只处理 761–817 行（程序行从0开始，所以是 760 到 816）
        for i in range(760, min(817, len(lines))):
            line = lines[i]
            # 匹配：p: 数字（允许空格）
            match = re.search(r"p:\s*(\d+\.?\d*)", line)
            if not match:
                continue

            # 尝试用配件名称匹配（自动对应）
            for name, price in price_map.items():
                if name in line:
                    new_line = re.sub(r"p:\s*\d+\.?\d*", f"p: {price}", line)
                    lines[i] = new_line
                    updated += 1
                    break

        # 保存
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"✅ 成功替换 {updated} 个价格")
        return updated

    except Exception as e:
        print(f"❌ 更新 HTML 失败: {e}")
        return 0

if __name__ == "__main__":
    prices = get_prices()
    if prices:
        update_html(prices)
