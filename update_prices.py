import requests
from bs4 import BeautifulSoup
import re

# -------------------------- 配置 --------------------------
URL_CPU_LIST = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
# 你要替换的行：761–817 行（Python 从 0 开始）
START_LINE = 760
END_LINE = 816

# ---------------------------------------------------------

def get_prices():
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "http://0532.name/"
        }
        
        print("🔍 正在爬取价格页面...")
        resp = session.get(URL_CPU_LIST, headers=headers, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        price_map = {}
        pattern = re.compile(r"([^\n\r：]+)：?￥(\d+\.?\d*)", re.U)

        for match in pattern.finditer(text):
            name = match.group(1).strip()
            price = match.group(2).strip()

            if 2 <= len(name) <= 80 and price.replace(".", "").isdigit():
                price_map[name] = price
                print(f"✅ {name} -> {price}")

        print(f"\n📊 总计爬取到 {len(price_map)} 个价格")
        return price_map

    except Exception as e:
        print(f"❌ 爬取价格失败: {str(e)}")
        return {}

def update_html(price_map):
    if not price_map:
        print("⚠️ 无价格数据，跳过更新")
        return 0

    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = 0
        max_line = min(END_LINE + 1, len(lines))

        for i in range(START_LINE, max_line):
            line = lines[i]
            if "p:" not in line:
                continue

            for name, price in price_map.items():
                if name in line:
                    new_line = re.sub(r"p:\s*\d+\.?\d*", f"p: {price}", line)
                    lines[i] = new_line
                    updated += 1
                    break

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"\n✅ HTML 更新完成！成功替换 {updated} 个价格")
        return updated

    except Exception as e:
        print(f"❌ 更新 HTML 失败: {str(e)}")
        return 0

if __name__ == "__main__":
    print("🚀 开始自动更新价格...")
    prices = get_prices()
    update_html(prices)
    print("\n🏁 程序执行完毕")
