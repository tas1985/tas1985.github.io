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
# 新增机箱URL配置
CASE_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%9C%BA%E7%AE%B1"
# 新增电源URL配置
POWER_SOURCE_URL = "http://0532.name/cpu_list?category=%E7%94%B5%E6%BA%90"
# 新增散热器URL配置
COOLER_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%95%A3%E7%83%AD%E5%99%A8"
HTML_FILE = "index.html"
START_LINE = 958
END_LINE = 1014
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 配置
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手10天质保）",p:250},'
RAM_EXCLUDE_LIST = ["金百达", "金士顿", "科摩思", "现代", "梵想"]
RAM_ASC_TECH_ADD = 50
SSD_EXCLUDE_LIST = ["金百达", "金士顿", "西部数据", "现代", "技嘉"]
SSD_TARGET_LINE = '{n:"品牌SSD 512G（到手10天质保）",p:149},'
# 新增机箱配置
CASE_TARGET_LINE = '{n:"乔思伯 TK1 星舰仓",p:499},'
CASE_INDENT = "            "  # 12个空格
# 新增电源配置
POWER_TARGET_LINE = '{n:"追风者 AMP GH850 850W 金牌全模组 ATX3.1 蟒纹线 白色",p:750},'
POWER_EXCLUDE_LIST = ["玄武", "Tt"]
POWER_INDENT = "            "  # 12个空格
# 新增散热器配置
COOLER_TARGET_LINE = '{n:"创氪星系展域SE 360 ARGB 白色 6.5寸裸眼3D屏幕",p:1549},'
COOLER_BRANDS = ["钛钽", "瓦尔基里", "华硕", "利民", "九州风神", "乔思伯"]
COOLER_INDENT = "            "  # 12个空格
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
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光)"
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|Corsair|芝奇|DDR4|DDR5|马甲条|灯条)"
    brand = re.search(brand_pattern, name).group() if re.search(brand_pattern, name) else ""
    series = re.search(series_pattern, name).group() if re.search(series_pattern, name) else ""
    capacity = re.search(r"\d+G", name).group() if re.search(r"\d+G", name) else ""
    freq = re.search(r"\d{4,5}", name).group() if re.search(r"\d{4,5}", name) else ""
    return f"{brand}_{series}_{capacity}_{freq}".strip("_")

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

def fetch_gpu_prices():
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        gpu_list = []
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            price = int(float(p))
            # 🔥 新增规则：名称含「白」→ 价格 +100
            if "白" in n:
                price += 100
            gpu_list.append({"name": n, "price": price})
        return gpu_list
    except Exception:
        return []

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
        raw_text = soup.get_text()
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", raw_text):
            if any(ex in n for ex in SSD_EXCLUDE_LIST):
                continue
            key = extract_ssd_exact_key(n)
            ssd_map[key] = int(float(p))
            ssd_list.append({"name": n, "price": int(float(p))})
        return ssd_map, ssd_list
    except Exception:
        return {}, []

