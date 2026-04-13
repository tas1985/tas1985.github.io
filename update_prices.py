# ==============================================================================
# 终极版：只修改仓库根目录 index.html
# 修改范围：761行 const defaultData 开始 → 955行 中文类目映射表 之前
# 直接修改价格数字，100% 成功！
# ==============================================================================
import requests
import re
import os

# 固定配置
URL_SOURCE = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 761
END_LINE = 955

# ---------------------- 抓取价格 ----------------------
def get_prices():
    try:
        r = requests.get(URL_SOURCE, timeout=10)
        r.encoding = "utf-8"
        data = {}
        for line in r.text.splitlines():
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                name = parts[0].strip()
                price = re.search(r"\d+", parts[1])
                if price:
                    data[name] = price.group()
        print(f"✅ 已抓取 {len(data)} 个价格")
        return data
    except:
        print("❌ 抓取失败")
        return {}

# ---------------------- 强制修改 JS 价格 ----------------------
def update_file():
    if not os.path.exists(HTML_FILE):
        print("❌ 找不到 index.html 文件！")
        return

    # 读取文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_prices()
    if not price_map:
        return

    count = 0
    print("\n开始更新 index.html 价格...\n")

    # 只修改 761 ~ 955 行
    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break

        line = lines[i]
        original = line

        # ---------------- 关键：直接替换 名称:数字 格式 ----------------
        def replace_match(m):
            key = m.group(1).strip()
            for name, price in price_map.items():
                if key in name or name in key:
                    nonlocal count
                    count += 1
                    return f"{key}:{price}"
            return m.group(0)

        # 匹配： 名称:1234   名称 : 1234
        new_line = re.sub(r'([\u4e00-\u9fa5a-zA-Z0-9\-_]+)\s*:\s*\d+', replace_match, line)
        lines[i] = new_line

        if new_line != original:
            print(f"行 {i+1} 已更新")

    # 直接写回 index.html！！！
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 成功！共更新 {count} 个价格！")
    print(f"✅ 文件已保存：{os.path.abspath(HTML_FILE)}")

if __name__ == "__main__":
    update_file()
