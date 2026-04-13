# ==========================================================================
# 终极锁定版：只修改 tas1985.github.io/index.html
# 精准修改：761行 const defaultData → 955行 // 中文类目映射表 之前
# 只改价格数字，绝不碰其他代码
# ==========================================================================
import requests
import re
import os

# 🔥 强制锁定你的文件路径
HTML_FILE = "tas1985.github.io/index.html"
URL_SOURCE = "http://0532.name/cpu_list"
START_LINE = 761
END_LINE = 955

# --------------------------------------------------------------------------
# 1. 获取价格表
# --------------------------------------------------------------------------
def get_price_map():
    try:
        resp = requests.get(URL_SOURCE, timeout=10)
        resp.encoding = "utf-8"
        price_dict = {}
        
        for line in resp.text.strip().splitlines():
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                name = parts[0].strip()
                price_match = re.search(r"\d+", parts[1])
                if price_match:
                    price_dict[name] = price_match.group()
        
        print(f"✅ 成功获取 {len(price_dict)} 个商品价格")
        return price_dict
    except:
        print("❌ 获取价格失败")
        return {}

# --------------------------------------------------------------------------
# 2. 强制修改 index.html 价格
# --------------------------------------------------------------------------
def update_price():
    if not os.path.exists(HTML_FILE):
        print(f"❌ 文件不存在：{HTML_FILE}")
        return

    # 读取文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_price_map()
    if not price_map:
        return

    update_count = 0
    print("\n开始强制更新价格（761~955行）...\n")

    # 只修改指定区间
    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break

        line = lines[i]
        original_line = line

        # 匹配：名称:1234  名称 : 1234
        def replace_func(match):
            nonlocal update_count
            key = match.group(1).strip()
            for name, price in price_map.items():
                if key in name or name in key:
                    update_count += 1
                    return f"{key}:{price}"
            return match.group(0)

        # 正则替换价格
        new_line = re.sub(r'([a-zA-Z0-9\u4e00-\u9fa5\-_]+)\s*:\s*\d+', replace_func, line)
        lines[i] = new_line

        if new_line != original_line:
            print(f"✅ 第 {i+1} 行已更新")

    # 强制写回文件
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 🎉 🎉 全部成功！")
    print(f"✅ 已修改文件：{HTML_FILE}")
    print(f"✅ 一共更新了 {update_count} 个价格")

if __name__ == "__main__":
    update_price()