# 新增机箱爬取函数
def fetch_case_prices():
    try:
        res = requests.get(CASE_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        case_list = []
        # 提取机箱名称和价格，格式和其他硬件保持一致
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            # 价格转为整数，保持和其他硬件统一格式
            case_list.append({"name": n.strip(), "price": int(float(p))})
        return case_list
    except Exception as e:
        print(f"❌ 机箱数据爬取失败：{e}")
        return []

# 新增电源爬取函数
def fetch_power_prices():
    try:
        res = requests.get(POWER_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        power_list = []
        # 提取电源名称和价格，排除玄武、Tt
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            # 排除包含玄武、Tt的电源
            if any(ex in n for ex in POWER_EXCLUDE_LIST):
                continue
            # 价格转为整数，保持格式统一
            power_list.append({"name": n.strip(), "price": int(float(p))})
        return power_list
    except Exception as e:
        print(f"❌ 电源数据爬取失败：{e}")
        return []

# 新增散热器爬取函数
def fetch_cooler_prices():
    try:
        res = requests.get(COOLER_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        cooler_list = []
        # 提取散热器名称和价格，只包含指定品牌
        for n, p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            # 只包含指定品牌的散热器
            if any(brand in n for brand in COOLER_BRANDS):
                # 价格转为整数，保持格式统一
                cooler_list.append({"name": n.strip(), "price": int(float(p))})
        return cooler_list
    except Exception as e:
        print(f"❌ 散热器数据爬取失败：{e}")
        return []

# -------------------------- 生成格式函数 --------------------------
def generate_gpu_content(gpu_list):
    return "".join([f'{INDENT}{{n:"{g["name"]}",p:{g["price"]}}},\n' for g in gpu_list])

def generate_mb_content(mb_list):
    return "".join([f'{INDENT}{{n:"{m["name"]}",p:{m["price"]}}},\n' for m in mb_list])

def generate_ram_content(ram_list):
    return "".join([f'{INDENT}{{n:"{r["name"]}",p:{r["price"]}}},\n' for r in ram_list])

# 新增机箱内容生成函数
def generate_case_content(case_list):
    return "".join([f'{CASE_INDENT}{{n:"{c["name"]}",p:{c["price"]}}},\n' for c in case_list])

# 新增电源内容生成函数
def generate_power_content(power_list):
    return "".join([f'{POWER_INDENT}{{n:"{p["name"]}",p:{p["price"]}}},\n' for p in power_list])

# 新增散热器内容生成函数
def generate_cooler_content(cooler_list):
    return "".join([f'{COOLER_INDENT}{{n:"{c["name"]}",p:{c["price"]}}},\n' for c in cooler_list])

def find_ssd_target_position(lines, target_line):
    """查找SSD目标位置"""
    for i, line in enumerate(lines):
        if target_line in line:
            return i
    return -1

def find_next_non_ssd_line(lines, start_pos):
    """查找下一个非SSD行的位置"""
    pos = start_pos + 1
    while pos < len(lines):
        line = lines[pos]
        # 检查是否是SSD数据行
        if line.strip().startswith('{n:"') and '"p:' in line and line.rstrip().endswith('},'):
            pos += 1
        else:
            # 检查缩进是否与SSD行一致
            stripped = line.lstrip()
            if stripped:  # 非空行
                leading_spaces = len(line) - len(stripped)
                if leading_spaces == len(SSD_APPEND_INDENT):  # 与SSD缩进相同
                    pos += 1
                else:
                    break
            else:  # 空行也认为不是SSD数据行
                break
    return pos

def update_ssd_prices():
    """修复后的SSD价格更新函数"""
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        ssd_map, ssd_list = fetch_ssd_exact_data()
        updated = 0

        # 计算特定硬盘价格
        nv7400_2t_price = 0
        for key in ssd_map:
            if "佰维" in key and "NV7400" in key and ("2T" in key or "2TB" in key):
                nv7400_2t_price = ssd_map[key]
                break

        nv7400_1t_price = int(nv7400_2t_price * 0.53) if nv7400_2t_price > 0 else 0

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

        # 更新特定SSD价格
        for i in range(len(lines)):
            line = lines[i]
            if not re.search(r'p:\d+', line):
                continue

            if "佰维 NV7400 1T TLC颗粒 读速7400MB/s" in line:
                if nv7400_1t_price > 0:
                    # 价格按更新后再减去90
                    final_price = nv7400_1t_price - 90
                    lines[i] = re.sub(r'p:\d+', f'p:{final_price}', line)
                    updated += 1
                    continue

            if "佰维 NV7400 2T TLC颗粒 读速7400MB/s" in line:
                if nv7400_2t_price > 0:
                    # 价格按更新后再减去300
                    final_price = nv7400_2t_price - 300
                    lines[i] = re.sub(r'p:\d+', f'p:{final_price}', line)
                    updated += 1
                    continue

            for ssd_name in target_ssd:
                if ssd_name in line:
                    key = extract_ssd_exact_key(ssd_name)
                    if key in ssd_map:
                        # 检查是否是需要特殊处理的型号
                        if ssd_name == "佰维 NV7400 2T TLC颗粒 读速7400MB/s" and nv7400_2t_price > 0:
                            # 价格按更新后再减去300
                            final_price = nv7400_2t_price - 300
                            lines[i] = re.sub(r'p:\d+', f'p:{final_price}', line)
                        else:
                            lines[i] = re.sub(r'p:\d+', f'p:{ssd_map[key]}', line)
                        updated += 1
                    break

        # 查找SSD目标位置和范围
        target_idx = find_ssd_target_position(lines, SSD_TARGET_LINE)
        if target_idx != -1:
            # 找到目标行之后的所有SSD行，删除它们
            start_pos = target_idx + 1
            end_pos = find_next_non_ssd_line(lines, target_idx)
            
            # 删除现有的SSD数据行
            del lines[start_pos:end_pos]
            
            # 准备新SSD数据（只包含不在目标列表中的新硬盘）
            existing_names = set(target_ssd)  # 已经处理过的SSD名称
            new_ssd_lines = []
            
            for ssd in ssd_list:
                # 检查这个SSD是否已经在目标列表中（即是否已更新价格）
                found_in_targets = False
                for target_name in target_ssd:
                    if target_name in ssd["name"]:
                        found_in_targets = True
                        break
                
                # 只添加不在目标列表中的新SSD
                if not found_in_targets:
                    new_ssd_lines.append(f'{SSD_APPEND_INDENT}{{n:"{ssd["name"]}",p:{ssd["price"]}}},\n')
            
            # 在目标位置后插入新的SSD数据
            if new_ssd_lines:
                for i, new_line in enumerate(new_ssd_lines):
                    lines.insert(start_pos + i, new_line)

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # 计算调整后的价格
        adjusted_2t_price = nv7400_2t_price - 300 if nv7400_2t_price > 0 else 0
        adjusted_1t_price = nv7400_1t_price - 90 if nv7400_1t_price > 0 else 0
        
        print(f"✅ 固态硬盘更新完成")
        print(f"🧮 佰维 NV7400 2T 原始价格 = {nv7400_2t_price}")
        print(f"🧮 佰维 NV7400 2T 调整后价格 = {adjusted_2t_price} (-300)")
        print(f"🧮 佰维 NV7400 1T 原始价格 = {nv7400_1t_price} (2T × 0.53)")
        print(f"🧮 佰维 NV7400 1T 调整后价格 = {adjusted_1t_price} (-90)")
        print(f"🧮 更新了 {updated} 个已知SSD价格")
        print(f"🧮 添加了 {len(new_ssd_lines)} 个新SSD型号")
        return updated
    except Exception as e:
        print(f"❌ 硬盘更新失败：{e}")
        return 0

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

# -------------------------- 修改后的显卡更新逻辑 --------------------------
def update_gpu_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 找到GPU_START_MARK的位置
        start_idx = next((i for i, l in enumerate(lines) if GPU_START_MARK in l), -1)
        if start_idx == -1:
            print("❌ 未找到显卡自动更新区域开始标记")
            return
        
        # 从开始标记的下一行开始查找结束标记
        end_idx = next((i for i, l in enumerate(lines[start_idx + 1:], start_idx + 1) if GPU_END_MARK in l), -1)
        if end_idx == -1:
            print("❌ 未找到显卡自动更新区域结束标记")
            return
        
        # 删除开始标记和结束标记之间的所有内容（不包括这两个标记本身）
        del lines[start_idx + 1:end_idx]
        
        # 获取新的显卡数据
        gpu_list = fetch_gpu_prices()
        
        # 生成显卡内容（注意这里不需要包含开始和结束标记）
        gpu_content = generate_gpu_content(gpu_list)
        
        # 在开始标记后插入新的显卡数据
        lines.insert(start_idx + 1, gpu_content)
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"✅ 显卡价格自动更新完成，共更新 {len(gpu_list)} 个显卡型号")
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")

# -------------------------- 固定显卡精准更新（已废弃，保留原逻辑）--------------------------
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
            if not re.search(r'p:\d+', line):
                continue
            for gpu_name in target_gpus:
                if gpu_name in line:
                    key = extract_gpu_exact_key(gpu_name)
                    if key in gpu_map:
                        price = gpu_map[key]
                        # 🔥 白色显卡 +100
                        if "白" in gpu_name:
                            price += 100
                        lines[i] = re.sub(r'p:\d+', f'p:{price}', line)
                        updated += 1
                    break
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 显卡价格自动更新完成：{updated} 个（白色显卡已+100）")
        return updated
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")
        return 0

# -------------------------- 内存定制价格（四要素匹配） --------------------------
def extract_ram_four_key(name):
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光)"
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|DDR4|DDR5|马甲条|灯条)"
    cas_pattern = r"(C\d+)"
    brand = re.search(brand_pattern, name).group() if re.search(brand_pattern, name) else ""
    series = re.search(series_pattern, name).group() if re.search(series_pattern, name) else ""
    cas = re.search(cas_pattern, name).group() if re.search(cas_pattern, name) else ""
    capacity = re.search(r"\d+G", name).group() if re.search(r"\d+G", name) else ""
    freq = re.search(r"\d{4,5}", name).group() if re.search(r"\d{4,5}", name) else ""
    return brand, series, cas, capacity, freq

