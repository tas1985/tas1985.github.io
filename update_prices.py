import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项 --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%86%85%E5%AD%98"
SSD_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%9B%BA%E6%80%81%E7%9B%98"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64 6.1; Win64; x64) AppleWebKit/537.36"}

# 配置
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手10天质保）",p:250},'
RAM_EXCLUDE_LIST = ["金百达", "金邦", "科摩思", "现代", "梵想"]
RAM_ASC_TECH_ADD = 50
SSD_EXCLUDE_LIST = ["金百达", "金士顿", "西部数据", "现代", "技嘉"]
SSD_TARGET_LINE = '{n:"品牌SSD 512G（到手10天质保）",p:149},'
INDENT = "            "
SSD_APPEND_INDENT = "            "

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

def extract_gpu_exact_key(name):
    name = name.strip().replace(" ", "").upper()
    brand = re.search(r"(七彩虹|微星)", name)
    model = re.search(r"(RTX\d+TI|RTX\d+)", name)
    vram = re.search(r"(\d+G)", name)
    series = re.search(r"(战斧|ULTRA|万图师|ADVANCED|银鲨)", name)
    key_parts = []
    if brand: key_parts.append(brand.group(1))
    if model: key_parts.append(model.group(1))
    if vram: key_parts.append(vram.group(1))
    if series: key_parts.append(series.group(1))
    return "|".join(key_parts)

def extract_ssd_exact_key(name):
    name = name.strip().replace(" ", "").upper()
    brand = re.search(r"(佰维|梵想|西数|致态|三星|雷克沙|宏碁)", name)
    model = re.search(r"(NV7400|NV3500|S500PRO|SN7100|TIPLUS7100|990PRO|雷神THOR|GM7)", name)
    cap = re.search(r"(\d+G|\d+TB|\d+T)", name)
    key_parts = []
    if brand: key_parts.append(brand.group(1))
    if model: key_parts.append(model.group(1))
    if cap: key_parts.append(cap.group(1))
    return "".join(key_parts)

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

def fetch_mb_prices():
    try:
        res = requests.get(MB_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return [{"name": n, "price": p} for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()) if MB_EXCLUDE not in n]
    except Exception:
        return []

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

def fetch_ssd_exact_data():
    try:
        res = requests.get(SSD_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ssd_map = {}
        ssd_list = []
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            if any(ex in n for ex in SSD_EXCLUDE_LIST):
                continue
            key = extract_ssd_exact_key(n)
            ssd_map[key] = int(float(p))
            ssd_list.append({"name": n, "price": int(float(p))})
        return ssd_map, ssd_list
    except Exception:
        return {}, []

# -------------------------- 生成格式函数 --------------------------
def generate_gpu_content(gpu_list):
    return "".join([f"{GPU_START_MARK}\n", *[f'{INDENT}{n:"{g["name"]}",p:{g["price"]}}},\n' for g in gpu_list], f"{GPU_END_MARK}\n"])

def generate_mb_content(mb_list):
    return "".join([f'{INDENT}{n:"{m["name"]}",p:{m["price"]}}},\n' for m in mb_list])

def generate_ram_content(ram_list):
    return "".join([f'{INDENT}{n:"{r["name"]}",p:{r["price"]}}},\n' for r in ram_list])

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

# -------------------------- 固定显卡精准更新 --------------------------
def update_fixed_gpu_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        gpu_map = fetch_gpu_exact_dict()
        updated = 0
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
            if not re.search(r'p:\d+', line): continue
            for gpu_name in target_gpus:
                if gpu_name in line:
                    key = extract_gpu_exact_key(gpu_name)
                    if key in gpu_map:
                        lines[i] = re.sub(r'p:\d+', f'p:{gpu_map[key]}', line)
                        updated += 1
                    break
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 显卡价格自动更新完成：{updated} 个")
        return updated
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")
        return 0

# -------------------------- 内存定制价格 --------------------------
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
            if not re.search(r"p:\d+(?:\.\d+)?", line): continue
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

# -------------------------- 固态硬盘精准更新（1T = 2T × 0.53） --------------------------
def update_ssd_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        ssd_map, ssd_list = fetch_ssd_exact_data()
        updated = 0

        # 你的定制价格规则
        nv7400_2t_price = ssd_map.get("佰维NV74002T", 0)
        nv7400_1t_custom_price = int(nv7400_2t_price * 0.53) if nv7400_2t_price > 0 else 0

        target_ssd = [
            "佰维 NV7400 512G TLC颗粒 读速7050MB/s",
            "佰维 NV3500 512G TLC颗粒",
            "佰维 NV3500 1T TLC颗粒",
            "佰维 NV7400 1T TLC颗粒 读速7400MB/s",
            "佰维 NV7400 2T TLC颗粒 读速7400MB/s",
            "梵想S500PRO-1T TLC颗粒",
            "梵想S500PRO-512GB TLC颗粒",
            "西数 黑盘SN7100 1T PCIE 4.0 读7250写6800",
            "致态 TIPlus7100-1TB PCIE 4.0 读7400，写6700",
            "三星 990 PRO 1T PCIE 4.0 读7450写6900",
            "雷克沙 雷神THOR 4T PCIE4.0 7000/6000",
            "品牌SSD 512G（到手10天质保）",
            "宏碁 GM7 2T PCIE 4.0 读7200写6300"
        ]

        for i in range(len(lines)):
            line = lines[i]
            if not re.search(r'p:\d+', line):
                continue
            for ssd_name in target_ssd:
                if ssd_name not in line:
                    continue
                # 核心定制：佰维 NV7400 1T = 2T × 0.53
                if "佰维 NV7400 1T TLC颗粒 读速7400MB/s" in ssd_name and nv7400_1t_custom_price > 0:
                    lines[i] = re.sub(r'p:\d+', f'p:{nv7400_1t_custom_price}', line)
                    updated += 1
                else:
                    key = extract_ssd_exact_key(ssd_name)
                    if key in ssd_map:
                        lines[i] = re.sub(r'p:\d+', f'p:{ssd_map[key]}', line)
                        updated += 1
                break

        # 插入新硬盘
        insert_idx = -1
        for i, line in enumerate(lines):
            if SSD_TARGET_LINE in line:
                insert_idx = i + 1
                break
        if insert_idx != -1:
            for ssd in ssd_list:
                lines.insert(insert_idx, f'{SSD_APPEND_INDENT}{n:"{ssd["name"]}",p:{ssd["price"]}}},\n')
                insert_idx += 1

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 固态硬盘更新完成：{updated} 个 | 佰维1T价格 = 2T×0.53")
        return updated
    except Exception as e:
        print(f"❌ 硬盘更新失败：{e}")
        return 0

# -------------------------- 主板/内存 自动更新 --------------------------
def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if MB_TARGET_LINE in l), -1)
        if idx == -1: return
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
        if idx == -1: return
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

    update_fixed_gpu_prices()
    update_exist_ram_prices()
    update_ssd_prices()
    update_mb_accurate()
    update_ram_accurate()

    print("===== ✅ 全部硬件价格更新完成 =====")
