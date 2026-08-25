import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 浏览器支持（可选）--------------------------
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("ℹ️ Playwright not installed, using requests for page fetching.")

_browser = None

def get_browser():
    global _browser
    if _browser is None and PLAYWRIGHT_AVAILABLE:
        try:
            playwright = sync_playwright().start()
            _browser = playwright.chromium.launch(headless=True)
        except Exception:
            pass
    return _browser

def fetch_page_content(url):
    if PLAYWRIGHT_AVAILABLE:
        browser = get_browser()
        if browser:
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)
                for _ in range(3):
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(1000)
                content = page.inner_text('body')
                page.close()
                return content
            except Exception as e:
                print(f"⚠️ 浏览器获取内容失败，回退到requests: {e}")
                pass
    res = requests.get(url, headers=HEADERS, timeout=15)
    res.encoding = 'utf-8'
    return res.text

# -------------------------- 全局配置项 --------------------------
SOURCE_URL = "https://0532.name/diy_pjhq?zd2=CPU"
GPU_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E5%86%85%E5%AD%98"
SSD_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E5%9B%BA%E6%80%81%E7%9B%98"
# 新增机箱URL配置
CASE_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E6%9C%BA%E7%AE%B1"
# 新增电源URL配置
POWER_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E7%94%B5%E6%BA%90"
# 新增散热器URL配置
COOLER_SOURCE_URL = "https://0532.name/diy_pjhq?zd2=%E6%95%A3%E7%83%AD%E5%99%A8"
HTML_FILE = "index.html"
START_LINE = 1055
END_LINE = 1110
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def is_garbled(text):
    """检测文本是否为乱码（包含不应出现在中文产品名中的西里尔/异常字符）"""
    for ch in text:
        cp = ord(ch)
        # 西里尔字母范围（俄语等），正常中文产品名不应包含
        if 0x0400 <= cp <= 0x04FF:
            return True
        # 制表符/方块绘制字符
        if 0x2500 <= cp <= 0x259F:
            return True
    return False

# 配置
GPU_START_MARK = "<!-- 显卡自动更新区域 开始 -->"
GPU_END_MARK = "<!-- 显卡自动更新区域 结束 -->"
MB_TARGET_LINE = '{n:"华硕 ROG STRIX B760-G GAMING WIFI D4 小吹雪",p:1289},'
MB_EXCLUDE = "铭瑄"
RAM_EXIST_START = '{n:"金百达 银爵 16G 8x2 3200'
RAM_EXIST_END = '{n:"宏碁掠夺者 96G(48G×2)套 DDR5 6000凌霜",'
RAM_INSERT_TARGET = '{n:"三星 DDR3 16G（拆机内存到手30天质保）",p:249},'
RAM_EXCLUDE_LIST = ["科摩思", "现代", "梵想"]
RAM_ASC_TECH_ADD = 0
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
    brand = re.search(r"(七彩虹|微星|华硕|技嘉|影驰|蓝宝石|蓝戟|索泰|映众|双敏|盈通|撼讯|旌宇|磐正|磐镭|电竞判客|英伟达|丽台|ELSA|PNY|耕升|翔升|铭瑄|梅捷)", name)
    model = re.search(r"(RTX\d+TI|RTX\d+|RX\d+XT|RX\d+GRE|RX\d+|ARC\d+|GTX\d+|GT\d+|QUADRO)", name)
    vram = extract_gpu_vram(name)
    series = re.search(r"(战斧|ULTRA|万图师|ADVANCED|银鲨|DUO|VENTUS|GAMING|TRIO|VULCAN|PHOTON|INDEX|脉动|氮动|极地|金属大师|星曜|圣刃|魔刃|FIRE|ATS|DUAL|TUF|ROG|AORUS|EAGLE|AERO|雪鹰|猎鹰|魔鹰|小雕|超级雕|幻影师|月影|星夜|开天|毁灭者|IGAME|GEFORCE|曜夜|红魔龙|暗黑犬|游骑兵|暗黑黑)", name)
    key_parts = []
    if brand: key_parts.append(brand.group(1))
    if model: key_parts.append(model.group(1))
    if vram: key_parts.append(vram)
    if series: key_parts.append(series.group(1))
    return "|".join(key_parts)

def match_core_keywords(name1, name2):
    name1_clean = name1.strip().replace(" ", "").upper()
    name2_clean = name2.strip().replace(" ", "").upper()
    
    brand_pattern = r"(七彩虹|微星|华硕|技嘉|影驰|蓝宝石|蓝戟|索泰|映众|双敏|盈通|撼讯|旌宇|磐正|磐镭|电竞判客|英伟达|丽台|ELSA|PNY|耕升|翔升|铭瑄|梅捷)"
    model_pattern = r"(RTX\d+TI|RTX\d+|RX\d+XT|RX\d+GRE|RX\d+|ARC\d+|GTX\d+|GT\d+|QUADRO)"
    series_pattern = r"(战斧|ULTRA|万图师|ADVANCED|银鲨|DUO|VENTUS|GAMING|TRIO|VULCAN|PHOTON|INDEX|脉动|氮动|极地|金属大师|星曜|圣刃|魔刃|FIRE|ATS|DUAL|TUF|ROG|AORUS|EAGLE|AERO|雪鹰|猎鹰|魔鹰|小雕|超级雕|幻影师|月影|星夜|开天|毁灭者|IGAME|GEFORCE|曜夜|红魔龙|暗黑犬|游骑兵|暗黑黑)"
    
    brand1 = re.search(brand_pattern, name1_clean)
    brand2 = re.search(brand_pattern, name2_clean)
    model1 = re.search(model_pattern, name1_clean)
    model2 = re.search(model_pattern, name2_clean)
    vram1 = extract_gpu_vram(name1)
    vram2 = extract_gpu_vram(name2)
    series1 = re.search(series_pattern, name1_clean)
    series2 = re.search(series_pattern, name2_clean)
    
    if not (brand1 and brand2 and model1 and model2 and vram1 and vram2):
        return False
    
    if brand1.group(1) != brand2.group(1):
        return False
    
    if model1.group(1) != model2.group(1):
        return False
    
    if vram1 != vram2:
        return False
    
    if series1 and series2:
        if series1.group(1) != series2.group(1):
            return False
    
    return True

def extract_gpu_vram(name):
    name_clean = name.strip().replace(" ", "").upper()
    vram_patterns = [
        r"(\d+)GB",
        r"(\d+)G",
        r"O(\d+)G",
    ]
    for pat in vram_patterns:
        m = re.search(pat, name_clean)
        if m:
            return f"{m.group(1)}G"
    return ""

def extract_gpu_chip_key(name):
    name = name.strip().replace(" ", "").upper()
    model = re.search(r"(RTX\d+TI|RTX\d+|RX\d+XT|RX\d+GRE|RX\d+|ARC\d+|GTX\d+|GT\d+|QUADRO)", name)
    vram = extract_gpu_vram(name)
    if model and vram:
        return f"{model.group(1)}|{vram}"
    if model:
        return model.group(1)
    return ""

# -------------------------- 内存关键字提取与匹配函数 --------------------------
def extract_ram_exact_key(name):
    name = name.strip().replace(" ", "").upper()
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光|佰维|雷克沙|金邦)"
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|弗雷|雷神|海拉|海姆达尔|幻光戟|博拉琪|TUF|天策|冰刃|Pallas|炫光星舰|影锋|HT200|巨蟹)"
    cas_pattern = r"(C\d+)"
    
    brand = re.search(brand_pattern, name)
    series = re.search(series_pattern, name)
    cas = re.search(cas_pattern, name)
    capacity = re.search(r"(\d+)G", name)
    freq = re.search(r"(\d{4,5})", name)
    
    key_parts = []
    if brand: key_parts.append(brand.group(1))
    if series: key_parts.append(series.group(1))
    if capacity: key_parts.append(f"{capacity.group(1)}G")
    if freq: key_parts.append(freq.group(1))
    if cas: key_parts.append(cas.group(1))
    
    return "|".join(key_parts)

def extract_ram_freq(name):
    name_clean = name.strip().replace(" ", "").upper()
    freq_match = re.search(r"(\d{4,5})", name_clean)
    if freq_match:
        return freq_match.group(1)
    return ""

def extract_ram_capacity(name):
    name_clean = name.strip().replace(" ", "").upper()
    cap_match = re.search(r"(\d+)G", name_clean)
    if cap_match:
        return f"{cap_match.group(1)}G"
    return ""

def extract_ram_cas(name):
    name_clean = name.strip().replace(" ", "").upper()
    cas_match = re.search(r"(C\d+)", name_clean)
    if cas_match:
        return cas_match.group(1)
    return ""

def extract_ram_brand(name):
    name_clean = name.strip().replace(" ", "").upper()
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光|佰维|雷克沙|金邦)"
    brand = re.search(brand_pattern, name_clean)
    if brand:
        return brand.group(1)
    return ""

def extract_ram_series(name):
    name_clean = name.strip().replace(" ", "").upper()
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|弗雷|雷神|海拉|海姆达尔|幻光戟|博拉琪|TUF|天策|冰刃|Pallas|炫光星舰|影锋|HT200|巨蟹)"
    series = re.search(series_pattern, name_clean)
    if series:
        return series.group(1)
    return ""

def match_ram_core_keywords(name1, name2):
    name1_clean = name1.strip().replace(" ", "").upper()
    name2_clean = name2.strip().replace(" ", "").upper()
    
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光|佰维|雷克沙|金邦)"
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|弗雷|雷神|海拉|海姆达尔|幻光戟|博拉琪|TUF|天策|冰刃|Pallas|炫光星舰|影锋|HT200|巨蟹)"
    
    brand1 = re.search(brand_pattern, name1_clean)
    brand2 = re.search(brand_pattern, name2_clean)
    series1 = re.search(series_pattern, name1_clean)
    series2 = re.search(series_pattern, name2_clean)
    cap1 = extract_ram_capacity(name1)
    cap2 = extract_ram_capacity(name2)
    freq1 = extract_ram_freq(name1)
    freq2 = extract_ram_freq(name2)
    cas1 = extract_ram_cas(name1)
    cas2 = extract_ram_cas(name2)
    
    if not (brand1 and brand2):
        return False
    
    if brand1.group(1) != brand2.group(1):
        return False
    
    if cap1 and cap2 and cap1 != cap2:
        return False
    
    if freq1 and freq2 and freq1 != freq2:
        return False
    
    if cas1 and cas2 and cas1 != cas2:
        return False
    
    if series1 and series2 and series1.group(1) != series2.group(1):
        return False
    
    return True

def find_chip_reference_price(gpu_dict, target_name):
    target_chip = extract_gpu_chip_key(target_name)
    if not target_chip:
        return None, None
    target_vram = extract_gpu_vram(target_name)
    matched = []
    for source_name, source_price in gpu_dict.items():
        source_chip = extract_gpu_chip_key(source_name)
        if not source_chip:
            continue
        if source_chip != target_chip:
            continue
        source_vram = extract_gpu_vram(source_name)
        if target_vram and source_vram and target_vram != source_vram:
            continue
        matched.append((source_name, source_price))
    if matched:
        matched.sort(key=lambda x: x[1])
        return matched[0][0], matched[0][1]
    return None, None

def extract_ssd_exact_key(name):
    """提取SSD型号的关键标识，用于匹配价格"""
    name = name.strip().replace(" ", "").upper()
    # 扩展品牌列表
    brand = re.search(r"(佰维|梵想|西数|致态|三星|雷克沙|宏碁|铠侠|惠普|英特尔|INTEL|HP|KIOXIA|LEXAR|ACER|BIWIN|SAMSUNG|ZHITAI|WD)", name)
    # 扩展型号列表 - 包含更多常见型号
    model = re.search(r"(NV7400|NV7100|NV3500|NV3000|S500PRO|S790|SP510|SP500|SN7100|SN850|SN770|TIPLUS7100|TIPLUS5000|TI600|990PRO|990EVO|9100PRO|雷神THOR|THOR|GM7|GM9|GM9000|ARES|VD10|SF10|KP270|KP260|KP230|KP130|NV3|N5000|N3500|X570|FA200|7100|7400|980|970|EX900|EX950|KC3000|NVME|PCIE)", name)
    # 容量匹配（更宽松）
    cap = re.search(r"(\d+G|\d+TB|\d+T|\d+GB)", name)
    key_parts = []
    if brand: key_parts.append(brand.group(1))
    if model: key_parts.append(model.group(1))
    if cap: key_parts.append(cap.group(1))
    # 如果没有匹配到品牌或型号，使用名称本身作为key（去除空格后）
    if not key_parts:
        return name[:50]  # 使用前50个字符作为唯一标识
    return "".join(key_parts)

