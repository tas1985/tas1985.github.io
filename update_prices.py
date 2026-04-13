# ==============================================================================
# 终极精准版：只修改 {n:"名称",p:1234} 里 p: 后面的数字
# 目标文件：仓库根目录 index.html
# 修改范围：761 ~ 955 行
# 绝对不会动其他任何代码！
# ==============================================================================
import requests
import re

# 配置
HTML_FILE = "index.html"
URL_PRICE = "http://0532.name/cpu_list"
START_LINE = 761
END_LINE = 955

# 获取价格表
def get_price_list():
    try:
        resp = requests.get(URL_PRICE, timeout=10)
        resp.encoding = "utf-8"
        prices = {}
        for line in resp.text.splitlines():
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                name = parts[0].strip()
                price = re.search(r"\d+", parts[1])
                if price:
                    prices[name] = price.group()
        print(f"✅ 获取到 {len(prices)} 个价格")
        return prices
    except:
        print("❌ 获取价格失败")
        return {}

# 主更新程序
def main():
    # 读取文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    prices = get_price_list()
    if not prices:
        return

    count = 0
    print("\n开始更新 p: 数字...\n")

    # 只修改 761~955 行
    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break
        line = lines[i]

        # 取出 n:"..." 里面的文字
        n_match = re.search(r'n:"([^"]+)"', line)
        if not n_match:
            continue

        item_name = n_match.group(1).strip()

        # 模糊匹配
        best_price = None
        best_key = None
        best_score = 0

        for key, val in prices.items():
            sc = 100 if key in item_name or item_name in key else 0
            if sc > best_score:
                best_score = sc
                best_price = val
                best_key = key

        if best_price and best_score > 0:
            # 只替换 p:数字 ！！！
            new_line = re.sub(r'p:\d+', f'p:{best_price}', line)
            if new_line != line:
                lines[i] = new_line
                count += 1
                print(f"✅ 第{i+1}行 {item_name} => p:{best_price}")

    # 写回文件
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 成功！一共更新了 {count} 个价格！")
    print("✅ 已修改 index.html 里所有 p:数字")

if __name__ == "__main__":
    main()
