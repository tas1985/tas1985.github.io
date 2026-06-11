import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项 --------------------------
SOURCE_URL = "http://0532.name/diy_pjhq?zd2=CPU"
GPU_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E5%86%85%E5%AD%98"
SSD_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E5%9B%BA%E6%80%81%E7%9B%98"
# 新增机箱URL配置
CASE_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E6%9C%BA%E7%AE%B1"
# 新增电源URL配置
POWER_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E7%94%B5%E6%BA%90"
# 新增散热器URL配置
COOLER_SOURCE_URL = "http://0532.name/diy_pjhq?zd2=%E6%95%A3%E7%83%AD%E5%99%A8"
HTML_FILE = "index.html"
START_LINE = 1055
END_LINE = 1110
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 配置
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
RAM_EXIST_START = '{n:"金百达_银爵 16G 3200(8*2)套装",'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（到手30天质保）",p:250},'
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
    # 清理特殊字符，但保留破折号以保持型号完整性
    cleaned = re.sub(r'[{n:"\",}]', '', name).strip()
    # 转换为小写，移除空格，但保留破折号
    name_clean = cleaned.lower().replace(" ", "")
    
    # 定义CPU型号模式
    patterns = [
        # Intel Core i系列
        r'i[3579]\-\d+[a-z0-9kf]*',
        r'i[3579]\d+[a-z0-9kf]*',
        # Intel Ultra系列
        r'ultra\s*\d+\s*[a-z]*',
        r'ultra\d+[a-z]*',
        # AMD Ryzen系列
        r'r[3579]\-\d+[a-z0-9x3d]*',
        r'r[3579]\d+[a-z0-9x3d]*',
        # AMD Threadripper
        r'tr\d+[a-z0-9]*'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name_clean)
        if match:
            result = match.group()
            # 如果结果不包含破折号，尝试从原始字符串中提取带破折号的版本
            if '-' not in result:
                dash_match = re.search(r'(i[3579])-(\d+)', cleaned, re.IGNORECASE)
                if dash_match:
                    result = dash_match.group(1) + '-' + dash_match.group(2)
            return result
    
    # 如果没有匹配到任何模式，返回清理后的名称
    return name_clean

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