# -------------------------- CPU 爬取函数 --------------------------
def fetch_cpu_prices():
    """爬取CPU价格，返回列表格式"""
    try:
        res = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        
        cpu_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            print(f"🔍 CPU正则提取，找到 {len(matches)} 个匹配")
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        cpu_list.append({"name": name.strip(), "price": int(float(price))})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not cpu_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                    
                    price_span = item.find('span', class_='product-price')
                    if price_span:
                        original_price = price_span.get('data-original', '')
                        if original_price:
                            try:
                                price = int(float(original_price))
                                cpu_list.append({"name": name, "price": price})
                                continue
                            except:
                                pass
                        
                        price_text_span = price_span.find('span', class_='price-text')
                        if price_text_span:
                            price_text = price_text_span.get_text(strip=True)
                            price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                            if price_match:
                                try:
                                    price = int(float(price_match.group(1)))
                                    cpu_list.append({"name": name, "price": price})
                                except:
                                    pass
        
        # 方法3：如果以上方法都失败，尝试从表格中提取数据
        if not cpu_list:
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



def fetch_gpu_prices():
    """爬取显卡价格，返回列表格式（不依赖Playwright）"""
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        gpu_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本/Markdown格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        gpu_list.append({"name": name.strip(), "price": int(float(price))})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 ul.parts-list 中提取数据
        if not gpu_list:
            parts_list = soup.find('ul', class_='parts-list')
            if not parts_list:
                parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                        
                        if len(name) > 3:
                            gpu_list.append({"name": name, "price": price})
        
        # 方法3：从HTML表格中提取数据
        if not gpu_list:
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
                            try:
                                price = int(float(price_match.group(1)))
                                gpu_list.append({"name": name, "price": price})
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

