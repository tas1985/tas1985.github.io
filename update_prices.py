import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项（原有100%保留 + 新增内存配置） --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
# 【新增】网站E：内存爬取地址
RAM_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%86%85%E5%AD%98"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/532.36"
}

# 显卡专属标记（原有不变）
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
# 主板定位（原有不变）
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
# 【新增】内存配置
# 现有内存更新范围：起始行标识 + 结束行标识
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",p:750},'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",p:7958},'
# 内存插入位置：三星DDR3 16G下一行
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手10天质保）",p:250},'
# 内存过滤品牌（排除）
RAM_EXCLUDE_LIST = ["金百达", "金邦", "科摩思", "现代", "梵想"]
# 阿斯加特内存统一加价50元
RAM_ASC_TECH_ADD = 50
# 12个空格缩进（全配件共用）
INDENT = "            "

# -------------------------- 【核心】提取硬件纯型号（原有不变） --------------------------
def extract_hardware_model(name):
    if not name:
        return ""
    name = re.sub(r'[{n:"\",}]', '', name)
    name = name.lower().replace(" ", "").replace("-", "")
    pattern = re.compile(
        r'(i[3579]\d+[a-z0-9]*)|'
        r'(r[3579]\d+[a-z0-9]*)|'
        r'(rtx\d+[a-z0-9]*)|'
        r'(gtx\d+[a-z0-9]*)|'
        r'(amd\d+[a-z0-9]*)|'
        r'(\d+gb)|'
        r'(\d+[a-z]+\d*)'
    )
    match = pattern.search(name)
    if match:
        return [m for m in match.groups() if m][0]
    return name

# -------------------------- 1. 爬取原有配件价格（原有不变） --------------------------
def fetch_latest_prices():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        price_dict = {}
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)
        for name, price in matches:
            model = extract_hardware_model(name)
            if model:
                price_dict[model] = price
        print(f"✅ 成功爬取 {len(price_dict)} 个核心配件")
        return price_dict
    except Exception as e:
        print(f"❌ 爬取配件失败：{str(e)}")
        return {}

# -------------------------- 2. 爬取显卡价格（原有不变） --------------------------
def fetch_gpu_prices():
    try:
        response = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        gpu_list = []
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)
        for name, price in matches:
            clean_name = re.sub(r"\s+", " ", name.strip())
            if clean_name and price:
                gpu_list.append({"name": clean_name, "price": price})
        print(f"✅ 成功爬取 {len(gpu_list)} 个显卡")
        return gpu_list
    except Exception as e:
        print(f"❌ 爬取显卡失败：{str(e)}")
        return []

# -------------------------- 3. 爬取主板价格（原有不变） --------------------------
def fetch_mb_prices():
    try:
        response = requests.get(MB_SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        mb_list = []
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)
        for name, price in matches:
            clean_name = re.sub(r"\s+", " ", name.strip())
            if clean_name and price and MB_EXCLUDE not in clean_name:
                mb_list.append({"name": clean_name, "price": price})
        print(f"✅ 成功爬取 {len(mb_list)} 个主板（已过滤铭瑄）")
        return mb_list
    except Exception as e:
        print(f"❌ 爬取主板失败：{str(e)}")
        return []

# -------------------------- 【新增】4. 爬取内存价格（过滤品牌 + 阿斯加特加价） --------------------------
def fetch_ram_prices():
    try:
        response = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        ram_list = []
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            clean_name = re.sub(r"\s+", " ", name.strip())
            # 过滤：排除指定5个品牌
            excluded = any(word in clean_name for word in RAM_EXCLUDE_LIST)
            if excluded or not clean_name or not price:
                continue
            
            # 阿斯加特内存统一+50元
            final_price = price
            if "阿斯加特" in clean_name:
                final_price = str(float(price) + RAM_ASC_TECH_ADD)
                print(f"💰 阿斯加特内存加价：{price} → {final_price}")

            ram_list.append({"name": clean_name, "price": final_price})
            print(f"内存：{clean_name} | 价格：{final_price}")

        print(f"✅ 成功爬取 {len(ram_list)} 个内存（已过滤品牌+阿斯加特加价）")
        return ram_list
    except Exception as e:
        print(f"❌ 爬取内存失败：{str(e)}")
        return []

# -------------------------- 5. 生成显卡格式（原有不变） --------------------------
def generate_gpu_content(gpu_list):
    content = [f"{GPU_START_MARK}\n"]
    for gpu in gpu_list:
        content.append(f'{INDENT}{{n:"{gpu["name"]}",p:{gpu["price"]}}},\n')
    content.append(f"{GPU_END_MARK}\n")
    return "".join(content)

# -------------------------- 6. 生成主板格式（原有不变） --------------------------
def generate_mb_content(mb_list):
    content = []
    for mb in mb_list:
        content.append(f'{INDENT}{{n:"{mb["name"]}",p:{mb["price"]}}},\n')
    return "".join(content)

# -------------------------- 【新增】7. 生成内存格式（12空格） --------------------------
def generate_ram_content(ram_list):
    content = []
    for ram in ram_list:
        content.append(f'{INDENT}{{n:"{ram["name"]}",p:{ram["price"]}}},\n')
    return "".join(content)

# -------------------------- 8. 更新原有CPU配件价格（原有不变） --------------------------
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
            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name:
                continue
            new_price = fuzzy_match_price(item_name, price_dict)
            if new_price:
                lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                update_count += 1
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return update_count
    except Exception as e:
        print(f"❌ 修改配件价格失败：{str(e)}")
        return 0

