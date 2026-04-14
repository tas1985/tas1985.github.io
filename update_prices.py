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
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
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
    """
    修正显卡精确匹配逻辑，综合品牌+型号+数字+显存+品阶中文的逻辑来匹配
    """
    name = name.strip()
    # 提取品牌
    brand_match = re.search(r"(七彩虹|微星|英伟达|NVIDIA|华硕|技嘉|影驰|索泰|耕升|蓝戟|Intel|AMD)", name)
    brand = brand_match.group(1) if brand_match else ""
    
    # 提取GPU系列和型号，比如RTX3060、RTX4070、RX6700等
    series_match = re.search(r"((RTX|GTX|Radeon\s+RX|RX)\s*\d+[A-Z]*\d*)", name, re.IGNORECASE)
    series = series_match.group(1).replace(" ", "") if series_match else ""
    
    # 提取显存容量，如12G、8G、16G
    vram_match = re.search(r"(\d+G[B]?)", name)
    vram = vram_match.group(1) if vram_match else ""
    
    # 提取品阶关键词，如战斧、万图师、超龙、豪华版、OC、白、黑、金、银等
    grade_keywords = re.findall(r"(战斧|万图师|超龙|豪华版|OC|白|黑|金|银|Pro|Ti|Super|Ultra|Advanced|Index|Arc)", name)
    grades = "".join(grade_keywords)
    
    # 组合为唯一标识
    key_parts = [brand, series, vram, grades]
    # 过滤空字符串并连接
    key = "|".join([part for part in key_parts if part])
    return key

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
            price = int(float(p))
            # 🔥 新增规则：名称含「白」→ 价格 +100
            if "白" in n:
                price += 100
            gpu_map[k] = price
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

# -------------------------- 生成格式函数 --------------------------
def generate_gpu_content(gpu_list):
    return "".join([f"{GPU_START_MARK}\n", *[f'{INDENT}{{n:"{g["name"]}",p:{g["price"]}}},\n' for g in gpu_list], f"{GPU_END_MARK}\n"])

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
            "三星 990 PRO 1T PCIE 4.0 读7400写6900",
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
                    lines[i] = re.sub(r'p:\d+', f'p:{nv7400_1t_price}', line)
                    updated += 1
                    continue

            for ssd_name in target_ssd:
                if ssd_name in line:
                    key = extract_ssd_exact_key(ssd_name)
                    if key in ssd_map:
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

        print(f"✅ 固态硬盘更新完成")
        print(f"🧮 佰维 NV7400 2T 价格 = {nv7400_2t_price}")
        print(f"🧮 佰维 NV7400 1T 价格 = {nv7400_1t_price} (2T × 0.53)")
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
            if not re.search(r'p:\d+', line):
                continue
            for gpu_name in target_gpus:
                if gpu_name in line:
                    key = extract_gpu_exact_key(gpu_name)
                    if key in gpu_map:
                        price = gpu_map[key]
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
        # 找到目标行（乔思伯 TK1 星舰仓）
        idx = next((i for i, l in enumerate(lines) if CASE_TARGET_LINE in l), -1)
        if idx == -1:
            print("❌ 未找到机箱目标行：{n:\"乔思伯 TK1 星舰仓\",p:499},")
            return
        # 目标行的下一行开始插入
        pos = idx + 1
        # 先删除原有机箱数据（避免重复）
        while pos < len(lines) and lines[pos].startswith(CASE_INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        # 插入新的机箱数据
        case_content = generate_case_content(fetch_case_prices())
        if case_content:
            lines.insert(pos, case_content)
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("✅ 机箱价格自动更新完成")
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
    print("===== 硬件价格自动更新 =====")
    cpu_prices = fetch_latest_prices()
    if cpu_prices:
        update_html_prices(cpu_prices)
    update_fixed_gpu_prices()
    update_exist_ram_prices()
    update_ssd_prices()
    update_mb_accurate()
    update_ram_accurate()
    # 新增执行机箱更新
    update_case_accurate()
    # 新增执行电源更新
    update_power_accurate()
    print("===== 全部执行完成 =====")