def fetch_ram_prices_new():
    """爬取内存价格，返回列表格式（不依赖Playwright）"""
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        ram_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本/Markdown格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3:
                    if any(w in name for w in RAM_EXCLUDE_LIST):
                        continue
                    try:
                        final_price = int(float(price)) + RAM_ASC_TECH_ADD if "阿斯加特" in name else int(float(price))
                        ram_list.append({"name": name.strip(), "price": final_price})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 ul.parts-list 中提取数据
        if not ram_list:
            parts_list = soup.find('ul', class_='parts-list')
            if not parts_list:
                parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        if any(w in name for w in RAM_EXCLUDE_LIST):
                            continue
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                        
                        final_price = price + RAM_ASC_TECH_ADD if "阿斯加特" in name else price
                        ram_list.append({"name": name, "price": final_price})
        
        # 方法3：从HTML表格中提取数据
        if not ram_list:
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
                            if any(w in name for w in RAM_EXCLUDE_LIST):
                                continue
                            try:
                                price = int(float(price_match.group(1)))
                                final_price = price + RAM_ASC_TECH_ADD if "阿斯加特" in name else price
                                ram_list.append({"name": name, "price": final_price})
                            except:
                                pass
        
        print(f"📊 爬取到 {len(ram_list)} 个内存型号")
        if ram_list:
            print("📋 部分内存价格:")
            for i, ram in enumerate(ram_list[:8]):
                print(f"   {ram['name'][:40]}...: ￥{ram['price']}")
        
        return ram_list
    except Exception as e:
        print(f"❌ 内存爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def fetch_mb_prices():
    try:
        res = requests.get(MB_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        mb_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3 and MB_EXCLUDE not in name and not is_garbled(name):
                    try:
                        mb_list.append({"name": name.strip(), "price": int(float(price))})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not mb_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        if MB_EXCLUDE in name or is_garbled(name):
                            continue
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            mb_list.append({"name": name, "price": price})
        
        return mb_list
    except Exception:
        return []

def fetch_raw_ram_prices():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        ram_dict = {}
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        feat = extract_ram_feature(name.strip())
                        if feat:
                            ram_dict[feat] = str(int(float(price)))
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not ram_dict:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            feat = extract_ram_feature(name)
                            if feat:
                                ram_dict[feat] = str(price)
        
        return ram_dict
    except Exception:
        return {}

def fetch_processed_ram():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        ram_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            print(f"🔍 内存正则提取，找到 {len(matches)} 个匹配")
            for name, price in matches:
                if len(name.strip()) > 3:
                    if any(w in name for w in RAM_EXCLUDE_LIST):
                        continue
                    try:
                        final_p = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                        ram_list.append({"name": name.strip(), "price": final_p})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not ram_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            if any(w in name for w in RAM_EXCLUDE_LIST):
                                continue
                            
                            final_p = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                            ram_list.append({"name": name, "price": final_p})
        
        # 方法3：如果以上方法都失败，尝试旧方法（查找产品名称标签）
        if not ram_list:
            product_names = soup.find_all('span', class_='product-name')
            
            for name_span in product_names:
                name = name_span.get('data-fullname', '').strip()
                if not name:
                    name = name_span.get_text(strip=True)
                
                price_span = name_span.find_next_sibling('span', class_='product-price')
                if price_span:
                    original_price = price_span.get('data-original', '')
                    if original_price:
                        try:
                            price = int(float(original_price))
                        except:
                            original_price = ''
                    
                    if not original_price:
                        price_text = price_span.get_text(strip=True)
                        price_match = re.search(r'￥(\d+(?:\.\d+)?)', price_text)
                        if price_match:
                            price = price_match.group(1)
                        else:
                            continue
                    
                    if any(w in name for w in RAM_EXCLUDE_LIST):
                        continue
                    
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
    """爬取固态硬盘价格，返回字典和列表格式"""
    try:
        res = requests.get(SSD_SOURCE_URL, headers=HEADERS, timeout=15)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        ssd_map = {}
        ssd_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            print(f"🔍 SSD正则提取，找到 {len(matches)} 个匹配")
            for name, price in matches:
                if len(name.strip()) > 3 and not any(ex in name for ex in SSD_EXCLUDE_LIST):
                    try:
                        price_val = int(float(price))
                        key = extract_ssd_exact_key(name.strip())
                        ssd_map[key] = price_val
                        ssd_list.append({"name": name.strip(), "price": price_val})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not ssd_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            if not any(ex in name for ex in SSD_EXCLUDE_LIST):
                                key = extract_ssd_exact_key(name)
                                ssd_map[key] = price
                                ssd_list.append({"name": name, "price": price})
        
        # 方法3：如果以上方法都失败，尝试从表格中提取数据
        if not ssd_list:
            tables = soup.find_all('table')
            print(f"🔍 SSD页面找到 {len(tables)} 个表格")
            
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
                            if not any(ex in name for ex in SSD_EXCLUDE_LIST):
                                key = extract_ssd_exact_key(name)
                                ssd_map[key] = price
                                ssd_list.append({"name": name, "price": price})
        
        print(f"📊 爬取到 {len(ssd_list)} 个固态硬盘型号")
        if ssd_list:
            print("📋 部分固态硬盘价格:")
            for i, ssd in enumerate(ssd_list[:8]):
                print(f"   {ssd['name'][:40]}...: ￥{ssd['price']}")
        
        return ssd_map, ssd_list
    except Exception as e:
        print(f"❌ 固态硬盘爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return {}, []

# 新增机箱爬取函数
def fetch_case_prices():
    try:
        res = requests.get(CASE_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        case_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3:
                    try:
                        case_list.append({"name": name.strip(), "price": int(float(price)), "image_url": ""})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not case_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            img_url = ""
                            img_tag = item.find('img', class_='product-image')
                            if img_tag:
                                img_url = img_tag.get('data-full-src', '')
                                if not img_url:
                                    img_url = img_tag.get('src', '')
                            
                            case_list.append({"name": name, "price": price, "image_url": img_url})
        
        return case_list
    except Exception as e:
        print(f"❌ 机箱数据爬取失败：{e}")
        return []

# 新增电源爬取函数
def fetch_power_prices():
    try:
        res = requests.get(POWER_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        power_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3 and not any(ex in name for ex in POWER_EXCLUDE_LIST):
                    try:
                        power_list.append({"name": name.strip(), "price": int(float(price))})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not power_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        if any(ex in name for ex in POWER_EXCLUDE_LIST):
                            continue
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            power_list.append({"name": name, "price": price})
        
        return power_list
    except Exception as e:
        print(f"❌ 电源数据爬取失败：{e}")
        return []

# 新增散热器爬取函数
def fetch_cooler_prices():
    try:
        res = requests.get(COOLER_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        text = res.text
        soup = BeautifulSoup(text, "html.parser")
        cooler_list = []
        
        # 方法1：优先使用正则从文本中提取（网站返回纯文本格式）
        matches = re.findall(r'-\s*([^\n￥]+?)\￥(\d+(?:\.\d+)?)', text)
        if matches:
            for name, price in matches:
                if len(name.strip()) > 3 and any(brand in name for brand in COOLER_BRANDS):
                    try:
                        cooler_list.append({"name": name.strip(), "price": int(float(price)), "image_url": ""})
                    except:
                        pass
        
        # 方法2：如果正则提取失败，尝试从 id="list" ul 列表中提取数据
        if not cooler_list:
            parts_list = soup.find('ul', id='list')
            if parts_list:
                items = parts_list.find_all('li')
                for item in items:
                    name_span = item.find('span', class_='product-name')
                    if name_span:
                        name = name_span.get('data-fullname', '').strip()
                        if not name:
                            name = name_span.get_text(strip=True)
                        
                        if not any(brand in name for brand in COOLER_BRANDS):
                            continue
                        
                        price_span = item.find('span', class_='product-price')
                        if price_span:
                            original_price = price_span.get('data-original', '')
                            if original_price:
                                try:
                                    price = int(float(original_price))
                                except:
                                    original_price = ''
                            
                            if not original_price:
                                price_text_span = price_span.find('span', class_='price-text')
                                if price_text_span:
                                    price_text = price_text_span.get_text(strip=True)
                                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        try:
                                            price = int(float(price_match.group(1)))
                                        except:
                                            continue
                                else:
                                    continue
                            
                            img_url = ""
                            img_tag = item.find('img', class_='product-image')
                            if img_tag:
                                img_url = img_tag.get('data-full-src', '')
                                if not img_url:
                                    img_url = img_tag.get('src', '')
                            
                            cooler_list.append({"name": name, "price": price, "image_url": img_url})
        
        return cooler_list
    except Exception as e:
        print(f"❌ 散热器数据爬取失败：{e}")
        return []

# -------------------------- 生成格式函数 --------------------------
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

def get_ssd_capacity_bonus(name):
    """根据SSD容量返回价格加成：1T+50，2T+100"""
    name_upper = name.upper()
    if '1T' in name_upper and not ('2T' in name_upper or '4T' in name_upper or '8T' in name_upper or '16T' in name_upper):
        return 50
    elif '2T' in name_upper and not ('4T' in name_upper or '8T' in name_upper or '16T' in name_upper):
        return 100
    return 0

def update_ssd_prices():
    """修复后的SSD价格更新函数 - 使用模糊匹配"""
    try:
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        ssd_map, ssd_list = fetch_ssd_exact_data()
        
        # 如果爬取失败或为空，保留原有数据
        if not ssd_list:
            print("⚠️ SSD数据获取失败或为空，保留原有SSD数据")
            return 0
        
        # 将列表转换为字典，方便查找（使用完整名称作为key）
        ssd_dict = {ssd["name"]: ssd["price"] for ssd in ssd_list}
        
        updated = 0
        same_count = 0
        no_match_count = 0

        # 计算特定硬盘价格
        nv7400_2t_price = 0
        for ssd in ssd_list:
            if "佰维" in ssd["name"] and "NV7400" in ssd["name"] and ("2T" in ssd["name"] or "2TB" in ssd["name"]):
                nv7400_2t_price = ssd["price"]
                break

        nv7400_1t_price = int(nv7400_2t_price * 0.53) if nv7400_2t_price > 0 else 0

        # 特殊处理的型号（需要价格调整）
        special_models = {
            "佰维 NV7400 1T TLC颗粒 读速7400MB/s": {"adjust": -90, "base_price": nv7400_1t_price},
            "佰维 NV7400 2T TLC颗粒 读速7400MB/s": {"adjust": -300, "base_price": nv7400_2t_price},
        }

        # 更新SSD价格 - 遍历HTML文件中的每个SSD行
        for i in range(len(lines)):
            line = lines[i]
            match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
            if not match:
                continue
            
            ssd_name = match.group(1)
            old_price = int(match.group(2))
            
            # 获取容量加成
            capacity_bonus = get_ssd_capacity_bonus(ssd_name)
            
            # 检查是否是特殊型号
            if ssd_name in special_models:
                special_info = special_models[ssd_name]
                if special_info["base_price"] > 0:
                    new_price = special_info["base_price"] + special_info["adjust"] + capacity_bonus
                    if new_price != old_price:
                        lines[i] = re.sub(r'p:\d+', f'p:{new_price}', line)
                        updated += 1
                        print(f"  ✓ 特殊更新: {ssd_name[:30]}... ￥{old_price} -> ￥{new_price} (容量加成:+{capacity_bonus})")
                    else:
                        same_count += 1
                continue
            
            # 使用模糊匹配查找爬取数据中的对应型号
            best_match = None
            best_score = 0
            
            # 先尝试精确匹配
            if ssd_name in ssd_dict:
                new_price = ssd_dict[ssd_name] + capacity_bonus
                if new_price != old_price:
                    lines[i] = re.sub(r'p:\d+', f'p:{new_price}', line)
                    updated += 1
                    print(f"  ✓ 精确匹配: {ssd_name[:30]}... ￥{old_price} -> ￥{new_price} (容量加成:+{capacity_bonus})")
                else:
                    same_count += 1
                continue
            
            # 提取容量信息用于匹配
            cap_match = re.search(r'(\d+G|\d+TB|\d+T)', ssd_name)
            capacity = cap_match.group(1) if cap_match else ""
            
            # 尝试使用型号关键字匹配
            ssd_key = extract_ssd_exact_key(ssd_name)
            
            # 在爬取数据中查找匹配
            for crawled_name, crawled_price in ssd_dict.items():
                crawled_key = extract_ssd_exact_key(crawled_name)
                
                # 检查容量是否一致
                crawled_cap = re.search(r'(\d+G|\d+TB|\d+T)', crawled_name)
                crawled_capacity = crawled_cap.group(1) if crawled_cap else ""
                
                # 容量必须一致才能匹配
                if capacity and crawled_capacity and capacity != crawled_capacity:
                    continue
                
                # 使用 fuzzywuzzy 进行模糊匹配
                from fuzzywuzzy import fuzz
                score = fuzz.token_set_ratio(ssd_name, crawled_name)
                
                # 如果key匹配，给予更高分数
                if ssd_key and crawled_key and ssd_key == crawled_key:
                    score = 95
                
                if score > best_score and score >= 70:
                    best_score = score
                    best_match = (crawled_name, crawled_price)
            
            if best_match:
                new_price = best_match[1] + capacity_bonus
                if new_price != old_price:
                    lines[i] = re.sub(r'p:\d+', f'p:{new_price}', line)
                    updated += 1
                    print(f"  ✓ 模糊匹配({best_score}%): {ssd_name[:25]}... -> {best_match[0][:25]}... ￥{old_price} -> ￥{new_price} (容量加成:+{capacity_bonus})")
                else:
                    same_count += 1
            else:
                no_match_count += 1
                print(f"  ⚠️ 未匹配: {ssd_name[:30]}...")

        # 查找SSD目标位置和范围
        target_idx = find_ssd_target_position(lines, SSD_TARGET_LINE)
        if target_idx != -1:
            # 找到目标行之后的所有SSD行，删除它们
            start_pos = target_idx + 1
            end_pos = find_next_non_ssd_line(lines, target_idx)
            
            # 删除现有的SSD数据行
            del lines[start_pos:end_pos]
            
            # 准备新SSD数据（只包含不在HTML文件中的新硬盘）
            existing_names = set()
            # 收集HTML文件中已存在的SSD名称
            for line in lines:
                match = re.search(r'{n:"([^"]+)",p:\d+}', line)
                if match:
                    existing_names.add(match.group(1))
            
            new_ssd_lines = []
            
            for ssd in ssd_list:
                # 只添加不在HTML文件中的新SSD
                if ssd["name"] not in existing_names:
                    # 应用容量加成
                    bonus = get_ssd_capacity_bonus(ssd["name"])
                    final_price = ssd["price"] + bonus
                    new_ssd_lines.append(f'{SSD_APPEND_INDENT}{{n:"{ssd["name"]}",p:{final_price}}},\n')
            
            # 在目标位置后插入新的SSD数据
            if new_ssd_lines:
                for j, new_line in enumerate(new_ssd_lines):
                    lines.insert(start_pos + j, new_line)

        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # 计算调整后的价格
        adjusted_2t_price = nv7400_2t_price - 300 + 100 if nv7400_2t_price > 0 else 0
        adjusted_1t_price = nv7400_1t_price - 90 + 50 if nv7400_1t_price > 0 else 0
        
        print(f"✅ 固态硬盘更新完成")
        print(f"🧮 佰维 NV7400 2T 原始价格 = {nv7400_2t_price}")
        print(f"🧮 佰维 NV7400 2T 调整后价格 = {adjusted_2t_price} (-300 + 容量加成+100)")
        print(f"🧮 佰维 NV7400 1T 原始价格 = {nv7400_1t_price} (2T × 0.53)")
        print(f"🧮 佰维 NV7400 1T 调整后价格 = {adjusted_1t_price} (-90 + 容量加成+50)")
        print(f"🧮 更新了 {updated} 个SSD价格")
        print(f"🧮 价格不变 {same_count} 个")
        print(f"🧮 未匹配 {no_match_count} 个")
        print(f"🧮 添加了 {len(new_ssd_lines) if 'new_ssd_lines' in dir() else 0} 个新SSD型号")
        return updated
    except Exception as e:
        print(f"❌ 硬盘更新失败：{e}")
        import traceback
        traceback.print_exc()
        return 0

# -------------------------- CPU 更新函数 --------------------------
# 定义CPU目标行（插入位置的标记）
CPU_TARGET_LINE = 'i3-12100F 3.3G 四核'

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
                    new_price = None
                    
                    # 方法1：精确匹配
                    if model_name in cpu_dict:
                        new_price = cpu_dict[model_name]
                        print(f"  ✅ 精确匹配: {model_name[:30]}...")
                    else:
                        # 方法2：使用CPU核心型号关键字进行模糊匹配
                        new_price = fuzzy_match_price(model_name, cpu_dict)
                    
                    if new_price is not None:
                        new_price = int(new_price)
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

# -------------------------- 显卡更新函数 --------------------------
def update_gpu_prices():
    """爬取显卡价格并更新HTML中的显卡列表"""
    try:
        print("\n=== 开始更新显卡数据 ===")
        
        # 爬取源网站数据，返回列表格式
        gpu_list = fetch_gpu_prices()
        
        # 如果获取失败或返回空列表，保留原有数据
        if not gpu_list:
            print("⚠️ 显卡数据获取失败或为空，保留原有显卡数据")
            return
        
        # 将列表转换为字典，方便查找
        gpu_dict = {gpu["name"]: gpu["price"] for gpu in gpu_list}
        print(f"✅ 成功爬取 {len(gpu_dict)} 个显卡型号")
        
        # 读取HTML文件
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"📄 已读取 {len(lines)} 行 HTML 文件")
        
        # 找到vga数组区域（覆盖所有显卡型号，不依赖注释标记）
        start_idx = -1
        for i, l in enumerate(lines):
            if 'vga: [' in l:
                start_idx = i
                break
        if start_idx == -1:
            print("❌ 未找到vga数组开始位置")
            return
        print(f"📍 找到vga数组开始在第 {start_idx + 1} 行")
        
        end_idx = -1
        for i in range(start_idx + 1, len(lines)):
            if lines[i].strip() == '],':
                end_idx = i
                break
        if end_idx == -1:
            print("❌ 未找到vga数组结束位置")
            return
        print(f"📍 找到vga数组结束在第 {end_idx + 1} 行")
        
        update_count = 0
        same_count = 0
        no_match_count = 0
        chip_ref_count = 0
        
        # 更新现有显卡型号的价格
        pos = start_idx + 1
        while pos < end_idx:
            line = lines[pos]
            if '{n:"' in line and '",p:' in line:
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    old_price = int(match.group(2))
                    new_price = None
                    
                    # 方法1：精确匹配
                    if model_name in gpu_dict:
                        new_price = gpu_dict[model_name]
                        print(f"  ✅ 精确匹配: {model_name[:40]}...")
                    else:
                        # 方法2：使用显卡关键字进行匹配
                        html_key = extract_gpu_exact_key(model_name)
                        if html_key:
                            for source_name in gpu_dict:
                                source_key = extract_gpu_exact_key(source_name)
                                if source_key and html_key == source_key:
                                    new_price = gpu_dict[source_name]
                                    print(f"  ✅ 关键字匹配: {model_name[:40]}... ≈ {source_name[:40]}...")
                                    break
                    
                    # 方法3：基于核心关键字匹配（品牌+型号+显存）
                    if new_price is None:
                        for source_name in gpu_dict:
                            if match_core_keywords(model_name, source_name):
                                new_price = gpu_dict[source_name]
                                print(f"  ✅ 核心匹配: {model_name[:40]}... ≈ {source_name[:40]}...")
                                break
                    
                    # 方法4：芯片级参考匹配（跨品牌，同GPU芯片+同显存）
                    # 微星-、撼讯系列显卡不参与跨品牌匹配，避免被其他品牌价格影响
                    if new_price is None and not (model_name.startswith("微星-") or model_name.startswith("撼讯")):
                        ref_name, ref_price = find_chip_reference_price(gpu_dict, model_name)
                        if ref_name and ref_price:
                            new_price = ref_price
                            chip_ref_count += 1
                            print(f"  ✅ 芯片参考匹配: {model_name[:40]}... ← {ref_name[:40]}...")
                    
                    # 方法5：使用fuzzywuzzy进行字符串相似度匹配（需GPU芯片+显存都一致）
                    # 微星-、撼讯系列显卡不参与跨品牌相似度匹配
                    if new_price is None and not (model_name.startswith("微星-") or model_name.startswith("撼讯")):
                        source_names = list(gpu_dict.keys())
                        best_match, score = process.extractOne(model_name, source_names)
                        if score >= 80:
                            target_chip = extract_gpu_chip_key(model_name)
                            match_chip = extract_gpu_chip_key(best_match)
                            target_vram = extract_gpu_vram(model_name)
                            match_vram = extract_gpu_vram(best_match)
                            chip_ok = target_chip and match_chip and target_chip == match_chip
                            vram_ok = (not target_vram) or (not match_vram) or (target_vram == match_vram)
                            if chip_ok and vram_ok:
                                new_price = gpu_dict[best_match]
                                print(f"  ✅ 相似度匹配({score}%): {model_name[:40]}... ≈ {best_match[:40]}...")
                            else:
                                print(f"  ⚠️ 相似度匹配跳过(芯片/显存不一致): {model_name[:30]}... ≈ {best_match[:30]}... ({score}%)")
                    
                    if new_price is not None:
                        new_price = int(new_price)
                        if "撼讯" in model_name:
                            markup = 100
                            new_price += markup
                            if "红魔" in model_name:
                                new_price += 600
                                markup += 600
                            if "暗黑犬" in model_name:
                                new_price += 250
                                markup += 250
                            print(f"  💰 撼讯加价+{markup}: {model_name[:40]}... 源价+{markup}=￥{new_price}")
                        if new_price != old_price:
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
        
        print(f"\n✅ 显卡价格自动更新完成：更新 {update_count} 个，价格不变 {same_count} 个，芯片参考匹配 {chip_ref_count} 个，未匹配(保留) {no_match_count} 个")
    except Exception as e:
        print(f"❌ 显卡更新失败：{e}")
        import traceback
        traceback.print_exc()

# -------------------------- 内存更新函数（新版） --------------------------
def update_ram_prices_new():
    """爬取内存价格并更新HTML中的内存列表（仿照显卡逻辑）"""
    try:
        print("\n=== 开始更新内存数据 ===")
        
        # 爬取源网站数据，返回列表格式
        ram_list = fetch_ram_prices_new()
        
        # 如果获取失败或返回空列表，保留原有数据
        if not ram_list:
            print("⚠️ 内存数据获取失败或为空，保留原有内存数据")
            return
        
        # 将列表转换为字典，方便查找
        ram_dict = {ram["name"]: ram["price"] for ram in ram_list}
        print(f"✅ 成功爬取 {len(ram_dict)} 个内存型号")
        
        # 读取HTML文件
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"📄 已读取 {len(lines)} 行 HTML 文件")
        
        # 找到ram数组区域（覆盖所有内存型号）
        start_idx = -1
        for i, l in enumerate(lines):
            if 'ram: [' in l:
                start_idx = i
                break
        if start_idx == -1:
            print("❌ 未找到ram数组开始位置")
            return
        print(f"📍 找到ram数组开始在第 {start_idx + 1} 行")
        
        end_idx = -1
        for i in range(start_idx + 1, len(lines)):
            if lines[i].strip() == '],':
                end_idx = i
                break
        if end_idx == -1:
            print("❌ 未找到ram数组结束位置")
            return
        print(f"📍 找到ram数组结束在第 {end_idx + 1} 行")
        
        update_count = 0
        same_count = 0
        no_match_count = 0
        ref_match_count = 0
        add_count = 0
        
        # 收集所有HTML中已有的内存型号名称
        existing_models = set()
        pos = start_idx + 1
        while pos < end_idx:
            line = lines[pos]
            if '{n:"' in line and '",p:' in line:
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    existing_models.add(match.group(1))
            pos += 1
        
        print(f"📋 HTML中已有 {len(existing_models)} 个内存型号")

        # 更新现有内存型号的价格
        pos = start_idx + 1
        while pos < end_idx:
            line = lines[pos]
            if '{n:"' in line and '",p:' in line:
                match = re.search(r'{n:"([^"]+)",p:(\d+)}', line)
                if match:
                    model_name = match.group(1)
                    old_price = int(match.group(2))
                    new_price = None

                    # 特殊处理：光威 天策 16G/32G 3200 白色 参考阿斯加特 TUF联名价格
                    if "光威 天策 16G（8*2）3200 白色" in model_name:
                        ref_price_from_html = 0
                        for temp_line in lines:
                            if "阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲" in temp_line:
                                price_match = re.search(r'p:(\d+)', temp_line)
                                if price_match:
                                    ref_price_from_html = int(price_match.group(1))
                                    break
                        if ref_price_from_html > 0:
                            new_price = ref_price_from_html
                            print(f"  ★ 特殊更新：光威 天策 16G 白色 = 阿斯加特 TUF联名(￥{ref_price_from_html})")
                    elif "光威 天策 32G（16*2）3200 白色" in model_name:
                        ref_price_from_html = 0
                        for temp_line in lines:
                            if "阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲" in temp_line:
                                price_match = re.search(r'p:(\d+)', temp_line)
                                if price_match:
                                    ref_price_from_html = int(price_match.group(1))
                                    break
                        if ref_price_from_html > 0:
                            new_price = ref_price_from_html
                            print(f"  ★ 特殊更新：光威 天策 32G 白色 = 阿斯加特 TUF联名(￥{ref_price_from_html})")

                    # 方法1：精确匹配
                    if new_price is None and model_name in ram_dict:
                        new_price = ram_dict[model_name]
                        print(f"  ✅ 精确匹配: {model_name[:40]}...")
                    elif new_price is None:
                        # 方法2：使用内存关键字进行匹配
                        html_key = extract_ram_exact_key(model_name)
                        if html_key:
                            for source_name in ram_dict:
                                source_key = extract_ram_exact_key(source_name)
                                if source_key and html_key == source_key:
                                    new_price = ram_dict[source_name]
                                    print(f"  ✅ 关键字匹配: {model_name[:40]}... ≈ {source_name[:40]}...")
                                    break
                    
                    # 方法3：基于核心关键字匹配（品牌+容量+频率+时序）
                    if new_price is None:
                        for source_name in ram_dict:
                            if match_ram_core_keywords(model_name, source_name):
                                new_price = ram_dict[source_name]
                                print(f"  ✅ 核心匹配: {model_name[:40]}... ≈ {source_name[:40]}...")
                                break
                    
                    # 方法4：基于品牌+容量+频率+时序的参考匹配（必须同品牌）
                    if new_price is None:
                        target_brand = extract_ram_brand(model_name)
                        target_cap = extract_ram_capacity(model_name)
                        target_freq = extract_ram_freq(model_name)
                        target_cas = extract_ram_cas(model_name)
                        
                        if target_brand and target_cap and target_freq:
                            matched_prices = []
                            for source_name, source_price in ram_dict.items():
                                source_brand = extract_ram_brand(source_name)
                                source_cap = extract_ram_capacity(source_name)
                                source_freq = extract_ram_freq(source_name)
                                source_cas = extract_ram_cas(source_name)
                                
                                brand_match = target_brand == source_brand
                                cap_match = target_cap == source_cap
                                freq_match = target_freq == source_freq
                                cas_match = (not target_cas) or (not source_cas) or (target_cas == source_cas)
                                
                                if brand_match and cap_match and freq_match and cas_match:
                                    matched_prices.append((source_name, source_price))
                            
                            if matched_prices:
                                matched_prices.sort(key=lambda x: x[1])
                                ref_name, ref_price = matched_prices[0]
                                new_price = ref_price
                                ref_match_count += 1
                                print(f"  ✅ 参数参考匹配: {model_name[:40]}... ← {ref_name[:40]}...")
                    
                    # 方法5：使用fuzzywuzzy进行字符串相似度匹配（需品牌+容量+频率一致）
                    if new_price is None:
                        source_names = list(ram_dict.keys())
                        best_match, score = process.extractOne(model_name, source_names)
                        if score >= 80:
                            target_brand = extract_ram_brand(model_name)
                            match_brand = extract_ram_brand(best_match)
                            target_cap = extract_ram_capacity(model_name)
                            match_cap = extract_ram_capacity(best_match)
                            target_freq = extract_ram_freq(model_name)
                            match_freq = extract_ram_freq(best_match)
                            
                            brand_ok = (not target_brand) or (not match_brand) or (target_brand == match_brand)
                            cap_ok = (not target_cap) or (not match_cap) or (target_cap == match_cap)
                            freq_ok = (not target_freq) or (not match_freq) or (target_freq == match_freq)
                            
                            if brand_ok and cap_ok and freq_ok:
                                new_price = ram_dict[best_match]
                                print(f"  ✅ 相似度匹配({score}%): {model_name[:40]}... ≈ {best_match[:40]}...")
                            else:
                                print(f"  ⚠️ 相似度匹配跳过(品牌/容量/频率不一致): {model_name[:30]}... ≈ {best_match[:30]}... ({score}%)")
                    
                    if new_price is not None:
                        new_price = int(new_price)
                        if new_price != old_price:
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
        
        # 自动追加新的内存型号
        new_models_added = []
        for source_name, source_price in ram_dict.items():
            # 检查是否已存在于HTML中（精确匹配）
            if source_name not in existing_models:
                # 检查是否通过关键字匹配已存在
                source_key = extract_ram_exact_key(source_name)
                already_exists = False
                for existing_model in existing_models:
                    existing_key = extract_ram_exact_key(existing_model)
                    if source_key and existing_key and source_key == existing_key:
                        already_exists = True
                        break
                
                # 检查是否通过核心匹配已存在
                if not already_exists:
                    for existing_model in existing_models:
                        if match_ram_core_keywords(source_name, existing_model):
                            already_exists = True
                            break
                
                if not already_exists:
                    # 追加新型号
                    new_line = f'            {{n:"{source_name}",p:{source_price}}},\n'
                    lines.insert(end_idx, new_line)
                    end_idx += 1
                    add_count += 1
                    new_models_added.append(source_name)
                    print(f"  ➕ 新增型号: {source_name[:40]}... ￥{source_price}")
        
        # 写入文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        print(f"\n✅ 内存价格自动更新完成：更新 {update_count} 个，价格不变 {same_count} 个，参数参考匹配 {ref_match_count} 个，未匹配(保留) {no_match_count} 个，新增 {add_count} 个")
        if new_models_added:
            print("📥 新增型号列表:")
            for model in new_models_added[:10]:
                print(f"   - {model[:50]}...")
            if len(new_models_added) > 10:
                print(f"   ... 还有 {len(new_models_added) - 10} 个新增型号")
    except Exception as e:
        print(f"❌ 内存更新失败：{e}")
        import traceback
        traceback.print_exc()

# -------------------------- 内存定制价格（四要素匹配） --------------------------
def extract_ram_four_key(name):
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威|英睿达|十铨|宇瞻|影驰|海力士|镁光)"
    series_pattern = r"(银爵|星刃|女武神|皇家戟|复仇者|铂胜|Ballistix|Trident|Vengeance|FURY|XPG|DDR4|DDR5|马甲条|灯条|弗雷|雷神|海拉|海姆达尔)"
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
                    if "金百达 银爵 32G 16x2 3600 D4 C18" in lines[j]:
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
                    if "金百达 银爵 32G 16x2 3600 D4 C18" in lines[j]:
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

            # 特殊处理：光威 天策 16G（8*2）3200 白色 参考阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲 的价格
            if "光威 天策 16G（8*2）3200 白色" in ram_name:
                print(f"  🔍 查找: 光威 天策 16G（8*2）3200 白色 = 阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲")
                
                ref_price = 0
                for j in range(len(lines)):
                    if "阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲" in lines[j]:
                        price_match = re.search(r'p:(\d+)', lines[j])
                        if price_match:
                            ref_price = float(price_match.group(1))
                            print(f"     从HTML获取参考价格: {int(ref_price)}")
                            break
                
                if ref_price > 0:
                    final_price = ref_price
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲 = {int(final_price)}")
                else:
                    print(f"  ⚠ 阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：光威 天策 32G（16*2）3200 白色 参考阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲 的价格
            if "光威 天策 32G（16*2）3200 白色" in ram_name:
                print(f"  🔍 查找: 光威 天策 32G（16*2）3200 白色 = 阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲")
                
                ref_price = 0
                for j in range(len(lines)):
                    if "阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲" in lines[j]:
                        price_match = re.search(r'p:(\d+)', lines[j])
                        if price_match:
                            ref_price = float(price_match.group(1))
                            print(f"     从HTML获取参考价格: {int(ref_price)}")
                            break
                
                if ref_price > 0:
                    final_price = ref_price
                    special_handled = True
                    print(f"  ★ 匹配成功: {ram_name} -> 阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲 = {int(final_price)}")
                else:
                    print(f"  ⚠ 阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲 价格未获取到，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特 弗雷 16G 8*2 3200（包含有黑甲和无黑甲版本）参考爬取数据
            if "阿斯加特 弗雷 16G 8*2 3200" in ram_name:
                found = False
                # 优先查找无黑甲的弗雷 16G
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "阿斯加特" in item_name and "弗雷" in item_name and "16G" in item_name and "3200" in item_name and ("8x2" in item_name or "8*2" in item_name) and "黑甲" not in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                # 如果没找到无黑甲版本，尝试有黑甲版本
                if not found:
                    for ram_item in ram_list:
                        item_name = ram_item['name']
                        if "阿斯加特" in item_name and "弗雷" in item_name and "16G" in item_name and "3200" in item_name and ("8x2" in item_name or "8*2" in item_name) and "黑甲" in item_name:
                            final_price = float(ram_item['price'])
                            special_handled = True
                            found = True
                            print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                            break
                if not found:
                    print(f"  ⚠ 未找到阿斯加特 弗雷 16G 8*2 3200 相关型号，跳过更新")
                    special_handled = True
                continue

            # 特殊处理：阿斯加特 弗雷 32G 16*2 3200（包含有黑甲和无黑甲版本）参考爬取数据
            if "阿斯加特 弗雷 32G 16*2 3200" in ram_name:
                found = False
                # 优先查找无黑甲的弗雷 32G
                for ram_item in ram_list:
                    item_name = ram_item['name']
                    if "阿斯加特" in item_name and "弗雷" in item_name and "32G" in item_name and "3200" in item_name and ("16x2" in item_name or "16*2" in item_name) and "黑甲" not in item_name:
                        final_price = float(ram_item['price'])
                        special_handled = True
                        found = True
                        print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                        break
                # 如果没找到无黑甲版本，尝试有黑甲版本
                if not found:
                    for ram_item in ram_list:
                        item_name = ram_item['name']
                        if "阿斯加特" in item_name and "弗雷" in item_name and "32G" in item_name and "3200" in item_name and ("16x2" in item_name or "16*2" in item_name) and "黑甲" in item_name:
                            final_price = float(ram_item['price'])
                            special_handled = True
                            found = True
                            print(f"  ★ 匹配成功: {ram_name} -> {item_name} -> 价格 {int(final_price)}")
                            break
                if not found:
                    print(f"  ⚠ 未找到阿斯加特 弗雷 32G 16*2 3200 相关型号，跳过更新")
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
            if "金百达 银爵 32G 16x2 3600 D4 C18" in ram_name:
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
            elif "金百达_银爵 16G 6000单根 c30 m-die" in ram_name or "金百达 银爵 16G 6000 D5 C30" in ram_name:
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
                    elif "金百达 银爵 32G 16x2 3600 D4 C18" in ram_name:
                        jbd_32g_3600_c18_final = base_price  # 保存金百达_银爵 32G 3600海力士c18的价格
                    elif "宏碁掠夺者" in ram_name:
                        final_price = base_price + 300


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
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        all_items = []
        
        # 方法1：尝试从 parts-list ul 列表中提取数据（当前页面结构）
        parts_list = soup.find('ul', class_='parts-list')
        if parts_list:
            items = parts_list.find_all('li')
            for item in items:
                # 获取产品名称（优先使用 data-fullname 属性）
                name_span = item.find('span', class_='product-name')
                if name_span:
                    name = name_span.get('data-fullname', '').strip()
                    if not name:
                        name = name_span.get_text(strip=True)
                    
                    # 获取价格（优先使用 data-original 属性）
                    price_span = item.find('span', class_='product-price')
                    if price_span:
                        # 优先使用 data-original 属性
                        original_price = price_span.get('data-original', '')
                        if original_price:
                            try:
                                price = str(int(float(original_price)))
                            except:
                                original_price = ''
                        
                        if not original_price:
                            # 从 price-text 子标签获取
                            price_text_span = price_span.find('span', class_='price-text')
                            if price_text_span:
                                price_text = price_text_span.get_text(strip=True)
                                price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                if price_match:
                                    price = price_match.group(1)
                                else:
                                    continue
                            else:
                                continue
                        
                        all_items.append((name, price))
                        
                        # 提取四要素
                        brand, series, cas, capacity, freq = extract_ram_four_key(name)
                        
                        # 阿斯加特品牌价格增加
                        final_price = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                        
                        # 所有爬取到的数据都加入列表（不管是否能提取四要素）
                        ram_list.append({
                            'name': name,
                            'key': (brand, series, cas, capacity, freq),
                            'price': final_price
                        })
        
        # 方法2：如果列表提取失败，尝试旧方法（查找产品名称标签）
        if not ram_list:
            product_names = soup.find_all('span', class_='product-name')
            
            for name_span in product_names:
                # 获取产品名称（优先使用 data-fullname 属性）
                name = name_span.get('data-fullname', '').strip()
                if not name:
                    name = name_span.get_text(strip=True)
                
                # 查找紧邻的价格标签
                price_span = name_span.find_next_sibling('span', class_='product-price')
                if price_span:
                    # 优先使用 data-original 属性
                    original_price = price_span.get('data-original', '')
                    if original_price:
                        try:
                            price = str(int(float(original_price)))
                        except:
                            original_price = ''
                    
                    if not original_price:
                        price_text = price_span.get_text(strip=True)
                        price_match = re.search(r'￥(\d+(?:\.\d+)?)', price_text)
                        if price_match:
                            price = price_match.group(1)
                        else:
                            continue
                    
                    all_items.append((name, price))
                    
                    # 提取四要素
                    brand, series, cas, capacity, freq = extract_ram_four_key(name)
                    
                    # 阿斯加特品牌价格增加
                    final_price = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                    
                    # 所有爬取到的数据都加入列表（不管是否能提取四要素）
                    ram_list.append({
                        'name': name,
                        'key': (brand, series, cas, capacity, freq),
                        'price': final_price
                    })
        
        # 方法3：如果以上方法都失败，尝试使用正则从文本中提取
        if not ram_list:
            text = soup.get_text()
            for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", text):
                if len(name.strip()) > 3:
                    all_items.append((name.strip(), price))
                    
                    # 提取四要素
                    brand, series, cas, capacity, freq = extract_ram_four_key(name.strip())
                    
                    # 阿斯加特品牌价格增加
                    final_price = str(int(float(price) + RAM_ASC_TECH_ADD)) if "阿斯加特" in name else str(int(float(price)))
                    
                    ram_list.append({
                        'name': name.strip(),
                        'key': (brand, series, cas, capacity, freq),
                        'price': final_price
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
    """主板更新逻辑：保留现有型号，只更新价格，不删除，新型号追加"""
    print("\n" + "="*50)
    print("🔄 开始主板价格更新")
    print("="*50)
    
    try:
        # ========== 第一步：爬取源网站数据 ==========
        print("\n📥 第一步：爬取源网站数据...")
        mb_list = fetch_mb_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not mb_list:
            print("⚠️ 主板数据获取失败或为空，保留原有主板数据")
            return
        
        # 将列表转换为字典，方便查找
        mb_dict = {mb["name"]: mb["price"] for mb in mb_list}
        print(f"   爬取到 {len(mb_dict)} 个主板型号")
        
        # 打印部分爬取数据用于调试
        print("\n   📋 部分爬取数据:")
        for i, (name, price) in enumerate(list(mb_dict.items())[:10]):
            print(f"      {name[:45]}... -> ￥{price}")
        
        # ========== 第二步：读取HTML中的主板数据 ==========
        print("\n📖 第二步：读取HTML主板数据...")
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split('\n')
        
        # 找到主板区域开始和结束位置
        board_start_idx = -1
        board_end_idx = -1
        for i, line in enumerate(lines):
            if 'board: [' in line:
                board_start_idx = i
            elif board_start_idx != -1 and board_end_idx == -1 and line.strip() == '],':
                # 确认是主板数组的结束（主板后面是cooler或psu或ssd）
                if i + 1 < len(lines) and ('cooler: [' in lines[i + 1] or 'psu: [' in lines[i + 1] or 'ssd: [' in lines[i + 1]):
                    board_end_idx = i
                    break
        
        if board_start_idx == -1 or board_end_idx == -1:
            print("❌ 未找到主板区域")
            return
        
        print(f"   主板区域：第{board_start_idx + 1}行 - 第{board_end_idx + 1}行")
        
        # 解析HTML中的主板数据
        html_mbs = {}  # {型号名: (价格, 行索引)}
        for i in range(board_start_idx + 1, board_end_idx):
            line = lines[i]
            match = re.search(r'{n:"([^"]+)",p:(\d+(?:\.\d+)?)}', line)
            if match:
                name = match.group(1)
                price = int(float(match.group(2)))
                html_mbs[name] = (price, i)
        
        print(f"   HTML中有 {len(html_mbs)} 个主板型号")
        
        # ========== 第三步：比对并更新 ==========
        print("\n📝 第三步：比对并更新...")
        
        update_count = 0
        new_add_count = 0
        no_change_count = 0
        no_match_count = 0
        
        # 创建模糊匹配映射（用于处理名称略有差异的情况）
        def normalize_name(name):
            """标准化型号名，便于模糊匹配"""
            n = name.replace(' ', '').replace('_', '').replace('*', 'x').replace('（', '(').replace('）', ')')
            return n
        
        # 建立标准化映射
        html_normalized = {normalize_name(k): (k, v) for k, v in html_mbs.items()}
        mb_normalized = {normalize_name(k): (k, v) for k, v in mb_dict.items()}
        
        # 收集需要更新的数据
        updates = []  # [(行索引, 新的价格, 型号名, 旧价格)]
        new_items = []  # [(型号名, 价格)] - 需要追加的新型号
        matched_html = set()  # 已匹配的HTML型号
        matched_scraped = set()  # 已匹配的爬取型号
        
        # 首先进行精确匹配
        for scraped_name, scraped_price in mb_dict.items():
            if scraped_name in html_mbs:
                old_price, line_idx = html_mbs[scraped_name]
                if scraped_price != old_price:
                    updates.append((line_idx, scraped_price, scraped_name, old_price))
                else:
                    no_change_count += 1
                matched_html.add(scraped_name)
                matched_scraped.add(scraped_name)
        
        # 进行模糊匹配（处理名称略有差异的情况）
        for scraped_norm, (scraped_name, scraped_price) in mb_normalized.items():
            if scraped_name in matched_scraped:
                continue
            
            for html_norm, (html_name, (html_price, line_idx)) in html_normalized.items():
                if html_name in matched_html:
                    continue
                
                # 检查是否是同一个型号（去掉常见后缀后比较核心部分）
                def remove_suffix(name):
                    for suffix in ['黑甲', '白甲', '极夜黑', '极地白', 'PRO', 'PLUS', 'MAX']:
                        name = name.replace(suffix, '')
                    return name
                
                core_scraped = remove_suffix(scraped_norm)
                core_html = remove_suffix(html_norm)
                
                if core_scraped == core_html:
                    # 找到匹配！检查价格是否变化
                    if scraped_price != html_price:
                        updates.append((line_idx, scraped_price, scraped_name, html_price))
                        print(f"   🔗 模糊匹配: {scraped_name[:35]}... ≈ {html_name[:35]}...")
                    else:
                        no_change_count += 1
                    matched_html.add(html_name)
                    matched_scraped.add(scraped_name)
                    break
        
        # 统计未匹配的HTML型号
        no_match_count = len(html_mbs) - len(matched_html)
        
        # 执行更新
        for line_idx, new_price, name, old_price in updates:
            lines[line_idx] = re.sub(r'p:\d+(?:\.\d+)?', f'p:{new_price}', lines[line_idx])
            print(f"   ✓ 更新: {name[:35]}... ￥{old_price} -> ￥{new_price}")
            update_count += 1
        
        # 追加新型号（只有确实没匹配上的才追加）
        for scraped_name, price in mb_dict.items():
            if scraped_name not in matched_scraped:
                # 检查是否已经在HTML中（作为手动添加的型号）
                found_in_html = False
                for line in lines:
                    if f'{{n:"{scraped_name}"' in line:
                        found_in_html = True
                        break
                if not found_in_html:
                    new_items.append((scraped_name, price))
        
        if new_items:
            print(f"\n   📌 追加 {len(new_items)} 个新型号:")
            new_lines = []
            for name, price in new_items:
                new_line = f'            {{n:"{name}",p:{price}}},'
                new_lines.append(new_line)
                print(f"   + 新增: {name[:40]}... ￥{price}")
                new_add_count += 1
            
            # 在主板区域末尾追加（在],前面添加新行）
            lines[board_end_idx] = '\n'.join(new_lines) + '\n' + lines[board_end_idx]
        
        # ========== 第四步：保存文件 ==========
        print("\n💾 第四步：保存文件...")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        # ========== 输出统计 ==========
        print("\n" + "="*50)
        print(f"📊 更新统计:")
        print(f"   - 价格更新: {update_count} 个型号")
        print(f"   - 新型号追加: {new_add_count} 个型号")
        print(f"   - 价格不变: {no_change_count} 个型号")
        print(f"   - 未匹配(保留): {no_match_count} 个型号")
        print("="*50)
        print("✅ 主板更新完成!")
        
    except Exception as e:
        print(f"❌ 主板更新失败：{e}")
        import traceback
        traceback.print_exc()

def update_ram_new():
    """内存更新逻辑（简洁版）：
    1. 爬取源网站获取最新的型号和价格
    2. 比对index里的内存型号和价格（支持模糊匹配）
    3. 价格变化直接更新
    4. 新型号追加到内存区域末尾
    """
    print("\n" + "="*50)
    print("🔄 开始内存价格更新")
    print("="*50)
    
    try:
        # ========== 第一步：爬取源网站数据 ==========
        print("\n📥 第一步：爬取源网站数据...")
        scraped_data = fetch_all_ram_from_source()
        if not scraped_data:
            print("❌ 未能获取到源网站数据")
            return
        print(f"   爬取到 {len(scraped_data)} 个内存型号")
        
        # 打印部分爬取数据用于调试
        print("\n   📋 部分爬取数据:")
        for i, (name, price) in enumerate(list(scraped_data.items())[:10]):
            print(f"      {name[:45]}... -> ￥{price}")
        
        # ========== 第二步：读取HTML中的内存数据 ==========
        print("\n📖 第二步：读取HTML内存数据...")
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split('\n')
        
        # 找到内存区域开始和结束位置
        ram_start_idx = -1
        ram_end_idx = -1
        for i, line in enumerate(lines):
            if 'ram: [' in line:
                ram_start_idx = i
            elif ram_start_idx != -1 and ram_end_idx == -1 and line.strip() == '],':
                # 确认是内存数组的结束（检查后面是否是board）
                if i + 1 < len(lines) and 'board: [' in lines[i + 1]:
                    ram_end_idx = i
                    break
        
        if ram_start_idx == -1 or ram_end_idx == -1:
            print("❌ 未找到内存区域")
            return
        
        print(f"   内存区域：第{ram_start_idx + 1}行 - 第{ram_end_idx + 1}行")
        
        # 解析HTML中的内存数据
        html_rams = {}  # {型号名: (价格, 行索引)}
        for i in range(ram_start_idx + 1, ram_end_idx):
            line = lines[i]
            match = re.search(r'{n:"([^"]+)",p:(\d+(?:\.\d+)?)}', line)
            if match:
                name = match.group(1)
                price = int(float(match.group(2)))
                html_rams[name] = (price, i)
        
        print(f"   HTML中有 {len(html_rams)} 个内存型号")
        
        # ========== 第三步：比对并更新 ==========
        print("\n📝 第三步：比对并更新...")
        
        update_count = 0
        new_add_count = 0
        no_change_count = 0
        
        # 创建模糊匹配映射（用于处理名称略有差异的情况）
        def normalize_name(name):
            """标准化型号名，便于模糊匹配"""
            # 去掉空格、下划线、星号等差异
            n = name.replace(' ', '').replace('_', '').replace('*', 'x').replace('（', '(').replace('）', ')')
            return n
        
        # 建立标准化映射
        html_normalized = {normalize_name(k): (k, v) for k, v in html_rams.items()}
        scraped_normalized = {normalize_name(k): (k, v) for k, v in scraped_data.items()}
        
        # 收集需要更新的数据
        updates = []  # [(行索引, 新的价格)]
        new_items = []  # [型号名] - 需要追加的新型号
        matched_html = set()  # 已匹配的HTML型号
        matched_scraped = set()  # 已匹配的爬取型号
        
        # 首先进行精确匹配
        for scraped_name, scraped_price in scraped_data.items():
            if scraped_name in html_rams:
                old_price, line_idx = html_rams[scraped_name]
                if scraped_price != old_price:
                    updates.append((line_idx, scraped_price, scraped_name, old_price))
                else:
                    no_change_count += 1
                matched_html.add(scraped_name)
                matched_scraped.add(scraped_name)
        
        # 进行模糊匹配（处理名称略有差异的情况，如"黑甲"后缀）
        for scraped_norm, (scraped_name, scraped_price) in scraped_normalized.items():
            if scraped_name in matched_scraped:
                continue
            
            for html_norm, (html_name, (html_price, line_idx)) in html_normalized.items():
                if html_name in matched_html:
                    continue
                
                # 检查是否是同一个型号（忽略"黑甲"等后缀差异）
                # 策略：去掉"黑甲"、"白甲"等后缀后比较核心部分
                def remove_suffix(name):
                    for suffix in ['黑甲', '白甲', '极夜黑', '极地白']:
                        name = name.replace(suffix, '')
                    return name
                
                core_scraped = remove_suffix(scraped_norm)
                core_html = remove_suffix(html_norm)
                
                if core_scraped == core_html:
                    # 找到匹配！检查价格是否变化
                    if scraped_price != html_price:
                        updates.append((line_idx, scraped_price, scraped_name, html_price))
                        print(f"   🔗 模糊匹配: {scraped_name[:35]}... ≈ {html_name[:35]}...")
                    else:
                        no_change_count += 1
                    matched_html.add(html_name)
                    matched_scraped.add(scraped_name)
                    break
        
        # 执行更新
        for line_idx, new_price, name, old_price in updates:
            lines[line_idx] = re.sub(r'p:\d+(?:\.\d+)?', f'p:{new_price}', lines[line_idx])
            print(f"   ✓ 更新: {name[:35]}... ￥{old_price} -> ￥{new_price}")
            update_count += 1
        
        # 追加新型号（只有确实没匹配上的才追加）
        if new_items:
            print(f"\n   📌 追加 {len(new_items)} 个新型号:")
            new_lines = []
            for name, price in new_items:
                new_line = f'            {{n:"{name}",p:{price}}},\n'
                new_lines.append(new_line)
                print(f"   + 新增: {name[:40]}... ￥{price}")
                new_add_count += 1
            
            # 在内存区域末尾追加
            lines[ram_end_idx] = lines[ram_end_idx] + '\n' + ''.join(new_lines)
        
        # ========== 第四步：保存文件 ==========
        print("\n💾 第四步：保存文件...")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        # ========== 输出统计 ==========
        print("\n" + "="*50)
        print(f"📊 更新统计:")
        print(f"   - 价格更新: {update_count} 个型号")
        print(f"   - 新型号追加: {new_add_count} 个型号")
        print(f"   - 价格不变: {no_change_count} 个型号")
        print("="*50)
        print("✅ 内存更新完成!")
        
    except Exception as e:
        print(f"❌ 内存更新失败: {e}")
        import traceback
        traceback.print_exc()

def fetch_all_ram_from_source():
    """从源网站爬取所有内存数据"""
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, "html.parser")
        
        ram_dict = {}
        
        # 方法1：尝试从 parts-list ul 列表中提取数据（当前页面结构）
        parts_list = soup.find('ul', class_='parts-list')
        if parts_list:
            items = parts_list.find_all('li')
            for item in items:
                # 获取产品名称（优先使用 data-fullname 属性）
                name_span = item.find('span', class_='product-name')
                if name_span:
                    name = name_span.get('data-fullname', '').strip()
                    if not name:
                        name = name_span.get_text(strip=True)
                    
                    # 获取价格（优先使用 data-original 属性）
                    price_span = item.find('span', class_='product-price')
                    if price_span:
                        # 优先使用 data-original 属性
                        original_price = price_span.get('data-original', '')
                        if original_price:
                            try:
                                price = int(float(original_price))
                            except:
                                original_price = ''
                        
                        if not original_price:
                            # 从 price-text 子标签获取
                            price_text_span = price_span.find('span', class_='price-text')
                            if price_text_span:
                                price_text = price_text_span.get_text(strip=True)
                                price_match = re.search(r'(\d+(?:\.\d+)?)', price_text)
                                if price_match:
                                    try:
                                        price = int(float(price_match.group(1)))
                                    except:
                                        continue
                            else:
                                continue
                        
                        # 排除列表中的品牌
                        if any(w in name for w in RAM_EXCLUDE_LIST):
                            continue
                        
                        # 阿斯加特品牌价格增加
                        if "阿斯加特" in name:
                            price += RAM_ASC_TECH_ADD
                        
                        ram_dict[name] = price
        
        # 方法2：如果列表提取失败，尝试旧方法（查找产品名称标签）
        if not ram_dict:
            product_names = soup.find_all('span', class_='product-name')
            
            for name_span in product_names:
                # 获取产品名称
                name = name_span.get('data-fullname', '').strip()
                if not name:
                    name = name_span.get_text(strip=True)
                
                # 排除列表中的品牌
                if any(w in name for w in RAM_EXCLUDE_LIST):
                    continue
                
                # 查找价格
                price_span = name_span.find_next_sibling('span', class_='product-price')
                if price_span:
                    # 优先使用 data-original 属性
                    original_price = price_span.get('data-original', '')
                    if original_price:
                        try:
                            price = int(float(original_price))
                        except:
                            original_price = ''
                    
                    if not original_price:
                        price_text = price_span.get_text(strip=True)
                        price_match = re.search(r'￥(\d+(?:\.\d+)?)', price_text)
                        if price_match:
                            price = int(float(price_match.group(1)))
                        else:
                            continue
                    
                    # 阿斯加特品牌价格增加
                    if "阿斯加特" in name:
                        price += RAM_ASC_TECH_ADD
                    
                    ram_dict[name] = price
        
        # 方法3：如果以上方法都失败，尝试使用正则从文本中提取
        if not ram_dict:
            text = soup.get_text()
            for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", text):
                if len(name.strip()) > 3:
                    if any(w in name for w in RAM_EXCLUDE_LIST):
                        continue
                    try:
                        price_val = int(float(price))
                        if "阿斯加特" in name:
                            price_val += RAM_ASC_TECH_ADD
                        ram_dict[name.strip()] = price_val
                    except:
                        pass
        
        return ram_dict
    except Exception as e:
        print(f"❌ 内存爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return {}

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
                    if "金百达 银爵 32G 16x2 3600 D4 C18" in model_name:
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
                                    if "金百达 银爵 32G 16x2 3600 D4 C18" in temp_name:
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
                                    if "金百达 银爵 32G 16x2 3600 D4 C18" in temp_name:
                                        ref_price_from_html = int(temp_match.group(2))
                                        print(f"     从HTML获取参考价格: 金百达_银爵 32G 3600(16*2)套装 海力士c18 = ￥{ref_price_from_html}")
                                        break
                            temp_pos += 1
                        
                        if ref_price_from_html > 0:
                            new_price = str(ref_price_from_html * 2)
                            print(f"  ★ 特殊更新：光威 天策 64G 白色 = 金百达_银爵(￥{ref_price_from_html}) × 2 = ￥{new_price}")
                        else:
                            print(f"  ⚠️ 光威 天策 64G 白色 缺少参考价格，跳过更新")
                    # 特殊处理：光威 天策 16G（8*2）3200 白色 = 阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲
                    elif "光威 天策 16G（8*2）3200 白色" in model_name:
                        print(f"  🔍 匹配到光威 天策 16G 白色，尝试从HTML获取参考价格")
                        ref_price_from_html = 0
                        temp_pos = 0
                        while temp_pos < len(lines):
                            temp_line = lines[temp_pos]
                            if '{n:"' in temp_line and '",p:' in temp_line:
                                temp_match = re.search(r'{n:"([^"]+)",p:(\d+)}', temp_line)
                                if temp_match:
                                    temp_name = temp_match.group(1)
                                    if "阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲" in temp_name:
                                        ref_price_from_html = int(temp_match.group(2))
                                        print(f"     从HTML获取参考价格: 阿斯加特 TUF联名 16G 8*2 3200 C18 黑橙甲 = ￥{ref_price_from_html}")
                                        break
                            temp_pos += 1

                        if ref_price_from_html > 0:
                            new_price = str(ref_price_from_html)
                            print(f"  ★ 特殊更新：光威 天策 16G 白色 = 阿斯加特 TUF联名(￥{ref_price_from_html}) = ￥{new_price}")
                        else:
                            print(f"  ⚠️ 光威 天策 16G 白色 缺少参考价格，跳过更新")
                    # 特殊处理：光威 天策 32G（16*2）3200 白色 = 阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲
                    elif "光威 天策 32G（16*2）3200 白色" in model_name:
                        print(f"  🔍 匹配到光威 天策 32G 白色，尝试从HTML获取参考价格")
                        ref_price_from_html = 0
                        temp_pos = 0
                        while temp_pos < len(lines):
                            temp_line = lines[temp_pos]
                            if '{n:"' in temp_line and '",p:' in temp_line:
                                temp_match = re.search(r'{n:"([^"]+)",p:(\d+)}', temp_line)
                                if temp_match:
                                    temp_name = temp_match.group(1)
                                    if "阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲" in temp_name:
                                        ref_price_from_html = int(temp_match.group(2))
                                        print(f"     从HTML获取参考价格: 阿斯加特 TUF联名 32G 16*2 3200 C18 黑甲 = ￥{ref_price_from_html}")
                                        break
                            temp_pos += 1

                        if ref_price_from_html > 0:
                            new_price = str(ref_price_from_html)
                            print(f"  ★ 特殊更新：光威 天策 32G 白色 = 阿斯加特 TUF联名(￥{ref_price_from_html}) = ￥{new_price}")
                        else:
                            print(f"  ⚠️ 光威 天策 32G 白色 缺少参考价格，跳过更新")
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
    """机箱更新逻辑：保留现有型号，只更新价格，不删除，新型号追加"""
    print("\n" + "="*50)
    print("🔄 开始机箱价格更新")
    print("="*50)
    
    try:
        # ========== 第一步：爬取源网站数据 ==========
        print("\n📥 第一步：爬取源网站数据...")
        case_list = fetch_case_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not case_list:
            print("⚠️ 机箱数据获取失败或为空，保留原有机箱数据")
            return
        
        # 将列表转换为字典，方便查找（保存完整信息包括图片URL）
        case_dict = {case["name"]: case for case in case_list}
        print(f"   爬取到 {len(case_dict)} 个机箱型号")
        
        # 打印部分爬取数据用于调试
        print("\n   📋 部分爬取数据:")
        for i, (name, case_info) in enumerate(list(case_dict.items())[:10]):
            print(f"      {name[:45]}... -> ￥{case_info['price']}")
        
        # ========== 第二步：读取HTML中的机箱数据 ==========
        print("\n📖 第二步：读取HTML机箱数据...")
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split('\n')
        
        # 找到机箱区域开始和结束位置
        case_start_idx = -1
        case_end_idx = -1
        for i, line in enumerate(lines):
            if 'case: [' in line:
                case_start_idx = i
            elif case_start_idx != -1 and case_end_idx == -1 and line.strip() == '],':
                # 确认是机箱数组的结束（机箱后面是注释或其他配件）
                if i + 1 < len(lines) and ('// 新增其他配件' in lines[i + 1] or 'fan: [' in lines[i + 1]):
                    case_end_idx = i
                    break
        
        if case_start_idx == -1 or case_end_idx == -1:
            print("❌ 未找到机箱区域")
            return
        
        print(f"   机箱区域：第{case_start_idx + 1}行 - 第{case_end_idx + 1}行")
        
        # 解析HTML中的机箱数据
        html_cases = {}  # {型号名: (价格, 行索引)}
        for i in range(case_start_idx + 1, case_end_idx):
            line = lines[i]
            match = re.search(r'{n:"([^"]+)",p:(\d+(?:\.\d+)?)}', line)
            if match:
                name = match.group(1)
                price = int(float(match.group(2)))
                html_cases[name] = (price, i)
        
        print(f"   HTML中有 {len(html_cases)} 个机箱型号")
        
        # ========== 第三步：比对并更新 ==========
        print("\n📝 第三步：比对并更新...")
        
        update_count = 0
        new_add_count = 0
        no_change_count = 0
        no_match_count = 0
        
        # 收集需要更新的数据
        updates = []  # [(行索引, 新的价格, 型号名, 旧价格)]
        new_items = []  # [(型号名, 价格)] - 需要追加的新型号
        matched_html = set()  # 已匹配的HTML型号
        matched_scraped = set()  # 已匹配的爬取型号
        
        # 定义需要加价的机箱型号及加价幅度
        CASE_MARKUP_MODELS = {
            "爱国者 炫影G10海景房 黑色": 50,
            "爱国者 炫影G10海景房 白色": 50,
        }
        
        # 精确匹配（机箱使用精确匹配，因为颜色版本价格不同，模糊匹配可能导致错误）
        for scraped_name, case_info in case_dict.items():
            scraped_price = case_info["price"]
            if scraped_name in html_cases:
                old_price, line_idx = html_cases[scraped_name]
                # 加价型号即使价格相同也需要更新（应用加价）
                if scraped_price != old_price or scraped_name in CASE_MARKUP_MODELS:
                    updates.append((line_idx, scraped_price, scraped_name, old_price))
                else:
                    no_change_count += 1
                matched_html.add(scraped_name)
                matched_scraped.add(scraped_name)
            else:
                # 尝试简单的空格/标点差异匹配
                scraped_name_clean = scraped_name.replace(' ', '').replace('_', '').replace('*', 'x').replace('（', '(').replace('）', ')')
                for html_name, (html_price, line_idx) in html_cases.items():
                    if html_name in matched_html:
                        continue
                    html_name_clean = html_name.replace(' ', '').replace('_', '').replace('*', 'x').replace('（', '(').replace('）', ')')
                    if scraped_name_clean == html_name_clean:
                        # 加价型号即使价格相同也需要更新
                        if scraped_price != html_price or html_name in CASE_MARKUP_MODELS:
                            updates.append((line_idx, scraped_price, scraped_name, html_price))
                            print(f"   🔗 格式匹配: {scraped_name[:35]}... ≈ {html_name[:35]}...")
                        else:
                            no_change_count += 1
                        matched_html.add(html_name)
                        matched_scraped.add(scraped_name)
                        break
        
        # 统计未匹配的HTML型号
        no_match_count = len(html_cases) - len(matched_html)
        
        # 执行更新
        for line_idx, new_price, name, old_price in updates:
            final_price = new_price
            if name in CASE_MARKUP_MODELS:
                markup = CASE_MARKUP_MODELS[name]
                final_price += markup
                print(f"   💰 加价: {name[:35]}... +{markup}元")
            lines[line_idx] = re.sub(r'p:\d+(?:\.\d+)?', f'p:{final_price}', lines[line_idx])
            print(f"   ✓ 更新: {name[:35]}... ￥{old_price} -> ￥{final_price}")
            update_count += 1
        
        # 追加新型号（只有确实没匹配上的才追加）
        for scraped_name, case_info in case_dict.items():
            if scraped_name not in matched_scraped:
                # 检查是否已经在HTML中（作为手动添加的型号）
                found_in_html = False
                for line in lines:
                    if f'{{n:"{scraped_name}"' in line:
                        found_in_html = True
                        break
                if not found_in_html:
                    price = case_info["price"]
                    image_url = case_info.get("image_url", "")
                    # 新型号也需要加价
                    if scraped_name in CASE_MARKUP_MODELS:
                        markup = CASE_MARKUP_MODELS[scraped_name]
                        price += markup
                        print(f"   💰 新型号加价: {scraped_name[:35]}... +{markup}元")
                    new_items.append((scraped_name, price, image_url))
        
        if new_items:
            print(f"\n   📌 追加 {len(new_items)} 个新型号:")
            new_lines = []
            for name, price in new_items:
                new_line = f'            {{n:"{name}",p:{price}}},'
                new_lines.append(new_line)
                print(f"   + 新增: {name[:40]}... ￥{price}")
                new_add_count += 1
            
            # 在机箱区域末尾追加
            lines[case_end_idx] = '\n'.join(new_lines) + '\n' + lines[case_end_idx]
        
        # ========== 第四步：保存文件 ==========
        print("\n💾 第四步：保存文件...")
        # 保存前验证行数是否合理（防止意外删除大量数据）
        original_line_count = len(lines)
        if original_line_count < 1000:
            print(f"⚠️ 异常：行数过少({original_line_count}行)，可能数据丢失，跳过保存")
            return
        
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        # 保存后验证文件完整性
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证机箱区域是否完整
        if 'case: [' not in content or '],' not in content:
            print("❌ 验证失败：机箱区域标记丢失！")
            return
        
        print("   ✅ 文件验证通过")
        
        # 自动添加图片映射
        add_image_mappings(new_items, 'case')
        
        # ========== 输出统计 ==========
        print("\n" + "="*50)
        print(f"📊 更新统计:")
        print(f"   - 价格更新: {update_count} 个型号")
        print(f"   - 新型号追加: {new_add_count} 个型号")
        print(f"   - 价格不变: {no_change_count} 个型号")
        print(f"   - 未匹配(保留): {no_match_count} 个型号")
        print("="*50)
        print("✅ 机箱更新完成!")
        
    except Exception as e:
        print(f"❌ 机箱更新失败：{e}")
        import traceback
        traceback.print_exc()

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
    """散热器更新逻辑：保留现有型号，只更新价格，不删除，新型号追加"""
    print("\n" + "="*50)
    print("🔄 开始散热器价格更新")
    print("="*50)
    
    try:
        # ========== 第一步：爬取源网站数据 ==========
        print("\n📥 第一步：爬取源网站数据...")
        cooler_list = fetch_cooler_prices()
        
        # 如果获取失败或返回空列表，不删除原有数据，直接返回
        if not cooler_list:
            print("⚠️ 散热器数据获取失败或为空，保留原有散热器数据")
            return
        
        # 将列表转换为字典，方便查找
        cooler_dict = {cooler["name"]: cooler for cooler in cooler_list}
        print(f"   爬取到 {len(cooler_dict)} 个散热器型号")
        
        # 打印部分爬取数据用于调试
        print("\n   📋 部分爬取数据:")
        for i, (name, cooler_info) in enumerate(list(cooler_dict.items())[:10]):
            print(f"      {name[:45]}... -> ￥{cooler_info['price']}")
        
        # ========== 第二步：读取HTML中的散热器数据 ==========
        print("\n📖 第二步：读取HTML散热器数据...")
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split('\n')
        
        # 找到散热器区域开始和结束位置
        cooler_start_idx = -1
        cooler_end_idx = -1
        for i, line in enumerate(lines):
            if 'cooler: [' in line:
                cooler_start_idx = i
            elif cooler_start_idx != -1 and cooler_end_idx == -1 and line.strip() == '],':
                # 确认是散热器数组的结束（散热器后面是fan）
                if i + 1 < len(lines) and 'fan: [' in lines[i + 1]:
                    cooler_end_idx = i
                    break
        
        if cooler_start_idx == -1 or cooler_end_idx == -1:
            print("❌ 未找到散热器区域")
            return
        
        print(f"   散热器区域：第{cooler_start_idx + 1}行 - 第{cooler_end_idx + 1}行")
        
        # 解析HTML中的散热器数据
        html_coolers = {}  # {型号名: (价格, 行索引)}
        for i in range(cooler_start_idx + 1, cooler_end_idx):
            line = lines[i]
            match = re.search(r'{n:"([^"]+)",p:(\d+(?:\.\d+)?)}', line)
            if match:
                name = match.group(1)
                price = int(float(match.group(2)))
                html_coolers[name] = (price, i)
        
        print(f"   HTML中有 {len(html_coolers)} 个散热器型号")
        
        # ========== 第三步：比对并更新 ==========
        print("\n📝 第三步：比对并更新...")
        
        update_count = 0
        new_add_count = 0
        no_change_count = 0
        no_match_count = 0
        
        # 收集需要更新的数据
        updates = []  # [(行索引, 新的价格, 型号名, 旧价格)]
        new_items = []  # [(型号名, 价格)] - 需要追加的新型号
        matched_html = set()  # 已匹配的HTML型号
        matched_scraped = set()  # 已匹配的爬取型号
        
        # 精确匹配
        for scraped_name, cooler_info in cooler_dict.items():
            scraped_price = cooler_info["price"]
            if scraped_name in html_coolers:
                old_price, line_idx = html_coolers[scraped_name]
                if scraped_price != old_price:
                    updates.append((line_idx, scraped_price, scraped_name, old_price))
                else:
                    no_change_count += 1
                matched_html.add(scraped_name)
                matched_scraped.add(scraped_name)
        
        # 型号关键字匹配（移除品牌名称）
        def normalize_model(model):
            """标准化型号名称，便于模糊匹配"""
            # 移除空格、下划线、连字符、特殊字符，转为小写
            n = model.replace(' ', '').replace('_', '').replace('-', '').replace('(', '').replace(')', '')
            n = n.replace('ARGB', 'RGB').replace('RGB', '')
            return n.lower()
        
        for scraped_name, cooler_info in cooler_dict.items():
            if scraped_name in matched_scraped:
                continue
            
            scraped_price = cooler_info["price"]
            
            # 移除品牌名称，只保留型号部分
            scraped_model = scraped_name
            for brand in COOLER_BRANDS:
                if brand in scraped_name:
                    scraped_model = scraped_name.replace(brand, "").strip()
                    break
            
            # 型号太短不进行匹配，避免误匹配（至少5个字符）
            if len(scraped_model) < 5:
                continue
            
            # 标准化型号
            scraped_norm = normalize_model(scraped_model)
            
            for html_name, (html_price, line_idx) in html_coolers.items():
                if html_name in matched_html:
                    continue
                
                # 移除品牌名称
                html_model = html_name
                for brand in COOLER_BRANDS:
                    if brand in html_name:
                        html_model = html_name.replace(brand, "").strip()
                        break
                
                # 标准化型号
                html_norm = normalize_model(html_model)
                
                # 精确匹配或标准化匹配
                if scraped_model == html_model or scraped_norm == html_norm:
                    if scraped_price != html_price:
                        updates.append((line_idx, scraped_price, scraped_name, html_price))
                        print(f"   🔗 型号匹配: {scraped_name[:35]}... ≈ {html_name[:35]}...")
                    else:
                        no_change_count += 1
                    matched_html.add(html_name)
                    matched_scraped.add(scraped_name)
                    break
        
        # 统计未匹配的HTML型号
        no_match_count = len(html_coolers) - len(matched_html)
        
        # 执行更新
        for line_idx, new_price, name, old_price in updates:
            lines[line_idx] = re.sub(r'p:\d+(?:\.\d+)?', f'p:{new_price}', lines[line_idx])
            print(f"   ✓ 更新: {name[:35]}... ￥{old_price} -> ￥{new_price}")
            update_count += 1
        
        # 追加新型号（只有确实没匹配上的才追加）
        for scraped_name, cooler_info in cooler_dict.items():
            if scraped_name not in matched_scraped:
                # 检查是否已经在HTML中（作为手动添加的型号）
                found_in_html = False
                for line in lines:
                    if f'{{n:"{scraped_name}"' in line:
                        found_in_html = True
                        break
                if not found_in_html:
                    price = cooler_info["price"]
                    image_url = cooler_info.get("image_url", "")
                    new_items.append((scraped_name, price, image_url))
        
        if new_items:
            print(f"\n   📌 追加 {len(new_items)} 个新型号:")
            new_lines = []
            for name, price in new_items:
                new_line = f'            {{n:"{name}",p:{price}}},'
                new_lines.append(new_line)
                print(f"   + 新增: {name[:40]}... ￥{price}")
                new_add_count += 1
            
            # 在散热器区域末尾追加
            lines[cooler_end_idx] = '\n'.join(new_lines) + '\n' + lines[cooler_end_idx]
        
        # ========== 第四步：保存文件 ==========
        print("\n💾 第四步：保存文件...")
        # 保存前验证行数是否合理（防止意外删除大量数据）
        original_line_count = len(lines)
        if original_line_count < 1000:
            print(f"⚠️ 异常：行数过少({original_line_count}行)，可能数据丢失，跳过保存")
            return
        
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        # 保存后验证文件完整性
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证散热器区域是否完整
        if 'cooler: [' not in content or '],' not in content:
            print("❌ 验证失败：散热器区域标记丢失！")
            return
        
        print("   ✅ 文件验证通过")
        
        # 自动添加图片映射
        add_image_mappings(new_items, 'cooler')
        
        # ========== 输出统计 ==========
        print("\n" + "="*50)
        print(f"📊 更新统计:")
        print(f"   - 价格更新: {update_count} 个型号")
        print(f"   - 新型号追加: {new_add_count} 个型号")
        print(f"   - 价格不变: {no_change_count} 个型号")
        print(f"   - 未匹配(保留): {no_match_count} 个型号")
        print("="*50)
        print("✅ 散热器更新完成!")
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
    
    # Intel Ultra型号（支持 "ultra" 或 "酷睿u" 两种格式）
    ultra_pattern = r'(?:ultra|酷睿u)(\d+)([a-z0-9]*)'
    ultra_match = re.search(ultra_pattern, text_lower)
    if ultra_match:
        return f"ultra{ultra_match.group(1)}{ultra_match.group(2)}"
    
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
    
    # 判断HTML中的包装类型
    html_has_retail = "散" in name
    html_has_box = "盒" in name
    
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
        
        # 如果HTML明确要求散片，但源网站是纯盒装，跳过
        if html_has_retail and source_has_box and not source_has_retail:
            print(f"     ✗ 跳过: 需要散片，但源网站是盒装")
            continue
        # 如果HTML明确要求盒装，但源网站是纯散片，跳过
        if html_has_box and source_has_retail and not source_has_box:
            print(f"     ✗ 跳过: 需要盒装，但源网站是散片")
            continue
        # 如果HTML既没有散也没有盒，则接受任何包装类型
        
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
    # 显卡更新
    update_gpu_prices()
    # 内存更新（使用新的匹配逻辑，仿照显卡更新）
    update_ram_prices_new()
    # 内存定制价格更新（处理金百达等特殊品牌，保留旧逻辑作为补充）
    update_exist_ram_prices()
    update_ssd_prices()
    update_mb_accurate()
    # 机箱更新
    update_case_accurate()
    # 新增执行电源更新
    update_power_accurate()
    # 新增执行散热器更新
    update_cooler_accurate()
    
    print("===== 全部执行完成 =====")


def add_image_mappings(new_items, mapping_type):
    """
    自动添加图片映射
    :param new_items: 新添加的配件列表，格式为 [(名称, 价格, 图片URL), ...]
    :param mapping_type: 映射类型，'case'、'cooler'、'vga'
    """
    if not new_items:
        print(f"\n📷 {mapping_type}图片映射：无新型号需要添加")
        return
    
    print(f"\n📷 自动添加{mapping_type}图片映射...")
    print(f"   待处理新型号数量: {len(new_items)}")
    
    # 确定映射表名称和位置
    mapping_names = {
        'case': 'caseImageMap',
        'cooler': 'coolerImageMap',
        'vga': 'vgaImageMap'
    }
    
    mapping_name = mapping_names.get(mapping_type)
    if not mapping_name:
        print(f"❌ 未知映射类型: {mapping_type}")
        return
    
    # 读取HTML文件
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split('\n')
    
    # 找到映射表的位置
    map_start_idx = -1
    map_end_idx = -1
    
    for i, line in enumerate(lines):
        if f'const {mapping_name} = {{' in line:
            map_start_idx = i
            print(f"   找到映射表开始位置: 第 {i+1} 行")
        elif map_start_idx != -1 and map_end_idx == -1 and line.strip() == '};':
            map_end_idx = i
            print(f"   找到映射表结束位置: 第 {i+1} 行")
            break
    
    if map_start_idx == -1 or map_end_idx == -1:
        print(f"❌ 未找到{mapping_name}映射表 (start={map_start_idx}, end={map_end_idx})")
        return
    
    print(f"   映射表范围: 第 {map_start_idx+1} 行 - 第 {map_end_idx+1} 行")
    
    # 解析现有映射
    existing_keys = set()
    for i in range(map_start_idx + 1, map_end_idx):
        line = lines[i]
        match = re.search(r"'([^']+)':", line)
        if match:
            existing_keys.add(match.group(1))
    
    # 添加新映射
    added_count = 0
    new_mappings = []
    
    for name, _ in new_items:
        if name not in existing_keys:
            # 转义单引号，避免JavaScript语法错误
            escaped_name = name.replace("'", "\\'")
            # 图片名称与配件名称一致
            new_mappings.append(f"        '{escaped_name}': '{escaped_name}',")
            print(f"   + 添加映射: '{name}' -> '{name}'")
            added_count += 1
    
    # 在映射表末尾添加新映射
    if new_mappings:
        lines[map_end_idx] = '\n'.join(new_mappings) + '\n' + lines[map_end_idx]
        
        # 保存前验证行数是否合理
        if len(lines) < 1000:
            print(f"⚠️ 异常：行数过少({len(lines)}行)，可能数据丢失，跳过保存")
            return
        
        # 保存文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        # 保存后验证文件完整性
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证映射表是否完整
        if f'const {mapping_name} = {{' not in content or '};' not in content:
            print(f"❌ 验证失败：{mapping_name}映射表标记丢失！")
            return
        
        print(f"✅ 成功添加 {added_count} 个{mapping_type}图片映射")
        
        # 自动下载新添加配件的图片
        download_images(new_items, mapping_type)
    else:
        print("   无需添加新映射")


def download_images(new_items, mapping_type):
    """
    自动下载新添加配件的图片并重命名
    :param new_items: 新添加的配件列表，格式为 [(名称, 价格, 图片URL), ...]
    :param mapping_type: 映射类型，'case'、'cooler'、'vga'
    """
    import os
    
    # 确定图片保存目录
    save_dirs = {
        'case': 'tas1985.github.io/PNG',
        'cooler': 'tas1985.github.io/PNG_SR',
        'vga': 'tas1985.github.io/PNG_VGA'
    }
    
    save_dir = save_dirs.get(mapping_type)
    if not save_dir:
        print(f"❌ 未知映射类型: {mapping_type}")
        return
    
    # 创建目录（如果不存在）
    os.makedirs(save_dir, exist_ok=True)
    
    downloaded_count = 0
    skipped_count = 0
    
    for item in new_items:
        if len(item) >= 3:
            name, _, img_url = item[0], item[1], item[2]
        else:
            name = item[0]
            img_url = ""
        
        if not img_url:
            print(f"   ⚠️ 无图片URL: {name}")
            skipped_count += 1
            continue
        
        # 构建完整的图片URL
        if not img_url.startswith('http'):
            img_url = 'https://0532.name' + img_url
        
        # 构建保存文件名（图片名称与配件名称一致）
        safe_name = name.replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_')
        safe_name = safe_name.replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        filename = f"{safe_name}.png"
        filepath = os.path.join(save_dir, filename)
        
        # 检查文件是否已存在
        if os.path.exists(filepath):
            print(f"   ≡ 图片已存在: {filename}")
            skipped_count += 1
            continue
        
        try:
            # 下载图片
            print(f"   📥 下载图片: {img_url} -> {filename}")
            response = requests.get(img_url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            
            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            downloaded_count += 1
            print(f"   ✅ 图片保存成功: {filename}")
        except Exception as e:
            print(f"   ❌ 图片下载失败: {name} - {e}")
            skipped_count += 1
    
    print(f"   📊 图片下载完成：成功 {downloaded_count} 个，跳过 {skipped_count} 个")
