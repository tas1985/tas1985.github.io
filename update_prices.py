import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项 --------------------------
# 原配件爬取地址
SOURCE_URL = "http://0532.name/cpu_list"
# 显卡分类爬取地址（新增）
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
HTML_FILE = "index.html"
# 原有配件修改行号 761-817
START_LINE = 760
END_LINE = 816
# 显卡插入起始行号 906行（Python索引905）
GPU_INSERT_LINE = 905
# 匹配阈值
MATCH_THRESHOLD = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/532.36"
}

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

# -------------------------- 2. 【新增】爬取显卡价格 --------------------------
def fetch_gpu_prices():
    """爬取显卡分类页面的所有显卡名称+价格"""
    try:
        response = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        gpu_list = []

        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            # 清理显卡名称（去除多余符号/空格）
            clean_name = re.sub(r"\s+", " ", name.strip())
            if clean_name and price:
                gpu_list.append({"name": clean_name, "price": price})
                print(f"显卡：{clean_name} | 价格：{price}")

        print(f"\n✅ 成功爬取 {len(gpu_list)} 个显卡")
        return gpu_list

    except Exception as e:
        print(f"❌ 爬取显卡失败：{str(e)}")
        return []

# -------------------------- 3. 生成显卡标准格式行 --------------------------
def generate_gpu_lines(gpu_list):
    """生成和你要求一致的格式：{n:"显卡名",p:价格},"""
    gpu_lines = []
    for gpu in gpu_list:
        line = f'{{n:"{gpu["name"]}",p:{gpu["price"]}}},\n'
        gpu_lines.append(line)
    return gpu_lines

# -------------------------- 4. 原有配件价格更新 --------------------------
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
                new_line = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                lines[i] = new_line
                update_count += 1

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return update_count

    except Exception as e:
        print(f"❌ 修改配件价格失败：{str(e)}")
        return 0

# -------------------------- 5. 【新增】906行后自动更新显卡 --------------------------
def update_gpu_section(gpu_lines):
    """自动替换906行后的显卡区域，无重复、每日更新"""
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 安全处理：如果文件行数不足，补充空行
        while len(lines) <= GPU_INSERT_LINE:
            lines.append("\n")

        # 分割文件：前906行 + 新显卡行
        new_file_content = lines[:GPU_INSERT_LINE + 1]
        new_file_content.extend(gpu_lines)

        # 保存文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_file_content)

        print(f"🎉 显卡更新完成！成功写入 {len(gpu_lines)} 个显卡到906行后")

    except Exception as e:
        print(f"❌ 更新显卡失败：{str(e)}")

# -------------------------- 6. 模糊匹配+锐龙R5-5600自动加价50 --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict:
        return None

    target_model = extract_hardware_model(target_name)
    best_match, score = process.extractOne(
        target_model,
        price_dict.keys(),
        scorer=process.fuzz.token_set_ratio
    )

    if score >= MATCH_THRESHOLD:
        original_price = price_dict[best_match]
        # 定制加价：锐龙R5-5600 +50元
        if target_model == "r55600":
            new_price = str(float(original_price) + 50)
            print(f"💰 R5-5600 加价：{original_price} → {new_price}")
            return new_price
        return original_price
    return None

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 全功能版：配件+显卡 每日自动更新 =====")
    
    # 1. 更新原有核心配件价格
    prices = fetch_latest_prices()
    if prices:
        count = update_html_prices(prices)
        print(f"✅ 核心配件更新完成：{count} 个")

    # 2. 【新增】自动更新显卡（906行后）
    gpu_data = fetch_gpu_prices()
    if gpu_data:
        gpu_format_lines = generate_gpu_lines(gpu_data)
        update_gpu_section(gpu_format_lines)

    print("===== 全部任务执行结束 =====")