# -------------------------- CPU 爬取函数 --------------------------
def fetch_cpu_prices():
    """爬取CPU价格，返回列表格式"""
    try:
        res = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        
        cpu_list = []
        
        # 尝试从表格中提取数据
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    price_text = cells[-1].get_text(strip=True)
                    price_match = re.search(r'￥?(\d+(?:\.\d+)?)', price_text)
                    if price_match and name and len(name) > 3:
                        price = int(float(price_match.group(1)))
                        cpu_list.append({"name": name, "price": price})
        
        # 如果表格提取失败，尝试使用正则从文本中提取
        if not cpu_list:
            text = soup.get_text()
            matches = re.findall(r'([^\n￥]+?)[：:\s]*[￥¥](\d+(?:\.\d+)?)', text)
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        cpu_list.append({"name": name.strip(), "price": int(float(price))})
                    except:
                        pass
        
        print(f"🔍 爬取到 {len(cpu_list)} 个 CPU 型号")
        if cpu_list:
            print("📋 部分CPU价格:")
            for i, cpu in enumerate(cpu_list[:8]):
                print(f"   {cpu['name']}: ￥{cpu['price']}")
        
        return cpu_list
    except Exception as e:
        print(f"❌ CPU爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

# -------------------------- CPU 内容生成函数 --------------------------
def generate_cpu_content(cpu_list):
    return "".join([f'{INDENT}{{n:"{c["name"]}",p:{c["price"]}}},\n' for c in cpu_list])

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
    """爬取显卡价格，返回列表格式"""
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        
        gpu_list = []
        
        # 方法1：尝试从表格中提取数据（最可靠）
        tables = soup.find_all('table')
        print(f"🔍 找到 {len(tables)} 个表格")
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    name = cells[0].get_text(strip=True)
                    price_text = cells[-1].get_text(strip=True)
                    price_match = re.search(r'￥?(\d+(?:\.\d+)?)', price_text)
                    if price_match and name and len(name) > 3:
                        price = int(float(price_match.group(1)))
                        # 白色显卡价格+100
                        if "白" in name:
                            price += 100
                        gpu_list.append({"name": name, "price": price})
        
        # 方法2：如果表格提取失败，尝试使用正则从文本中提取
        if not gpu_list:
            print("⚠️ 表格提取失败，尝试正则提取...")
            text = soup.get_text()
            # 使用更健壮的正则表达式匹配
            matches = re.findall(r'([^\n￥]+?)[：:\s]*[￥¥](\d+(?:\.\d+)?)', text)
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        price_val = int(float(price))
                        # 白色显卡价格+100
                        if "白" in name:
                            price_val += 100
                        gpu_list.append({"name": name.strip(), "price": price_val})
                    except:
                        pass
        
        print(f"📊 爬取到 {len(gpu_list)} 个显卡型号")
        if gpu_list:
            print("📋 部分显卡价格:")
            for i, gpu in enumerate(gpu_list[:8]):
                print(f"   {gpu['name'][:40]}...: ￥{gpu['price']}")
        
        return gpu_list
    except Exception as e:
        print(f"❌ 显卡爬取失败: {e}")
        import traceback
        traceback.print_exc()
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
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        
        # 查找所有产品名称标签
        product_names = soup.find_all('span', class_='product-name')
        
        for name_span in product_names:
            # 获取产品名称（优先使用 data-fullname 属性）
            name = name_span.get('data-fullname', '').strip()
            if not name:
                name = name_span.get_text(strip=True)
            
            # 查找紧邻的价格标签
            price_span = name_span.find_next_sibling('span', class_='product-price')
            if price_span:
                price_text = price_span.get_text(strip=True)
                price_match = re.search(r'￥(\d+(?:\.\d+)?)', price_text)
                if price_match:
                    price = price_match.group(1)
                    
                    # 排除列表中的品牌
                    if any(w in name for w in RAM_EXCLUDE_LIST):
                        continue
                    
                    # 阿斯加特品牌价格增加
                    final_p = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                    ram_list.append({"name": name, "price": final_p})
        
        print(f"🔍 爬取到 {len(ram_list)} 个内存型号")
        if ram_list:
            print("📋 部分内存价格:")
            for i, ram in enumerate(ram_list[:8]):
                print(f"   {ram['name'][:40]}...: ￥{ram['price']}")
            
            # 🔍 调试输出：显示所有弗雷相关的数据
            print("\n🔍 爬取到的所有弗雷相关内存:")
            for ram in ram_list:
                if "弗雷" in ram['name']:
                    print(f"   {ram['name']} -> ￥{ram['price']}")
            print()
        
        return ram_list
    except Exception as e:
        print(f"❌ 内存爬取失败: {e}")
        import traceback
        traceback.print_exc()
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

# -------------------------- CPU 更新函数 --------------------------
# 定义CPU目标行（插入位置的标记）
CPU_TARGET_LINE = '{n:"i3-12100F 3.3G 四核",p:599},'

def update_cpu_accurate():
    """CPU更新逻辑：保留现有型号，只更新价格，不删除"""
    try:
        # 先获取源网站的CPU数据
        cpu_list = fetch_cpu_prices()
        
        # 如果获取失败或为空，保留原有数据
        if not cpu_list:
            print("⚠️ CPU数据获取失败或为空，保留原有CPU数据")
            return
        
        # 将列表转换为字典，方便查找
        cpu_dict = {cpu["name"]: cpu["price"] for cpu in cpu_list}
        
        # 获取成功后打开文件进行更新
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 找到CPU目标行的位置
        idx = next((i for i, l in enumerate(lines) if CPU_TARGET_LINE in l), -1)
        if idx == -1:
            print(f"❌ 未找到CPU目标行：{CPU_TARGET_LINE}")
            return
        
        update_count = 0
        same_count = 0
        no_match_count = 0
        
        # 更新现有CPU型号的价格
        pos = idx + 1
        while pos < len(lines):
            line = lines[pos]
            if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                # 提取型号名称和当前价格
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    old_price = int(match.group(2))
                    
                    # 在源网站查找匹配的价格
                    if model_name in cpu_dict:
                        new_price = cpu_dict[model_name]
                        if new_price != old_price:
                            # 更新价格
                            new_line = re.sub(r'p:\d+', f'p:{new_price}', line)
                            lines[pos] = new_line
                            update_count += 1
                            print(f"  ✓ 更新价格: {model_name[:30]}... ￥{old_price} -> ￥{new_price}")
                        else:
                            same_count += 1
                            print(f"  ≡ 价格不变: {model_name[:30]}... ￥{old_price}")
                    else:
                        no_match_count += 1
                        print(f"  ⚠️ 未匹配: {model_name[:30]}...")
                pos += 1
            else:
                break
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"✅ CPU更新完成：更新 {update_count} 个，价格不变 {same_count} 个，未匹配 {no_match_count} 个")
    except Exception as e:
        print(f"❌ CPU更新失败：{e}")
        import traceback
        traceback.print_exc()

