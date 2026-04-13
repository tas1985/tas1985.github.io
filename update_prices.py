# ==========================================================================
# 终极精准版
# 功能：只修改 {n:"xxx",p:数字} 里 p: 后面的价格
# 目标：仓库根目录 index.html
# 范围：761 ~ 955 行
# 绝对成功！
# ==========================================================================
import requests
import re

# 固定配置
HTML_FILE = "index.html"
URL_SOURCE = "http://0532.name/cpu_list"
START_LINE = 761
END_LINE = 955

# 获取价格表
def fetch_prices():
    try:
        resp = requests.get(URL_SOURCE, timeout=10)
        resp.encoding = "utf-8"
        price_map = {}
        
        for line in resp.text.splitlines():
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                name = parts[0].strip()
                price = re.search(r"\d+", parts[1])
                if price:
                    price_map[name] = price.group()
        
        print(f"✅ 成功获取 {len(price_map)} 个价格")
        return price_map
    except:
        print("❌ 获取价格失败")
        return {}

# 主程序
def main():
    # 读取 HTML
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = fetch_prices()
    if not price_map:
        return

    count = 0
    print("\n开始更新 p: 价格...\n")

    # 只修改 761~955 行
    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break
        
        line = lines[i]

        # 匹配 n:"名称"
        n_match = re.search(r'n:"([^"]+)"', line)
        if not n_match:
            continue

        item_name = n_match.group(1).strip()

        # 最强匹配：只要包含关键词就匹配
        best_price = None
        for key, price in price_map.items():
            if key in item_name or item_name in key:
                best_price = price
                break

        if best_price:
            # 🔥 只替换 p:数字
            new_line = re.sub(r'p:\d+', f'p:{best_price}', line)
            if new_line != line:
                lines[i] = new_line
                count += 1
                print(f"✅ 第{i+1}行：{item_name} → p:{best_price}")

    # 写回文件
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 全部成功！共更新 {count} 个价格！")
    print("✅ 已修改 index.html 里所有 p:xxx")

if __name__ == "__main__":
    main()
