import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项 --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%86%85%E5%AD%98"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36"}

# 显卡/主板/内存 配置
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手10天质保）",p:250},'
RAM_EXCLUDE_LIST = ["金百达", "金邦", "科摩思", "现代", "梵想"]
RAM_ASC_TECH_ADD = 50
INDENT = "            "

# -------------------------- 核心工具函数 --------------------------
def extract_hardware_model(name):
    if not name:
        return ""
    name = re.sub(r'[{n:"\",}]', '', name).lower().replace(" ", "").replace("-", "")
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
    return match.group() if match else name

def extract_ram_feature(name):
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威)"
    brand = re.search(brand_pattern, name).group() if re.search(brand_pattern, name) else ""
    capacity = re.search(r"\d+G", name).group() if re.search(r"\d+G", name) else ""
    freq = re.search(r"\d{4,5}", name).group() if re.search(r"\d{4,5}", name) else ""
    return f"{brand}_{capacity}_{freq}".strip("_")

# 【终极精准匹配：严格区分 5060/5060Ti/5070/5070Ti】
def extract_gpu_exact_key(name):
    name = name.strip().replace(" ", "").upper()
    brand = re.search(r"(七彩虹|微星)", name)
    
    # 优先匹配带TI的型号，绝对不混淆
    model = re.search(r"(RTX\d+TI|RTX\d+)", name)
    vram = re.search(r"(\d+G)", name)
    series = re.search(r"(战斧|ULTRA|万图师|ADVANCED|银鲨)", name)
    
    key_parts = []
    if brand:
        key_parts.append(brand.group(1))
    if model:
        key_parts.append(model.group(1))  # 保留完整型号 RTX5060 / RTX5060TI
    if vram:
        key_parts.append(vram.group(1))
    if series:
        key_parts.append(series.group(1))
    return "|".join(key_parts)

# -------------------------- 爬取函数 --------------------------
def fetch_latest_prices():
    try:
        res = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        price_dict = {extract_hardware_model(n): p for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text())}
        return price_dict
    except Exception:
        return {}

def fetch_gpu_exact_dict():
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        gpu_map = {}
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            k = extract_gpu_exact_key(n)
            gpu_map[k] = int(float(p))
        return gpu_map
    except Exception:
        return {}

def fetch_gpu_prices():
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return [{"name": n, "price": p} for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text())]
    except Exception:
        return []

def fetch_mb_prices():
    try:
        res = requests.get(MB_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return [{"name": n, "price": p} for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()) if MB_EXCLUDE not in n]
    except Exception:
        return {}

def fetch_raw_ram_prices():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ram_dict = {}
        for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            feat = extract_ram_feature(name)
            if feat:
                ram_dict[feat] = price
        return ram_dict
    except Exception:
        return {}

def fetch_processed_ram():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            if any(w in name for w in RAM_EXCLUDE_LIST):
                continue
            final_p = str(float(price) + RAM_ASC_TECH_ADD) if "阿斯加特" in name else price
            ram_list.append({"name": name, "price": final_p})
        return ram_list
    except Exception:
        return []

# -------------------------- 生成格式函数 --------------------------
def generate_gpu_content(gpu_list):
    return "".join([f"{GPU_START_MARK}\n", *[f'{INDENT}{{n:"{g["name"]}",p:{g["price"]}}},\n' for g in gpu_list], f"{GPU_END_MARK}\n"])

def generate_mb_content(mb_list):
    return "".join([f'{INDENT}{{n:"{m["name"]}",p:{m["price"]}}},\n' for m in mb_list])

def generate_ram_content(ram_list):
    return "".join([f'{INDENT}{{n:"{r["name"]}",p:{r["price"]}}},\n' for r in ram_list])

# -------------------------- CPU 更新 --------------------------
def update_html_prices(price_dict):
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        cnt = 0
        for i in range(START_LINE, END_LINE + 1):
            if i >= len(lines):
                break
            if not re.search(r"p:\d+(?:\.\d+)?", lines[i]):
                continue
            name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", lines[i]).strip()
            new_p = fuzzy_match_price(name, price_dict)
            if new_p:
                lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_p}", lines[i])
                cnt += 1
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return cnt
    except Exception:
        return 0