# -------------------------- 修改后的显卡更新逻辑 --------------------------
def update_gpu_accurate():
    """显卡更新逻辑：保留现有型号，只更新价格，不删除用户手动添加的型号"""
    try:
        print("\n=== 开始更新显卡数据 ===")
        # 先获取新的显卡数据，只有获取成功才进行更新
        gpu_list = fetch_gpu_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not gpu_list:
            print("⚠️ 显卡数据获取失败或为空，保留原有显卡数据")
            return
        
        # 将列表转换为字典，方便查找
        gpu_dict = {gpu["name"]: gpu["price"] for gpu in gpu_list}
        print(f"✅ 成功获取 {len(gpu_dict)} 个显卡数据")
        
        # 获取成功后再打开文件进行更新
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"📄 已读取 {len(lines)} 行 HTML 文件")
        
        # 找到GPU_START_MARK的位置
        start_idx = next((i for i, l in enumerate(lines) if GPU_START_MARK in l), -1)
        if start_idx == -1:
            print("❌ 未找到显卡自动更新区域开始标记")
            return
        print(f"📍 找到开始标记在第 {start_idx + 1} 行")
        
        # 从开始标记的下一行开始查找结束标记
        end_idx = next((i for i, l in enumerate(lines[start_idx + 1:], start_idx + 1) if GPU_END_MARK in l), -1)
        if end_idx == -1:
            print("❌ 未找到显卡自动更新区域结束标记")
            return
        print(f"📍 找到结束标记在第 {end_idx + 1} 行")
        
        update_count = 0
        same_count = 0
        no_match_count = 0
        
        # 更新现有显卡型号的价格（保留原有型号，只更新价格）
        pos = start_idx + 1
        while pos < end_idx:
            line = lines[pos]
            if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                # 提取型号名称和当前价格
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    old_price = int(match.group(2))
                    
                    # 在源网站查找匹配的价格
                    if model_name in gpu_dict:
                        new_price = gpu_dict[model_name]
                        if new_price != old_price:
                            # 更新价格
                            new_line = re.sub(r'p:\d+', f'p:{new_price}', line)
                            lines[pos] = new_line
                            update_count += 1
                            print(f"  ✓ 更新价格: {model_name[:40]}... ￥{old_price} -> ￥{new_price}")
                        else:
                            same_count += 1
                            print(f"  ≡ 价格不变: {model_name[:40]}... ￥{old_price}")
                    else:
                        no_match_count += 1
                        print(f"  ⚠️ 未匹配(保留): {model_name[:40]}...")
                pos += 1
            else:
                pos += 1
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"✅ 显卡价格自动更新完成：更新 {update_count} 个，价格不变 {same_count} 个，未匹配(保留) {no_match_count} 个")
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")
        import traceback
        traceback.print_exc()

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
        jbd_32g_3600_c18_final = 0  # 金百达_银爵 32G 3600(16*2)套装 海力士c18 的价格
        acer_pallasll_96g_6400_c32_final = 0  # 宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 的价格

        # ==================== 第一阶段：先收集所有参考价格 ====================
        print("🔄 第一阶段：收集参考价格")
        
        # 收集金百达_银爵 32G 3600(16*2)套装 海力士c18 的价格
        print(f"  🔍 收集: 金百达_银爵 32G 3600(16*2)套装 海力士c18")
        found_jbd_32g_3600 = False
        for ram_item in ram_list:
            # 调试输出：显示所有金百达银爵相关型号
            if "金百达" in ram_item['name'] and "银爵" in ram_item['name']:
                print(f"     候选: {ram_item['name']} -> {ram_item['price']}")
            if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "3600" in ram_item['name'] and ("16*2" in ram_item['name'] or "16x2" in ram_item['name']):
                jbd_32g_3600_c18_final = float(ram_item['price'])
                print(f"  ✓ 收集成功: 金百达_银爵 32G 3600(16*2)套装 海力士c18 = {int(jbd_32g_3600_c18_final)}")
                found_jbd_32g_3600 = True
                break
        if not found_jbd_32g_3600:
            print(f"  ⚠ 从爬取数据中未找到金百达_银爵 32G 3600(16*2)套装，将从HTML文件中读取当前价格")
        
        # 收集宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 的价格
        print(f"  🔍 收集: 宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32")
        for ram_item in ram_list:
            if "宏碁掠夺者" in ram_item['name'] and "Pallas" in ram_item['name'] and "96G" in ram_item['name'] and "6400" in ram_item['name'] and "C32" in ram_item['name']:
                acer_pallasll_96g_6400_c32_final = float(ram_item['price'])
                print(f"  ✓ 收集成功: 宏碁掠夺者 Pallasll 96G 6400 C32 = {int(acer_pallasll_96g_6400_c32_final)}")
                break
        
        # ==================== 第二阶段：进行价格更新 ====================
        print("🔄 第二阶段：更新内存价格")

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

            # 特殊处理：宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 凌霜马甲 黑/银
            if "宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 凌霜马甲 黑/银" in ram_name:
                print(f"  🔍 查找: 宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "宏碁掠夺者" in item_name and "Pallas" in item_name and "96G" in item_name and "6400" in item_name and "C32" in item_name:
                        final_price = float(ram_item['price'])
                        acer_pallasll_96g_6400_c32_final = final_price  # 保存价格供阿斯加特女武II使用
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特女武II RGB96G(48G*2)6400 D5 海M-C32 参考宏碁掠夺者 Pallasll 96G 6400 C32 的价格
            if "阿斯加特女武II RGB96G(48G*2)6400 D5 海M-C32" in ram_name:
                print(f"  🔍 查找: 参考宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 的价格")
                if acer_pallasll_96g_6400_c32_final > 0:
                    final_price = acer_pallasll_96g_6400_c32_final
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 宏碁掠夺者 Pallasll 96G 6400 C32 -> 价格 {int(final_price)}")
                else:
                    print(f"  ⚠ 宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜 参考宏碁掠夺者 Pallasll 96G 6400 C32 的价格
            if "宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜" in ram_name:
                print(f"  🔍 查找: 参考宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 的价格")
                if acer_pallasll_96g_6400_c32_final > 0:
                    final_price = acer_pallasll_96g_6400_c32_final
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 宏碁掠夺者 Pallasll 96G 6400 C32 -> 价格 {int(final_price)}")
                else:
                    print(f"  ⚠ 宏碁掠夺者 Pallasll 96G 6400 D5 48x2 C32 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特 DDR4 64G（32X2）3200 参考金百达_银爵 32G 3600(16*2)套装 海力士c18 的价格的2倍
            if "阿斯加特 DDR4 64G（32X2）3200" in ram_name:
                print(f"  🔍 查找: 阿斯加特 DDR4 64G（32X2）3200 = 金百达_银爵 32G 3600海力士c18 × 2")
                
                # 强制从HTML文件中查找金百达_银爵的价格作为参考
                ref_price = 0
                for j in range(start, end + 1):
                    if "金百达_银爵 32G 3600(16*2)套装 海力士c18" in lines[j]:
                        price_match = re.search(r'p:(\d+)', lines[j])
                        if price_match:
                            ref_price = float(price_match.group(1))
                            jbd_32g_3600_c18_final = ref_price
                            print(f"     从HTML获取参考价格: {int(ref_price)}")
                            break
                
                if ref_price > 0:
                    final_price = ref_price * 2
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 金百达_银爵 32G 3600海力士c18 × 2 = {int(final_price)}")
                else:
                    print(f"  ⚠ 金百达_银爵 32G 3600(16*2)套装 海力士c18 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：光威 天策 64G（32*2）3200 白色 参考金百达_银爵 32G 3600(16*2)套装 海力士c18 的价格的2倍
            if "光威 天策 64G（32*2）3200 白色" in ram_name:
                print(f"  🔍 查找: 光威 天策 64G（32*2）3200 白色 = 金百达_银爵 32G 3600海力士c18 × 2")
                
                # 强制从HTML文件中查找金百达_银爵的价格作为参考
                ref_price = 0
                for j in range(start, end + 1):
                    if "金百达_银爵 32G 3600(16*2)套装 海力士c18" in lines[j]:
                        price_match = re.search(r'p:(\d+)', lines[j])
                        if price_match:
                            ref_price = float(price_match.group(1))
                            jbd_32g_3600_c18_final = ref_price
                            print(f"     从HTML获取参考价格: {int(ref_price)}")
                            break
                
                if ref_price > 0:
                    final_price = ref_price * 2
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 金百达_银爵 32G 3600海力士c18 × 2 = {int(final_price)}")
                else:
                    print(f"  ⚠ 金百达_银爵 32G 3600(16*2)套装 海力士c18 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特 弗雷 16G 8*2 3200 参考 阿斯加特 弗雷 16G 8*2 3200 黑甲 的价格
            if "阿斯加特 弗雷 16G 8*2 3200" in ram_name and "黑甲" not in ram_name:
                print(f"  🔍 查找: 阿斯加特 弗雷 16G 8*2 3200 = 阿斯加特 弗雷 16G 8*2 3200 黑甲")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "阿斯加特" in item_name and "弗雷" in item_name and "16G" in item_name and "3200" in item_name and ("8x2" in item_name or "8*2" in item_name) and "黑甲" in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到阿斯加特 弗雷 16G 8*2 3200 黑甲，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特 弗雷 32G 16*2 3200 参考 阿斯加特 弗雷 32G 16*2 3200 黑甲 的价格
            if "阿斯加特 弗雷 32G 16*2 3200" in ram_name and "黑甲" not in ram_name:
                print(f"  🔍 查找: 阿斯加特 弗雷 32G 16*2 3200 = 阿斯加特 弗雷 32G 16*2 3200 黑甲")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "阿斯加特" in item_name and "弗雷" in item_name and "32G" in item_name and "3200" in item_name and ("16x2" in item_name or "16*2" in item_name) and "黑甲" in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到阿斯加特 弗雷 32G 16*2 3200 黑甲，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：金百达_银爵 16G 3200(8*2)套装 -> 金百达 银爵 16G 8x2 3200 D4 C16
            if "金百达_银爵 16G 3200(8*2)套装" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 16G 8x2 3200 D4 C16")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "金百达" in item_name and "银爵" in item_name and "16G" in item_name and "3200" in item_name and ("8x2" in item_name or "8*2" in item_name):
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到金百达 银爵 16G 8x2 3200 D4 C16，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：金百达_银爵 32G 3600(16*2)套装 海力士c18 -> 金百达 银爵 32G 16x2 3600 D4 C18
            if "金百达_银爵 32G 3600(16*2)套装 海力士c18" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 32G 16x2 3600 D4 C18")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "金百达" in item_name and "银爵" in item_name and "32G" in item_name and "3600" in item_name and ("16x2" in item_name or "16*2" in item_name):
                        final_price = float(ram_item['price'])
                        jbd_32g_3600_c18_final = final_price  # 保存价格供其他型号参考
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到金百达 银爵 32G 16x2 3600 D4 C18，跳过更新")
                    special_handled = True
                continue

            if "金百达_星刃 32G 6000 c28 海力士A-die 灯条" in ram_name:
                print(f"  🔍 查找: 宏碁掠夺者 冰刃 32G 6000D5 16*2 C28 RGB 黑/白")
                found = False
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "宏碁掠夺者" in item_name and "冰刃" in item_name and "6000" in item_name and "C28" in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                if not found:
                    print(f"  ⚠ 未找到宏碁掠夺者 冰刃 6000 C28，跳过更新")
                    special_handled = True
                continue

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
                print(f"  🔍 查找: 金百达 银爵 16G 6000 D5 C36 单根 (需×2)")
                for ram_item in ram_list:
                    if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "6000" in ram_item['name'] and "C36" in ram_item['name']:
                        # 源网站是16G单根价格，需要乘以2得到32G套装价格
                        final_price = float(ram_item['price']) * 2
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {ram_item['name']} × 2 -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到金百达 银爵 16G 6000 D5 C36 单根，跳过更新")
                    special_handled = True
            elif "金百达_银爵 16G 6000单根 c30 m-die" in ram_name:
                print(f"  🔍 查找: 金百达 银爵 16G 6000 D5 C30 单根")
                for ram_item in ram_list:
                    if "金百达" in ram_item['name'] and "银爵" in ram_item['name'] and "6000" in ram_item['name'] and "C30" in ram_item['name']:
                        # 源网站已经是16G单根价格，不需要除以0.5
                        final_price = float(ram_item['price'])
                        special_handled = True
                        print(f"  ★ 匹配成功: {ram_name} -> {ram_item['name']} -> 价格 {int(final_price)}")
                        break
                if not special_handled:
                    print(f"  ⚠ 未找到金百达 银爵 16G 6000 D5 C30 单根，跳过更新")
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
                    elif "金百达_银爵 32G 3200(16*2)套装" in ram_name:
                        jbd_32g_3200_final = base_price
                    elif "金百达_银爵 32G 3600(16*2)套装 海力士c18" in ram_name:
                        jbd_32g_3600_c18_final = base_price  # 保存金百达_银爵 32G 3600海力士c18的价格
                    elif "宏碁掠夺者" in ram_name:
                        final_price = base_price + 300
                    elif "阿斯加特" in ram_name and "女武神" not in ram_name:
                        final_price = base_price + 50

                    if final_price is not None:
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
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        all_items = []
        
        # 查找所有产品名称标签
        product_names = soup.find_all('span', class_='product-name')
        
        for name_span in product_names:
            # 获取产品名称（优先使用 data-fullname 属性）
            name = name_span.get('data-fullname', '').strip()
            if not name:
                name = name_span.get_text(strip=True)
            
            # 查找紧邻的价格标签
            price_span = name_span.find_next_sibling('span', class_='product-price')
            if price_span:
                price_text = price_span.get_text(strip=True)
                price_match = re.search(r'￥(\d+(?:\.\d+)?)', price_text)
                if price_match:
                    price = price_match.group(1)
                    all_items.append((name, price))
                    
                    # 提取四要素
                    brand, series, cas, capacity, freq = extract_ram_four_key(name)
                    if brand or series or cas or capacity or freq:
                        ram_list.append({
                            'name': name,
                            'key': (brand, series, cas, capacity, freq),
                            'price': price
                        })
        
        print(f"\n📋 网站内存数据 (共{len(all_items)}个):")
        for n, p in all_items[:30]:
            print(f"   {n} -> {p}")
        if len(all_items) > 30:
            print(f"   ... 还有 {len(all_items)-30} 个")
        return ram_list
    except Exception as e:
        print(f"❌ 获取内存数据失败：{e}")
        import traceback
        traceback.print_exc()
        return []

# -------------------------- 主板/内存 自动更新 --------------------------
def update_mb_accurate():
    try:
        # 先获取新的主板数据，只有获取成功才进行更新
        mb_list = fetch_mb_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not mb_list:
            print("⚠️ 主板数据获取失败或为空，保留原有主板数据")
            return
        
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        idx = next((i for i, l in enumerate(lines) if MB_TARGET_LINE in l), -1)
        if idx == -1:
            return
        pos = idx + 1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]:
            del lines[pos]
        lines.insert(pos, generate_mb_content(mb_list))
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 主板价格自动更新完成，共更新 {len(mb_list)} 个主板型号")
    except Exception as e:
        print(f"❌ 主板更新失败：{e}")

def update_ram_accurate():
    """内存更新逻辑：保留现有型号，只更新价格，不删除，新型号追加"""
    try:
        # 先获取源网站的内存数据
        ram_list = fetch_processed_ram()
        
        # 如果获取失败或为空，保留原有数据
        if not ram_list:
            print("⚠️ 内存数据获取失败或为空，保留原有内存数据")
            return
        
        # 将列表转换为字典，方便查找
        ram_dict = {ram["name"]: ram["price"] for ram in ram_list}
        
        # 获取成功后打开文件进行更新
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 找到内存目标行的位置
        idx = next((i for i, l in enumerate(lines) if RAM_INSERT_TARGET in l), -1)
        if idx == -1:
            print(f"❌ 未找到内存目标行：{RAM_INSERT_TARGET}")
            return
        
        # 🔍 找到内存区域的开始位置（ram: [之后）
        ram_start_idx = -1
        for i in range(idx - 1, max(0, idx - 100), -1):  # 向前最多查找 100 行
            if 'ram: [' in lines[i]:
                ram_start_idx = i
                break
        
        if ram_start_idx == -1:
            print("⚠️ 未找到内存区域开始位置，使用目标行作为参考")
            ram_start_idx = idx
        
        update_count = 0
        same_count = 0
        no_match_count = 0
        
        # 更新现有内存型号的价格
        # 首先查找金百达_银爵 32G 3600(16*2)套装 海力士 c18 的价格
        ref_price = 0
        pos = ram_start_idx + 1  # 从内存区域开始位置查找
        while pos < len(lines):
            line = lines[pos]
            if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    if "金百达_银爵 32G 3600(16*2)套装 海力士 c18" in model_name:
                        ref_price = int(match.group(2))
                        print(f"  🔍 找到参考型号：{model_name[:40]}... 价格￥{ref_price}")
                        break
                pos += 1
            else:
                break
        
        # 如果在 HTML 中没找到参考价格，从爬取数据中查找
        if ref_price <= 0:
            for ram in ram_list:
                if "金百达" in ram["name"] and "银爵" in ram["name"] and "3600" in ram["name"] and ("16*2" in ram["name"] or "16x2" in ram["name"]):
                    ref_price = int(ram["price"])
                    print(f"  🔍 从爬取数据找到参考价格：{ram['name'][:40]}... 价格￥{ref_price}")
                    break
        
        # 更新内存型号 - 从内存区域开始位置到目标行之后
        pos = ram_start_idx + 1
        
        # 🔍 调试：输出所有爬取到的阿斯加特弗雷相关数据
        print("\n🔍 爬取到的阿斯加特弗雷相关数据:")
        for ram in ram_list:
            if "弗雷" in ram["name"]:
                print(f"   {ram['name']} -> ￥{ram['price']}")
        print()
        
        # 💾 预先查找弗雷内存的价格（用于同时更新带黑甲和不带黑甲的型号）
        fei_le_16g_price = None
        fei_le_32g_price = None
        for ram in ram_list:
            ram_name = ram["name"]
            # 查找 16G 弗雷价格（优先匹配不带黑甲的，如果没有则用黑甲的）
            if fei_le_16g_price is None and "阿斯加特" in ram_name and "弗雷" in ram_name and "16G" in ram_name and "3200" in ram_name and ("8x2" in ram_name or "8*2" in ram_name):
                fei_le_16g_price = ram["price"]
                print(f"💾 找到弗雷 16G 价格：{ram_name} -> ￥{fei_le_16g_price}")
            # 查找 32G 弗雷价格（优先匹配不带黑甲的，如果没有则用黑甲的）
            if fei_le_32g_price is None and "阿斯加特" in ram_name and "弗雷" in ram_name and "32G" in ram_name and "3200" in ram_name and ("16x2" in ram_name or "16*2" in ram_name):
                fei_le_32g_price = ram["price"]
                print(f"💾 找到弗雷 32G 价格：{ram_name} -> ￥{fei_le_32g_price}")
        
        while pos < len(lines):
            line = lines[pos]
            if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                # 提取型号名称和当前价格
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    old_price = int(match.group(2))
                    new_price = None
                    
                    # 特殊处理：阿斯加特 DDR4 64G（32X2）3200 = 金百达_银爵 32G 3600(16*2)套装 × 2
                    if "阿斯加特 DDR4 64G（32X2）3200" in model_name:
                        print(f"  🔍 匹配到阿斯加特 DDR4 64G，尝试从HTML获取参考价格")
                        # 强制从HTML文件中查找金百达_银爵的价格
                        ref_price_from_html = 0
                        temp_pos = idx + 1
                        while temp_pos < len(lines):
                            temp_line = lines[temp_pos]
                            if '{n:"' in temp_line and '",p:' in temp_line:
                                temp_match = re.search(r'{n:"([^"]+)",p:(\d+)}', temp_line)
                                if temp_match:
                                    temp_name = temp_match.group(1)
                                    if "金百达_银爵 32G 3600(16*2)套装 海力士c18" in temp_name:
                                        ref_price_from_html = int(temp_match.group(2))
                                        print(f"     从HTML获取参考价格: 金百达_银爵 32G 3600(16*2)套装 海力士c18 = ￥{ref_price_from_html}")
                                        break
                            temp_pos += 1
                        
                        if ref_price_from_html > 0:
                            new_price = str(ref_price_from_html * 2)
                            print(f"  ★ 特殊更新：阿斯加特 DDR4 64G = 金百达_银爵(￥{ref_price_from_html}) × 2 = ￥{new_price}")
                        else:
                            print(f"  ⚠️ 阿斯加特 DDR4 64G 缺少参考价格，跳过更新")
                    # 特殊处理：光威 天策 64G（32*2）3200 白色 = 金百达_银爵 32G 3600(16*2)套装 × 2
                    elif "光威 天策 64G（32*2）3200 白色" in model_name:
                        print(f"  🔍 匹配到光威 天策 64G 白色，尝试从HTML获取参考价格")
                        # 强制从HTML文件中查找金百达_银爵的价格
                        ref_price_from_html = 0
                        temp_pos = idx + 1
                        while temp_pos < len(lines):
                            temp_line = lines[temp_pos]
                            if '{n:"' in temp_line and '",p:' in temp_line:
                                temp_match = re.search(r'{n:"([^"]+)",p:(\d+)}', temp_line)
                                if temp_match:
                                    temp_name = temp_match.group(1)
                                    if "金百达_银爵 32G 3600(16*2)套装 海力士c18" in temp_name:
                                        ref_price_from_html = int(temp_match.group(2))
                                        print(f"     从HTML获取参考价格: 金百达_银爵 32G 3600(16*2)套装 海力士c18 = ￥{ref_price_from_html}")
                                        break
                            temp_pos += 1
                        
                        if ref_price_from_html > 0:
                            new_price = str(ref_price_from_html * 2)
                            print(f"  ★ 特殊更新：光威 天策 64G 白色 = 金百达_银爵(￥{ref_price_from_html}) × 2 = ￥{new_price}")
                        else:
                            print(f"  ⚠️ 光威 天策 64G 白色 缺少参考价格，跳过更新")
                    # 特殊处理：阿斯加特 弗雷 16G 8*2 3200（不区分是否黑甲）使用爬取到的弗雷 16G 价格
                    elif "阿斯加特 弗雷 16G 8*2 3200" in model_name:
                        if fei_le_16g_price is not None:
                            new_price = str(fei_le_16g_price)
                            print(f"  ★ 特殊更新：阿斯加特 弗雷 16G 8*2 3200 = 爬取的弗雷 16G 价格 -> ￥{new_price}")
                        else:
                            print(f"  ⚠️ 未找到阿斯加特 弗雷 16G 8*2 3200 的爬取价格，跳过更新")
                    # 特殊处理：阿斯加特 弗雷 32G 16*2 3200（不区分是否黑甲）使用爬取到的弗雷 32G 价格
                    elif "阿斯加特 弗雷 32G 16*2 3200" in model_name:
                        if fei_le_32g_price is not None:
                            new_price = str(fei_le_32g_price)
                            print(f"  ★ 特殊更新：阿斯加特 弗雷 32G 16*2 3200 = 爬取的弗雷 32G 价格 -> ￥{new_price}")
                        else:
                            print(f"  ⚠️ 未找到阿斯加特 弗雷 32G 16*2 3200 的爬取价格，跳过更新")
                    # 正常更新逻辑
                    elif model_name in ram_dict:
                        new_price = ram_dict[model_name]
                        if new_price != old_price:
                            print(f"  ✓ 更新价格：{model_name[:30]}... ￥{old_price} -> ￥{new_price}")
                        else:
                            same_count += 1
                            print(f"  ≡ 价格不变：{model_name[:30]}... ￥{old_price}")
                    else:
                        no_match_count += 1
                        print(f"  ⚠️ 未匹配：{model_name[:30]}...")
                    
                    # 更新价格
                    if new_price and new_price != str(old_price):
                        new_line = re.sub(r'p:\d+', f'p:{new_price}', line)
                        lines[pos] = new_line
                        update_count += 1
                pos += 1
            else:
                break
        
        # 收集现有型号名称
        existing_names = set()
        pos = idx + 1
        while pos < len(lines):
            line = lines[pos]
            if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                match = re.search(r'{n:"([^"]+)",p:\d+}', line)
                if match:
                    existing_names.add(match.group(1))
                pos += 1
            else:
                break
        
        # 准备新型号数据（只添加不在现有列表中的型号）
        new_ram_lines = []
        for ram in ram_list:
            if ram["name"] not in existing_names:
                new_ram_lines.append(f'{INDENT}{{n:"{ram["name"]}",p:{ram["price"]}}},\n')
        
        # 在现有型号后插入新型号
        if new_ram_lines:
            insert_pos = idx + 1
            # 找到现有型号的最后一行
            while insert_pos < len(lines):
                line = lines[insert_pos]
                if line.startswith(INDENT) and '{n:"' in line and '",p:' in line:
                    insert_pos += 1
                else:
                    break
            
            # 插入新型号
            for i, new_line in enumerate(new_ram_lines):
                lines.insert(insert_pos + i, new_line)
            print(f"  ➕ 新增 {len(new_ram_lines)} 个内存型号")
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"✅ 内存更新完成：更新 {update_count} 个，价格不变 {same_count} 个，未匹配 {no_match_count} 个")
    except Exception as e:
        print(f"❌ 内存更新失败：{e}")
        import traceback
        traceback.print_exc()

# 新增机箱自动更新函数
def update_case_accurate():
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 爬取机箱数据，创建型号到价格的映射
        case_list = fetch_case_prices()
        # 只使用完整名称进行精确匹配，避免错误匹配
        case_map = {case["name"]: case["price"] for case in case_list}
        
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
                # 只使用完整名称精确匹配
                if name in case_map:
                    new_price = case_map[name]
                    lines[pos] = re.sub(r'p:\d+', f'p:{new_price}', line)
                    updated += 1
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
        # 先获取新的电源数据，只有获取成功才进行更新
        power_list = fetch_power_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not power_list:
            print("⚠️ 电源数据获取失败或为空，保留原有电源数据")
            return
        
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
        power_content = generate_power_content(power_list)
        if power_content:
            lines.insert(pos, power_content)
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ 电源价格自动更新完成，共更新 {len(power_list)} 个电源型号")
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

# -------------------------- CPU 核心型号提取函数 --------------------------
def extract_cpu_key(text):
    """提取CPU核心型号关键字，核心识别要点：数字+英文后缀如12400F、5600X、5500X3D
    例如: "i5-12400F 散" -> "i512400f", "锐龙 R5-5500X3D" -> "r55500x3d"
    """
    if not text:
        return None
    text_lower = text.lower().replace(" ", "").replace("-", "")
    
    # Intel型号: i3/i5/i7/i9 + 4-5位数字 + 可选后缀(F/K/KF等)
    intel_pattern = r'i([3579])(\d{4,5})([a-z0-9]*)'
    intel_match = re.search(intel_pattern, text_lower)
    if intel_match:
        result = f"i{intel_match.group(1)}{intel_match.group(2)}{intel_match.group(3)}"
        return result
    
    # AMD型号: r3/r5/r7/r9 + 4位数字 + 可选后缀(X/X3D等)
    amd_pattern = r'r([3579])(\d{4})([a-z0-9x3d]*)'
    amd_match = re.search(amd_pattern, text_lower)
    if amd_match:
        result = f"r{amd_match.group(1)}{amd_match.group(2)}{amd_match.group(3)}"
        return result
    
    # Intel Ultra型号
    ultra_match = re.search(r'ultra(\d+)', text_lower)
    if ultra_match:
        return f"ultra{ultra_match.group(1)}"
    
    return None

# -------------------------- CPU 匹配逻辑 --------------------------
def fuzzy_match_price(name, price_dict):
    """匹配CPU价格：通过核心型号关键字进行匹配"""
    if not price_dict:
        return None
    
    # 提取HTML中的CPU核心型号
    html_key = extract_cpu_key(name)
    if not html_key:
        print(f"  ⚠️ 无法提取CPU核心型号：{name[:35]}")
        return None
    
    print(f"  📌 HTML型号: {name[:40]}...")
    print(f"  🔑 提取关键字: {html_key}")
    
    # 判断是否需要散片
    is_retail = "散" in name
    
    # 遍历源网站价格字典
    for source_name, price in price_dict.items():
        # 提取源网站中的CPU核心型号
        source_key = extract_cpu_key(source_name)
        if not source_key:
            continue
        
        # 调试输出：显示正在比较的关键字
        if html_key[:2] == source_key[:2]:  # 同系列(i5/r5等)才显示
            print(f"     ↔ 比较: {source_key} vs {html_key} ({source_name[:30]}...)")
        
        # 核心型号必须完全匹配
        if html_key != source_key:
            continue
        
        # 散片/盒装匹配
        source_has_retail = "散" in source_name.lower()
        source_has_box = "盒" in source_name.lower()
        
        # 如果HTML要求散片，但源网站是盒装，跳过
        if is_retail and source_has_box and not source_has_retail:
            print(f"     ✗ 跳过: 需要散片，但源网站是盒装")
            continue
        # 如果HTML要求盒装，但源网站是散片，跳过
        if not is_retail and source_has_retail and not source_has_box:
            print(f"     ✗ 跳过: 需要盒装，但源网站是散片")
            continue
        
        # 找到匹配！
        result = str(int(float(price)))
        print(f"  ✓ 匹配成功: {name[:35]}... -> {source_name} -> ￥{result}")
        return result
    
    print(f"  ❌ 未匹配到: {name[:35]}... (关键字: {html_key})")
    return None

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 硬件价格自动更新 =====")
    # 使用新的CPU更新逻辑
    update_cpu_accurate()
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
