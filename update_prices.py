import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项（原有100%保留） --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%86%85%E5%AD%98"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36"
}

# 显卡标记
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
# 主板配置
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
# 内存配置
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",p:750},'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",p:7958},'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手10天质保）",p:250},'
RAM_EXCLUDE_LIST = ["金百达", "金邦", "科摩思", "现代", "梵想"]
RAM_ASC_TECH_ADD = 50
INDENT = "            "

# -------------------------- 核心型号提取（不变） --------------------------
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

# -------------------------- 1. 爬取CPU原价（不变） --------------------------
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
        return price_dict
    except Exception as e:
        print(f"❌ 爬取配件失败：{str(e)}")
        return {}

# -------------------------- 2. 爬取显卡（不变） --------------------------
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
        return gpu_list
    except Exception as e:
        print(f"❌ 爬取显卡失败：{str(e)}")
        return []

# -------------------------- 3. 爬取主板（不变） --------------------------
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
        return mb_list
    except Exception as e:
        print(f"❌ 爬取主板失败：{str(e)}")
        return []

# -------------------------- 【修复】4. 爬取【原始内存原价】（无过滤无加价，专用于更新现有内存） --------------------------
def fetch_raw_ram_prices():
    try:
        response = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        ram_dict = {}
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)
        for name, price in matches:
            model = extract_hardware_model(name)
            if model:
                ram_dict[model] = price
        print(f"✅ 成功获取内存原始价格（用于更新现有内存）")
        return ram_dict
    except Exception as e:
        print(f"❌ 爬取原始内存失败：{str(e)}")
        return {}

# -------------------------- 5. 爬取【处理后内存】（过滤+加价，专用于新增内存） --------------------------
def fetch_processed_ram():
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
            excluded = any(word in clean_name for word in RAM_EXCLUDE_LIST)
            if excluded or not clean_name or not price:
                continue
            final_price = str(float(price) + RAM_ASC_TECH_ADD) if "阿斯加特" in clean_name else price
            ram_list.append({"name": clean_name, "price": final_price})
        return ram_list
    except Exception as e:
        print(f"❌ 爬取处理后内存失败：{str(e)}")
        return []

# -------------------------- 生成格式（不变） --------------------------
def generate_gpu_content(gpu_list):
    content = [f"{GPU_START_MARK}\n"]
    for gpu in gpu_list:
        content.append(f'{INDENT}{{n:"{gpu["name"]}",p:{gpu["price"]}}},\n')
    content.append(f"{GPU_END_MARK}\n")
    return "".join(content)
def generate_mb_content(mb_list):
    return "".join([f'{INDENT}{{n:"{mb["name"]}",p:{mb["price"]}}},\n' for mb in mb_list])
def generate_ram_content(ram_list):
    return "".join([f'{INDENT}{{n:"{ram["name"]}",p:{ram["price"]}}},\n' for ram in ram_list])

# -------------------------- 6. 更新CPU价格（不变） --------------------------
def update_html_prices(price_dict):
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        update_count = 0
        for i in range(START_LINE, END_LINE + 1):
            if i >= len(lines): break
            line = lines[i]
            price_match = re.search(r"p:(\d+(?:\.\d+)?)", line)
            if not price_match: continue
            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name: continue
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

# -------------------------- 【修复】7. 更新现有内存价格（用原始原价，价格100%准确） --------------------------
def update_exist_ram_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 获取【原始内存原价】
        ram_dict = fetch_raw_ram_prices()
        # 定位内存范围
        start_idx = end_idx = -1
        for i, line in enumerate(lines):
            if RAM_EXIST_START in line and start_idx == -1:
                start_idx = i
            if RAM_EXIST_END in line:
                end_idx = i
                break
        if start_idx == -1 or end_idx == -1:
            print("❌ 未找到现有内存范围")
            return 0

        update_count = 0
        for i in range(start_idx, end_idx + 1):
            line = lines[i]
            price_match = re.search(r"p:(\d+(?:\.\d+)?)", line)
            if not price_match: continue
            item_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
            if not item_name: continue

            target_model = extract_hardware_model(item_name)
            best_match, score = process.extractOne(target_model, ram_dict.keys(), scorer=process.fuzz.token_set_ratio)
            if score < MATCH_THRESHOLD: continue

            # 原始价格 + 阿斯加特单独加价
            original_price = ram_dict[best_match]
            new_price = str(float(original_price) + RAM_ASC_TECH_ADD) if "阿斯加特" in item_name else original_price
            
            lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
            update_count += 1
            print(f"✅ 内存更新：{item_name} | 新价格：{new_price}")

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"🎉 现有内存价格修复完成！更新：{update_count} 个")
        return update_count
    except Exception as e:
        print(f"❌ 修复内存价格失败：{str(e)}")
        return 0

# -------------------------- 显卡/主板/内存 插入更新（全部不变） --------------------------
def update_gpu_by_mark():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = generate_gpu_content(fetch_gpu_prices())
        final_content = re.compile(re.escape(GPU_START_MARK)+r".*?"+re.escape(GPU_END_MARK), re.DOTALL).sub(new_content.strip(), content)
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)
    except Exception as e:
        print(f"❌ 更新显卡失败：{str(e)}")

def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        target_index = next((i for i, line in enumerate(lines) if MB_TARGET_LINE in line), -1)
        if target_index == -1: return
        insert_pos = target_index + 1
        while insert_pos < len(lines) and lines[insert_pos].startswith(INDENT) and '{n:"' in lines[insert_pos]:
            del lines[insert_pos]
        lines.insert(insert_pos, generate_mb_content(fetch_mb_prices()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"❌ 更新主板失败：{str(e)}")

def update_ram_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        target_index = next((i for i, line in enumerate(lines) if RAM_INSERT_TARGET in line), -1)
        if target_index == -1: return
        insert_pos = target_index + 1
        while insert_pos < len(lines) and lines[insert_pos].startswith(INDENT) and '{n:"' in lines[insert_pos]:
            del lines[insert_pos]
        lines.insert(insert_pos, generate_ram_content(fetch_processed_ram()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"❌ 更新内存失败：{str(e)}")

# -------------------------- CPU双加价（不变） --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict: return None
    target_model = extract_hardware_model(target_name)
    best_match, score = process.extractOne(target_model, price_dict.keys(), scorer=process.fuzz.token_set_ratio)
    if score >= MATCH_THRESHOLD:
        original_price = price_dict[best_match]
        if target_model == "r55600":
            return str(float(original_price) + 50)
        elif "R5-5500X3D" in target_name or target_model == "r55500x3d":
            return str(float(original_price) + 39)
        return original_price
    return None

# -------------------------- 主函数（修复调用） --------------------------
if __name__ == "__main__":
    print("===== 全功能修复版 - 内存价格已校准 =====")
    # 1. 更新CPU
    price_dict = fetch_latest_prices()
    if price_dict:
        update_html_prices(price_dict)
    # 2. 【修复】更新现有内存（原价校准）
    update_exist_ram_prices()
    # 3. 更新显卡+主板
    update_gpu_by_mark()
    update_mb_accurate()
    # 4. 新增内存
    update_ram_accurate()
    print("===== 全部执行完成 =====")