def update_exist_ram_prices():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        ram_list = fetch_raw_ram_prices_with_details()
        if not ram_list:
            print("❌ 未能获取到内存数据")
            return 0
        
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
        jbd_32g_6000_final = 0
        jbd_32g_3200_final = 0

        for i in range(start, end + 1):
            line = lines[i]
            if not re.search(r"p:\d+(?:\.\d+)?", line):
                continue

            match = re.search(r'{n:"([^"]+)"', line)
            if not match:
                continue

            ram_name = match.group(1)
            final_price = None
            special_handled = False

            if "金百达_银爵 32G 6000(16*2)套装 c30 m-die" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 32G 16x2 6000 D5 C30")
                for ram_item in ram_list:
                    if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "6000" in ram_item['name'] and "C30" in ram_item['name']:
                        final_price = float(ram_item['price'])
                        jbd_32g_6000_final = final_price
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {ram_item['name']} -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到金百达 银爵 32G 16x2 6000 D5 C30，跳过更新")
                    special_handled = True
            elif "金百达_银爵 32G 6000(16*2)套装 c36" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 32G 16x2 6000 D5 C36 长鑫")
                for ram_item in ram_list:
                    if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "6000" in ram_item['name'] and "C36" in ram_item['name']:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {ram_item['name']} -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到金百达 银爵 32G 16x2 6000 D5 C36 长鑫，跳过更新")
                    special_handled = True
            elif "金百达_银爵 16G 6000单根 c30 m-die" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 32G 16x2 6000 D5 C30 的一半")
                for ram_item in ram_list:
                    if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "6000" in ram_item['name'] and "C30" in ram_item['name']:
                        final_price = float(ram_item['price']) / 2
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {ram_item['name']}/2 -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到金百达 银爵 32G 16x2 6000 D5 C30，跳过更新")
                    special_handled = True
            elif "金百达_星刃 32G 6000 c28 海力士A-die 灯条" in ram_name:
                print(f"  🔍 查找: 宏碁掠夺者 冰刃 32G 6000D5 16*2 C28 RGB")
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "宏碁掠夺者" in item_name and "冰刃" in item_name and "6000" in item_name and "C28" in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到宏碁掠夺者 冰刃 6000 C28，跳过更新")
                    special_handled = True

            if not special_handled:
                target_brand, target_series, target_cas, target_capacity, target_freq = extract_ram_four_key(ram_name)

                matched_price = None
                best_score = 0

                for ram_item in ram_list:
                    source_brand, source_series, source_cas, source_capacity, source_freq = ram_item['key']
                    price = ram_item['price']

                    score = 0
                    if target_brand and source_brand and target_brand == source_brand:
                        score += 20
                    if target_series and source_series and target_series == source_series:
                        score += 20
                    if target_cas and source_cas and target_cas == source_cas:
                        score += 20
                    if target_capacity and source_capacity and target_capacity == source_capacity:
                        score += 20
                    if target_freq and source_freq and target_freq == source_freq:
                        score += 20

                    if score > best_score:
                        best_score = score
                        matched_price = price

                if matched_price is not None and best_score >= 60:
                    base_price = float(matched_price)
                    final_price = base_price

                    if "阿斯加特_女武神 32G 3600(16*2)套装灯条" in ram_name:
                        final_price = base_price + 150
                    elif "阿斯加特 DDR4 64G（32X2）3200" in ram_name:
                        final_price = jbd_32g_3200_final * 2.6
                    elif "金百达_银爵 32G 3200(16*2)套装" in ram_name:
                        jbd_32g_3200_final = base_price
                    elif "宏碁掠夺者" in ram_name:
                        final_price = base_price + 300
                    elif "阿斯加特" in ram_name and "女武神" not in ram_name:
                        final_price = base_price + 50

                    print(f"  ✓ 匹配成功 [{best_score}分]: {ram_name} -> 价格 {int(final_price)}")
                else:
                    print(f"  ✗ 未匹配到: {ram_name} (品牌:{target_brand}, 系列:{target_series}, 时序:{target_cas}, 容量:{target_capacity}, 频率:{target_freq})")

            if final_price is not None:
                lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{int(final_price)}", line)
                cnt += 1
        
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 内存定制价格更新完成：{cnt} 个")
        return cnt
    except Exception as e:
        print(f"❌ 内存更新失败：{e}")
        import traceback
        traceback.print_exc()
        return 0

