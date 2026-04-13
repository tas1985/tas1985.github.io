import requests
import re
import os

# ===================== 【精准配置】=====================
URL_SOURCE = "http://0532.name/cpu_list"
HTML_FILE = "index.html"

# 你指定的精准范围
START_LINE = 761    # 从 const defaultData 开始
END_LINE = 955      # 到 // 中文类目映射表 之前
# ======================================================

def get_price_dict():
    """获取A网站所有配件名称+价格"""
    try:
        resp = requests.get(URL_SOURCE, timeout=10)
        resp.encoding = "utf-8"
        lines = resp.text.splitlines()
        
        price_map = {}
        for line in lines:
            line = line.strip()
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    price = parts[1].strip()
                    num = re.search(r"\d+", price)
                    if num:
                        price_map[name.lower()] = num.group()
        print(f"✅ 成功获取 {len(price_map)} 个配件价格")
        return price_map
    except Exception as e:
        print(f"❌ 获取价格失败：{e}")
        return {}

def update_js_prices():
    """精准修改 const defaultData 内部的价格"""
    if not os.path.exists(HTML_FILE):
        print("❌ 未找到 index.html")
        return

    # 读取文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_price_dict()
    if not price_map:
        return

    count = 0
    print("\n🔧 开始精准修改 defaultData 内的价格...")

    # 只修改 761 ~ 955 行
    for i in range(START_LINE - 1, END_LINE):
        if i >= len(lines):
            break
        
        line = lines[i]
        original = line

        # 匹配格式：价格:数字 或 价格 : 数字
        # 例如：i5-12400F:600 → 只改 600
        pattern = re.compile(r'([a-zA-Z0-9\u4e00-\u9fa5\-_]+)\s*:\s*\d+')
        
        def replace_price(match):
            key = match.group(1).lower().strip()
            # 模糊匹配（包含关键词即可）
            for p_key, p_val in price_map.items():
                if key in p_key or p_key in key:
                    nonlocal count
                    count += 1
                    return f"{match.group(1)}:{p_val}"
            return match.group(0)

        # 替换价格
        new_line = pattern.sub(replace_price, line)
        lines[i] = new_line

        if new_line != original:
            print(f"✅ 第{i+1}行：{new_line.strip()}")

    # 写回文件
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 完成！共更新 {count} 个价格！")
    print("✅ 仅修改了 const defaultData 区域，其他代码完全不动！")

if __name__ == "__main__":
    update_js_prices()
