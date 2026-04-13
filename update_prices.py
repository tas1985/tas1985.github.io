import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项（原有不变 + 新增主板配置） --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
# 【新增】网站D：主板爬取地址
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
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
# 【新增】主板定位：固定在这行正下方插入
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
# 【新增】主板过滤：排除铭瑄
MB_EXCLUDE = "铭瑄"
# 12个空格缩进（显卡/主板共用）
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

# -------------------------- 【新增】3. 爬取主板价格（自动过滤铭瑄） --------------------------
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
            # 核心：自动排除带「铭瑄」的主板
            if clean_name and price and MB_EXCLUDE not in clean_name:
                mb_list.append({"name": clean_name, "price": price})
                print(f"主板：{clean_name} | 价格：{price}")
                
        print(f"✅ 成功爬取 {len(mb_list)} 个主板（已过滤铭瑄）")
        return mb_list
    except Exception as e:
        print(f"❌ 爬取主板失败：{str(e)}")
        return []

# -------------------------- 4. 生成显卡格式（原有不变） --------------------------
def generate_gpu_content(gpu_list):
    content = [f"{GPU_START_MARK}\n"]
    for gpu in gpu_list:
        content.append(f'{INDENT}{{n:"{gpu["name"]}",p:{gpu["price"]}}},\n')
    content.append(f"{GPU_END_MARK}\n")
    return "".join(content)

# -------------------------- 【新增】5. 生成主板格式（12个空格） --------------------------
def generate_mb_content(mb_list):
    content = []
    for mb in mb_list:
        # 严格12空格 + 标准格式
        content.append(f'{INDENT}{{n:"{mb["name"]}",p:{mb["price"]}}},\n')
    return "".join(content)

# -------------------------- 6. 更新原有配件价格（原有不变） --------------------------
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

# -------------------------- 7. 纯标记驱动更新显卡（原有不变） --------------------------
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
        print(f"🎉 显卡更新完成！基于注释标记，12空格缩进")
    except Exception as e:
        print(f"❌ 更新显卡失败：{str(e)}")

# -------------------------- 【新增】8. 精准定位更新主板（小吹雪下一行 + 每日更新） --------------------------
def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 获取最新主板数据（已过滤铭瑄）
        mb_list = fetch_mb_prices()
        mb_content = generate_mb_content(mb_list)

        # 遍历找到目标行：华硕小吹雪
        target_index = -1
        for i, line in enumerate(lines):
            if MB_TARGET_LINE in line:
                target_index = i
                break

        if target_index == -1:
            print("❌ 未找到华硕小吹雪主板行，无法插入主板")
            return

        # 清理原有主板数据（从下一行开始，删除旧主板行）
        insert_pos = target_index + 1
        # 安全删除：只删除12空格开头的主板行，不碰其他代码
        while insert_pos < len(lines):
            current_line = lines[insert_pos]
            if current_line.startswith(INDENT) and '{n:"' in current_line:
                del lines[insert_pos]
            else:
                break

        # 插入新主板数据
        lines.insert(insert_pos, mb_content)

        # 保存文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"🎉 主板更新完成！定位在小吹雪下方，12空格，已过滤铭瑄")

    except Exception as e:
        print(f"❌ 更新主板失败：{str(e)}")

# -------------------------- 9. 双型号自动加价（原有不变，R5-5500X3D强制生效） --------------------------
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

# -------------------------- 主函数（原有功能 + 新增主板调用） --------------------------
if __name__ == "__main__":
    print("===== 全功能终极版 - CPU+显卡+主板 每日自动更新 =====")
    # 1. 更新原有CPU/配件价格（双加价不变）
    prices = fetch_latest_prices()
    if prices:
        count = update_html_prices(prices)
        print(f"✅ 配件价格更新完成：{count} 个")
    # 2. 更新显卡（原有不变）
    update_gpu_by_mark()
    # 3. 【新增】更新主板（精准定位+过滤铭瑄）
    update_mb_accurate()
    print("===== 全部执行完成 =====")