def fetch_raw_ram_prices_with_details():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        all_items = []
        for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            brand, series, cas, capacity, freq = extract_ram_four_key(name)
            if brand or series or cas or capacity or freq:
                ram_list.append({
                    'name': name,
                    'key': (brand, series, cas, capacity, freq),
                    'price': price
                })
            all_items.append((name, price))
        print(f"\n📋 网站内存数据 (共{len(all_items)}个):")
        for n, p in all_items[:30]:
            print(f"   {n} -> {p}")
        if len(all_items) > 30:
            print(f"   ... 还有 {len(all_items)-30} 个")
        return ram_list
    except Exception as e:
        print(f"❌ 获取内存数据失败：{e}")
        return []

# -------------------------- 主板/内存 自动更新 --------------------------
def update_mb_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if MB_TARGET_LINE in l), -1)
        if idx == -1:
            return
        pos = idx + 1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        lines.insert(pos, generate_mb_content(fetch_mb_prices()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass

def update_ram_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if RAM_INSERT_TARGET in l), -1)
        if idx == -1:
            return
        pos = idx + 1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        lines.insert(pos, generate_ram_content(fetch_processed_ram()))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass

# 新增机箱自动更新函数
def update_case_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 爬取机箱数据，创建型号到价格的映射
        case_list = fetch_case_prices()
        case_map = {}
        for case in case_list:
            name = case["name"]
            # 使用完整名称作为键
            case_map[name] = case["price"]
            # 提取型号部分作为键，提高匹配成功率
            # 尝试提取品牌后的型号部分
            parts = name.split(" ")
            if len(parts) > 1:
                # 尝试不同的型号提取方式
                for i in range(1, len(parts)):
                    model = " ".join(parts[i:])
                    case_map[model] = case["price"]
        
        # 找到机箱区域的开始位置
        idx = next((i for i, l in enumerate(lines) if CASE_TARGET_LINE in l), -1)
        if idx == -1:
            print("❌ 未找到机箱目标行：{n:\"乔思伯 TK1 星舰仓\",p:499},")
            return
        
        # 从目标行的下一行开始，查找机箱数据行
        pos = idx + 1
        updated = 0
        
        # 遍历机箱数据行
        while pos < len(lines) and lines[pos].startswith(CASE_INDENT) and '{n:"' in lines[pos]:
            line = lines[pos]
            # 提取机箱名称
            match = re.search(r'{n:"([^"]+)"', line)
            if match:
                name = match.group(1)
                # 尝试匹配型号
                matched = False
                # 首先尝试完整名称匹配
                if name in case_map:
                    new_price = case_map[name]
                    lines[pos] = re.sub(r'p:\d+', f'p:{new_price}', line)
                    updated += 1
                    matched = True
                else:
                    # 尝试型号关键字匹配
                    for model in case_map:
                        if model in name:
                            new_price = case_map[model]
                            lines[pos] = re.sub(r'p:\d+', f'p:{new_price}', line)
                            updated += 1
                            matched = True
                            break
            pos += 1
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 机箱价格自动更新完成，共更新 {updated} 个型号")
    except Exception as e:
        print(f"❌ 机箱更新失败：{e}")

