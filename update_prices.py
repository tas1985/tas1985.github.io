# ==============================================================================
# 100% 成功版
# 功能：从 http://0532.name/cpu_list 提取 ￥ 后的价格
# 只修改：{n:"xxx",p:数字} 里的 p: 后面数字
# 只作用：你给的所有CPU型号
# 绝对不破坏代码格式
# ==============================================================================
import requests
import re

# 配置
HTML_FILE = "index.html"
URL = "http://0532.name/cpu_list"

# 你要更新的所有CPU名称（精准对应）
CPU_MAP = {
    "i3-12100F 3.3G 四核": "i3-12100F",
    "i3-12100 3.3G 四核": "i3-12100",
    "i5-12400F 2.5G 六核": "i5-12400F",
    "i5-12400 2.5G 六核": "i5-12400",
    "i5-12490F 3.0G 六核": "i5-12490F",
    "i5-12600KF 3.7G 十核": "i5-12600KF",
    "i7-12700KF 3.6G 十二核": "i7-12700KF",
    "i9-12900KF 3.2G 十六核": "i9-12900KF",
    "i9-12900K 3.2G 十六核": "i9-12900K",
    "i3-13100F 3.4G 四核": "i3-13100F",
    "i3-13100 3.4G 四核": "i3-13100",
    "i5-13400F 2.5G 十核": "i5-13400F",
    "i5-13400 2.5G 十核": "i5-13400",
    "i5-13600KF 3.5G 十四核": "i5-13600KF",
    "i5-13600K 3.5G 十四核": "i5-13600K",
    "i7-13700KF 2.1G 十六核": "i7-13700KF",
    "i9-13900KF 3.0G 二十四核": "i9-13900KF",
    "i9-13900K 3.0G 二十四核": "i9-13900K",
    "i3-14100F 3.5G 四核": "i3-14100F",
    "i3-14100 3.5G 四核": "i3-14100",
    "i5-14400F 2.5G 十核": "i5-14400F",
    "i5-14400 2.5G 十核": "i5-14400",
    "中文原盒i5-14490F 2.5G 十核": "i5-14490F",
    "i5-14600KF 3.5G 十四核二十线程5.3G睿频": "i5-14600KF",
    "i5-14600K 3.5G 十四核": "i5-14600K",
    "i7-14700KF 3.4G 二十核": "i7-14700KF",
    "i9-14900KF 3.2G 二十四核": "i9-14900KF",
    "i9-14900K 3.2G 二十四核": "i9-14900K",
    "Intel E5-2666V3 3.5G 10核20线程（到手10天质保）": "E5-2666V3",
    "Ultra 5 225F 2.7G 十核": "Ultra 5 225F",
    "Ultra 5 225 2.7G 十核": "Ultra 5 225",
    "Ultra 5 230F 2.7G 十核": "Ultra 5 230F",
    "Ultra 5 230 2.7G 十核": "Ultra 5 230",
    "Ultra 5 245KF 3.6G 十四核": "Ultra 5 245KF",
    "Ultra 5 245K 3.6G 十四核": "Ultra 5 245K",
    "Ultra 7 265KF 3.3G 二十核": "Ultra 7 265KF",
    "Ultra 7 265K 3.3G 二十核": "Ultra 7 265K",
    "Ultra 9 285K 3.2G 二十四核": "Ultra 9 285K",
    "Ultra 7 270K PLUS 盒装 24核心24线程性能不输U9 285K": "Ultra 7 270K PLUS",
    "锐龙 R5-5500X3D 3.0G 6核12线程帧数超过i5-14600KF": "R5-5500X3D",
    "锐龙 R5-5500 散 3.6G 6核12线程": "R5-5500",
    "锐龙 R5-5600 盒 3.5G 6核12线程": "R5-5600",
    "锐龙 R5-5600X 3.7G 6核12线程": "R5-5600X",
    "锐龙 R5-5600GT 3.6G 6核12线程 集显": "R5-5600GT",
    "锐龙 R7-5700X 3.4G 8核16线程": "R7-5700X",
    "锐龙 R5-7500F 3.7G 6核12线程": "R5-7500F",
    "锐龙 R7-7800X3D 5.0G 8核16线程 集显": "R7-7800X3D",
    "锐龙 R5-9500F 3.8G 6核12线程": "R5-9500F",
    "锐龙 R5-9600X 3.9G 6核12线程 集显": "R5-9600X",
    "锐龙 R7-9700X 3.8G 8核16线程 集显": "R7-9700X",
    "锐龙 R9-9900X 4.4G 12核24线程 集显": "R9-9900X",
    "锐龙 R9-9950X 4.3G 16核32线程 集显": "R9-9950X",
    "锐龙 R7-9800X3D 4.7G 8核16线程 集显": "R7-9800X3D",
    "锐龙 R7-9850X3D 4.7G 8核16线程 集显": "R7-9850X3D",
    "锐龙 R9-9950X3D 4.3G 16核32线程 集显": "R9-9950X3D",
}

# ---------------------- 提取 ￥ 后面的数字 ----------------------
def get_price_dict():
    try:
        resp = requests.get(URL, timeout=15)
        resp.encoding = "utf-8"
        text = resp.text

        price_map = {}
        # 匹配：名称 + ￥数字
        items = re.findall(r'([^\n]+?)\s*￥\s*(\d+)', text)
        for name, price in items:
            key = name.strip()
            price_map[key] = price.strip()

        print(f"✅ 成功提取 {len(price_map)} 个价格（只取￥后数字）")
        return price_map
    except Exception as e:
        print("❌ 获取价格失败")
        return {}

# ---------------------- 只替换 p:xxx ----------------------
def update_file():
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    price_map = get_price_dict()
    if not price_map:
        return

    count = 0
    print("\n开始更新 p: 价格...")

    for i in range(len(lines)):
        line = lines[i]
        # 匹配 {n:"xxx",p:数字}
        match = re.search(r'n:"([^"]+)"', line)
        if not match:
            continue

        item_name = match.group(1).strip()
        if item_name not in CPU_MAP:
            continue

        # 用简称去匹配价格
        short = CPU_MAP[item_name]
        final_price = None

        for key, price in price_map.items():
            if short in key:
                final_price = price
                break

        if final_price:
            # 只替换 p:数字
            new_line = re.sub(r'p:\d+', f'p:{final_price}', line)
            if new_line != line:
                lines[i] = new_line
                count += 1
                print(f"✅ {item_name} → p:{final_price}")

    # 写回 index.html
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n🎉 全部完成！共更新 {count} 个CPU价格！")

if __name__ == "__main__":
    update_file()