# -------------------------- 【新增】9. 更新现有内存价格（仿照CPU方式 + 阿斯加特+50） --------------------------
def update_exist_ram_prices(ram_dict):
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 定位现有内存的起止行
        start_idx = end_idx = -1
        for i, line in enumerate(lines):
            if RAM_EXIST_START in line and start_idx == -1:
                start_idx = i
            if RAM_EXIST_END in line:
                end_idx = i
                break
        if start_idx == -1 or end_idx == -1:
            print("❌ 未找到现有内存范围，跳过更新")
            return 0

        update_count = 0
        # 遍历内存范围，模糊匹配更新价格
        for i in range(start_idx, end_idx + 1):
            line = lines[i]
            price_match = re.search(r"p:(\d+(?:\.\d+)?)", line)
            if not price_match:
                continue
            item_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
            if not item_name:
                continue

            # 模糊匹配
            target_model = extract_hardware_model(item_name)
            best_match, score = process.extractOne(target_model, ram_dict.keys(), scorer=process.fuzz.token_set_ratio)
            if score < MATCH_THRESHOLD:
                continue

            original_price = ram_dict[best_match]
            # 阿斯加特内存+50
            if "阿斯加特" in item_name:
                new_price = str(float(original_price) + RAM_ASC_TECH_ADD)
                print(f"💰 现有阿斯加特内存加价：{original_price} → {new_price}")
            else:
                new_price = original_price

            # 替换价格
            lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
            update_count += 1

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 现有内存价格更新完成：{update_count} 个")
        return update_count
    except Exception as e:
        print(f"❌ 更新现有内存失败：{str(e)}")
        return 0

# -------------------------- 10. 显卡更新（原有不变） --------------------------
def update_gpu_by_mark():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        gpu_list = fetch_gpu_prices()
        new_content = generate_gpu_content(gpu_list)
        pattern = re.compile(re.escape(GPU_START_MARK) + r".*?" + re.escape(GPU_END_MARK), re.DOTALL)
        final_content = pattern.sub(new_content.strip(), content)
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"🎉 显卡更新完成！")
    except Exception as e:
        print(f"❌ 更新显卡失败：{str(e)}")

# -------------------------- 11. 主板更新（原有不变） --------------------------
def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        mb_list = fetch_mb_prices()
        mb_content = generate_mb_content(mb_list)
        target_index = -1
        for i, line in enumerate(lines):
            if MB_TARGET_LINE in line:
                target_index = i
                break
        if target_index == -1:
            print("❌ 未找到小吹雪主板行")
            return
        insert_pos = target_index + 1
        while insert_pos < len(lines):
            current_line = lines[insert_pos]
            if current_line.startswith(INDENT) and '{n:"' in current_line:
                del lines[insert_pos]
            else:
                break
        lines.insert(insert_pos, mb_content)
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"🎉 主板更新完成！")
    except Exception as e:
        print(f"❌ 更新主板失败：{str(e)}")

# -------------------------- 【新增】12. 内存精准插入更新（指定位置+12空格） --------------------------
def update_ram_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        ram_list = fetch_ram_prices()
        ram_content = generate_ram_content(ram_list)
        # 定位三星DDR3 16G行
        target_index = -1
        for i, line in enumerate(lines):
            if RAM_INSERT_TARGET in line:
                target_index = i
                break
        if target_index == -1:
            print("❌ 未找到三星内存行")
            return
        # 删除旧内存数据
        insert_pos = target_index + 1
        while insert_pos < len(lines):
            current_line = lines[insert_pos]
            if current_line.startswith(INDENT) and '{n:"' in current_line:
                del lines[insert_pos]
            else:
                break
        # 插入新内存
        lines.insert(insert_pos, ram_content)
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"🎉 内存新增/更新完成！")
    except Exception as e:
        print(f"❌ 更新内存失败：{str(e)}")

# -------------------------- 13. 双CPU自动加价（原有不变，100%生效） --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict:
        return None
    target_model = extract_hardware_model(target_name)
    best_match, score = process.extractOne(target_model, price_dict.keys(), scorer=process.fuzz.token_set_ratio)
    
    if score >= MATCH_THRESHOLD:
        original_price = price_dict[best_match]
        # 锐龙 R5-5600 +50元
        if target_model == "r55600":
            new_price = str(float(original_price) + 50)
            print(f"💰 R5-5600 加价：{original_price} → {new_price}")
            return new_price
        # 锐龙 R5-5500X3D 强制加价+39元
        elif "R5-5500X3D" in target_name or target_model == "r55500x3d":
            new_price = str(float(original_price) + 39)
            print(f"💰 R5-5500X3D 加价成功：{original_price} → {new_price}")
            return new_price
        return original_price
    return None

# -------------------------- 主函数（原有功能 + 新增内存两步操作） --------------------------
if __name__ == "__main__":
    print("===== 全功能终极版 - CPU+显卡+主板+内存 每日自动更新 =====")
    # 1. 更新原有CPU配件价格（原有不变）
    prices = fetch_latest_prices()
    if prices:
        update_html_prices(prices)
    
    # 2. 【新增】第一步：爬取内存并更新现有内存价格
    ram_dict = {extract_hardware_model(item["name"]): item["price"] for item in fetch_ram_prices()}
    update_exist_ram_prices(ram_dict)
    
    # 3. 原有功能：更新显卡 + 主板
    update_gpu_by_mark()
    update_mb_accurate()
    
    # 4. 【新增】第二步：新增/更新内存列表（指定位置+过滤+加价）
    update_ram_accurate()
    
    print("===== 全部任务执行完成 =====")