# 新增电源自动更新函数
def update_power_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 找到目标行（追风者 AMP GH850 850W 金牌全模组 ATX3.1 蟒纹线 白色）
        idx = next((i for i, l in enumerate(lines) if POWER_TARGET_LINE in l), -1)
        if idx == -1:
            print(f"❌ 未找到电源目标行：{POWER_TARGET_LINE}")
            return
        # 目标行的下一行开始插入
        pos = idx + 1
        # 先删除原有电源数据（避免重复）
        while pos < len(lines) and lines[pos].startswith(POWER_INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        # 插入新的电源数据
        power_content = generate_power_content(fetch_power_prices())
        if power_content:
            lines.insert(pos, power_content)
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("✅ 电源价格自动更新完成")
    except Exception as e:
        print(f"❌ 电源更新失败：{e}")

# 新增散热器自动更新函数
def update_cooler_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 爬取散热器数据，创建型号到价格的映射
        cooler_list = fetch_cooler_prices()
        cooler_map = {}
        for cooler in cooler_list:
            # 提取型号关键字，用于匹配
            name = cooler["name"]
            # 移除品牌名称，只保留型号部分
            for brand in COOLER_BRANDS:
                if brand in name:
                    model = name.replace(brand, "").strip()
                    # 创建映射，使用型号关键字作为键
                    cooler_map[model] = cooler["price"]
                    # 同时使用完整名称作为键，提高匹配成功率
                    cooler_map[name] = cooler["price"]
                    break
        
        # 找到散热器区域的开始位置
        idx = next((i for i, l in enumerate(lines) if COOLER_TARGET_LINE in l), -1)
        if idx == -1:
            print(f"❌ 未找到散热器目标行：{COOLER_TARGET_LINE}")
            return
        
        # 从目标行的下一行开始，查找散热器数据行
        pos = idx + 1
        updated = 0
        
        # 遍历散热器数据行
        while pos < len(lines) and lines[pos].startswith(COOLER_INDENT) and '{n:"' in lines[pos]:
            line = lines[pos]
            # 提取散热器名称
            match = re.search(r'{n:"([^"]+)"', line)
            if match:
                name = match.group(1)
                # 尝试匹配型号
                matched = False
                # 首先尝试完整名称匹配
                if name in cooler_map:
                    new_price = cooler_map[name]
                    lines[pos] = re.sub(r'p:\d+', f'p:{new_price}', line)
                    updated += 1
                    matched = True
                else:
                    # 尝试型号关键字匹配
                    for model in cooler_map:
                        if model in name:
                            new_price = cooler_map[model]
                            lines[pos] = re.sub(r'p:\d+', f'p:{new_price}', line)
                            updated += 1
                            matched = True
                            break
            pos += 1
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 散热器价格自动更新完成，共更新 {updated} 个型号")
    except Exception as e:
        print(f"❌ 散热器更新失败：{e}")

# -------------------------- CPU 加价逻辑 --------------------------
def fuzzy_match_price(name, price_dict):
    if not price_dict:
        return None
    
    # 特殊处理i5-14490F
    if "i5-14490F" in name or "i5 14490F" in name:
        # 查找i5-14400F的价格
        for key in price_dict:
            if "i514400" in key:
                p = float(price_dict[key])
                return str(int(p + 225))
    
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
    print("===== 硬件价格自动更新 =====")
    cpu_prices = fetch_latest_prices()
    if cpu_prices:
        update_html_prices(cpu_prices)
    # 使用新的显卡更新逻辑
    update_gpu_accurate()
    # 旧的固定显卡更新逻辑已不再需要，可以注释掉
    # update_fixed_gpu_prices()
    update_exist_ram_prices()
    update_ssd_prices()
    update_mb_accurate()
    update_ram_accurate()
    # 新增执行机箱更新
    update_case_accurate()
    # 新增执行电源更新
    update_power_accurate()
    # 新增执行散热器更新
    update_cooler_accurate()
    print("===== 全部执行完成 =====")
