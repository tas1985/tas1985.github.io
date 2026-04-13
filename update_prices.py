import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项 --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/532.36"
}

# 显卡专属标记（纯标记定位，无行号依赖）
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
# 12个空格缩进
INDENT = "            "

# -------------------------- 【核心】提取硬件纯型号 --------------------------
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

# -------------------------- 1. 爬取原有配件价格 --------------------------
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

# -------------------------- 2. 爬取显卡价格 --------------------------
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

# -------------------------- 3. 生成带12个空格的显卡数据 --------------------------
def generate_gpu_content(gpu_list):
    content = [f"{GPU_START_MARK}\n"]
    for gpu in gpu_list:
        content.append(f'{INDENT}{{n:"{gpu["name"]}",p:{gpu["price"]}}},\n')
    content.append(f"{GPU_END_MARK}\n")
    return "".join(content)

# -------------------------- 4. 更新原有配件价格 --------------------------
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

# -------------------------- 5. 纯标记驱动更新显卡 --------------------------
def update_gpu_by_mark():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        gpu_list = fetch_gpu_prices()
        new_content = generate_gpu_content(gpu_list)

        pattern = re.compile(
            re.escape(GPU_START_MARK) + r".*?" + re.escape(GPU_END_MARK),
            re.DOTALL
        )
        final_content = pattern.sub(new_content.strip(), content)

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"🎉 显卡更新完成！基于注释标记更新，12空格缩进")

    except Exception as e:
        print(f"❌ 更新显卡失败：{str(e)}")

# -------------------------- 6. 【修复】双型号自动加价（100%生效） --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict:
        return None
    
    target_model = extract_hardware_model(target_name)
    # 调试日志：打印识别到的名称和型号
    print(f"🔍 匹配CPU：{target_name} | 提取型号：{target_model}")
    
    best_match, score = process.extractOne(target_model, price_dict.keys(), scorer=process.fuzz.token_set_ratio)
    
    if score >= MATCH_THRESHOLD:
        original_price = price_dict[best_match]
        
        # 规则1：锐龙 R5-5600 +50元
        if target_model == "r55600":
            new_price = str(float(original_price) + 50)
            print(f"💰 R5-5600 加价：{original_price} → {new_price}")
            return new_price
        
        # 规则2：【修复强制生效】锐龙 R5-5500X3D 专属加价 +39元
        elif "R5-5500X3D" in target_name or target_model == "r55500x3d":
            new_price = str(float(original_price) + 39)
            print(f"💰 R5-5500X3D 加价成功：{original_price} → {new_price}")
            return new_price
        
        # 其他配件原价
        return original_price
    return None

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 纯标记定位版 - 全自动价格更新 =====")
    prices = fetch_latest_prices()
    if prices:
        count = update_html_prices(prices)
        print(f"✅ 配件价格更新完成：{count} 个")
    update_gpu_by_mark()
    print("===== 全部执行完成 =====")