# -------------------------- 【14张显卡 终极精准更新】 --------------------------
def update_fixed_gpu_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        gpu_map = fetch_gpu_exact_dict()
        updated = 0

        # 你指定的完整显卡列表
        target_gpus = [
            "七彩虹 RTX5050 8G 战斧 DUO 双扇",
            "七彩虹 RTX5060 8G 战斧 DUO 双扇",
            "微星 RTX5060 8G 万图师白色",
            "微星 RTX3050 6G 万图师",
            "七彩虹 RTX5050 8G ULTRA W DUO 白色双扇",
            "七彩虹 RTX5060 8G ULTRA W OC 白色三扇",
            "七彩虹 RTX5060ti 8G 战斧 DUO 双扇",
            "七彩虹 RTX5060ti 16G 战斧 DUO 双扇",
            "七彩虹 RTX5060TI 16G ULTRA W DUO OC 白色双扇",
            "微星 RTX5070 VENTUS 2X OC 12G 万图师",
            "七彩虹 RTX5070 12G ULTRA W OC 白色",
            "七彩虹 RTX5070TI 16G 战斧豪华版 SFF",
            "微星 RTX5080万图师3X OC PLUS",
            "七彩虹 RTX5090D Advanced银鲨OC 24GB"
        ]

        for i in range(len(lines)):
            line = lines[i]
            if not re.search(r'p:\d+', line):
                continue
            for gpu_name in target_gpus:
                if gpu_name in line:
                    key = extract_gpu_exact_key(gpu_name)
                    if key in gpu_map:
                        new_price = gpu_map[key]
                        lines[i] = re.sub(r'p:\d+', f'p:{new_price}', line)
                        updated += 1
                    break

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 14张显卡价格自动更新完成：{updated} 个")
        return updated
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")
        return 0

# -------------------------- 内存定制价格（100%正确版） --------------------------
def update_exist_ram_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        ram_dict = fetch_raw_ram_prices()

        jbd_32g_6000_final = 0
        jbd_32g_3200_final = 0

        for i in range(len(lines)):
            line = lines[i]
            if "金百达_银爵 32G 6000(16*2)套装 c30 m-die" in line:
                ram_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
                feat = extract_ram_feature(ram_name)
                if feat in ram_dict:
                    base = float(ram_dict[feat])
                    jbd_32g_6000_final = base - 400
            if "金百达_银爵 32G 3200(16*2)套装" in line:
                ram_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
                feat = extract_ram_feature(ram_name)
                if feat in ram_dict:
                    jbd_32g_3200_final = float(ram_dict[feat])

        start = end = -1
        for i, line in enumerate(lines):
            if start == -1 and RAM_EXIST_START in line:
                start = i
            if RAM_EXIST_END in line:
                end = i
        if start == -1 or end == -1:
            print("❌ 未找到内存范围")
            return 0

        cnt = 0
        for i in range(start, end + 1):
            line = lines[i]
            if not re.search(r"p:\d+(?:\.\d+)?", line):
                continue

            ram_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
            feat = extract_ram_feature(ram_name)
            base_price = float(ram_dict.get(feat, 0))
            final_price = base_price

            if "阿斯加特_女武神 32G 3600(16*2)套装灯条" in ram_name:
                final_price = base_price + 150
            elif "阿斯加特 DDR4 64G（32X2）3200" in ram_name:
                final_price = jbd_32g_3200_final * 2.6
            elif "金百达_银爵 32G 6000(16*2)套装 c30 m-die" in ram_name:
                final_price = jbd_32g_6000_final
            elif "金百达_银爵 16G 6000单根 c30 m-die" in ram_name:
                final_price = jbd_32g_6000_final * 0.55
            elif "金百达_星刃 32G 6000 c28 海力士A-die 灯条" in ram_name:
                final_price = base_price - 150
            elif "宏碁掠夺者" in ram_name:
                final_price = base_price + 300
            elif "阿斯加特" in ram_name and "女武神" not in ram_name:
                final_price = base_price + 50

            lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{int(final_price)}", line)
            cnt += 1

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 内存定制价格更新完成：{cnt} 个")
        return cnt
    except Exception as e:
        print(f"❌ 内存更新失败：{e}")
        return 0

# -------------------------- 主板/内存 自动更新 --------------------------
def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if MB_TARGET_LINE in l), -1)
        if idx == -1:
            print("❌ 未找到主板插入位置")
            return
        pos = idx + 1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        lines.insert(pos, generate_mb_content(fetch_mb_prices()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("✅ 主板价格已实时更新")
    except Exception:
        print("❌ 主板更新失败")

def update_ram_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if RAM_INSERT_TARGET in l), -1)
        if idx == -1:
            print("❌ 未找到内存插入位置")
            return
        pos = idx + 1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        lines.insert(pos, generate_ram_content(fetch_processed_ram()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("✅ 内存价格已实时更新")
    except Exception:
        print("❌ 内存精准更新失败")

# -------------------------- CPU 加价逻辑 --------------------------
def fuzzy_match_price(name, price_dict):
    if not price_dict:
        return None
    model = extract_hardware_model(name)
    best, score = process.extractOne(model, price_dict.keys())
    if score < MATCH_THRESHOLD:
        return None
    p = float(price_dict[best])
    if model == "r55600":
        return str(int(p + 50))
    if "R5-5500X3D" in name or model == "r55500x3d":
        return str(int(p + 39))
    return str(int(p))

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 硬件价格每日自动更新程序启动 =====")
    cpu_prices = fetch_latest_prices()
    cpu_cnt = update_html_prices(cpu_prices)
    print(f"✅ CPU价格已更新：{cpu_cnt} 个")

    update_fixed_gpu_prices()    # 14张显卡 精准自动更新
    update_exist_ram_prices()    # 内存定制价格
    update_mb_accurate()         # 主板
    update_ram_accurate()        # 内存列表

    print("===== ✅ 全部硬件价格更新完成 =====")
