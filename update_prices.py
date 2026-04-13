import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 全局配置项（完全不变） --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
GPU_SOURCE_URL = "http://0532.name/cpu_list?category=%E6%98%BE%E5%8D%A1"
MB_SOURCE_URL = "http://0532.name/cpu_list?category=%E4%B8%BB%E6%9D%BF"
RAM_SOURCE_URL = "http://0532.name/cpu_list?category=%E5%86%85%E5%AD%98"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36"}

# 显卡/主板/内存 配置（完全不变）
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
def extract_hardware_model(name):  # CPU专用，保留不变
    if not name: return ""
    name = re.sub(r'[{n:"\",}]', '', name).lower().replace(" ", "").replace("-", "")
    pattern = re.compile(r'(i[3579]\d+[a-z0-9]*)|(r[3579]\d+[a-z0-9]*)|(rtx\d+[a-z0-9]*)|(gtx\d+[a-z0-9]*)|(amd\d+[a-z0-9]*)|(\d+gb)|(\d+[a-z]+\d*)')
    match = pattern.search(name)
    return match.group() if match else name

# 【新增·核心】内存专用：提取 品牌+容量+频率 精准特征（金百达+16G+3200）
def extract_ram_feature(name):
    # 1. 提取品牌（中文品牌名）
    brand_pattern = r"(金百达|宏碁掠夺者|阿斯加特|芝奇|海盗船|金士顿|威刚|三星|科赋|光威)"
    brand = re.search(brand_pattern, name)
    brand = brand.group() if brand else ""
    
    # 2. 提取容量（xxG）
    capacity = re.search(r"\d+G", name)
    capacity = capacity.group() if capacity else ""
    
    # 3. 提取频率（纯数字，3200/6000/5600等）
    freq = re.search(r"\d{4,5}", name)
    freq = freq.group() if freq else ""
    
    # 组合唯一特征：品牌_容量_频率
    return f"{brand}_{capacity}_{freq}".strip("_")

# -------------------------- 爬取函数（完全不变） --------------------------
def fetch_latest_prices():
    try:
        res = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        price_dict = {extract_hardware_model(n):p for n,p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text())}
        return price_dict
    except: return {}

def fetch_gpu_prices():
    try:
        res = requests.get(GPU_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return [{"name":n,"price":p} for n,p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text())]
    except: return []

def fetch_mb_prices():
    try:
        res = requests.get(MB_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return [{"name":n,"price":p} for n,p in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()) if MB_EXCLUDE not in n]
    except: return []

def fetch_raw_ram_prices():
    """爬取原始内存数据，生成【特征:价格】字典（用于精准匹配更新）"""
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ram_dict = {}
        for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            feat = extract_ram_feature(name)
            if feat: ram_dict[feat] = price
        return ram_dict
    except: return {}

def fetch_processed_ram():
    try:
        res = requests.get(RAM_SOURCE_URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        ram_list = []
        for name, price in re.findall(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)", soup.get_text()):
            if any(w in name for w in RAM_EXCLUDE_LIST): continue
            final_p = str(float(price)+RAM_ASC_TECH_ADD) if "阿斯加特" in name else price
            ram_list.append({"name":name,"price":final_p})
        return ram_list
    except: return []

# -------------------------- 生成格式函数（完全不变） --------------------------
def generate_gpu_content(gpu_list): return "".join([f"{GPU_START_MARK}\n", *[f'{INDENT}{{n:"{g["name"]}",p:{g["price"]}}},\n' for g in gpu_list], f"{GPU_END_MARK}\n"])
def generate_mb_content(mb_list): return "".join([f'{INDENT}{{n:"{m["name"]}",p:{m["price"]}}},\n' for m in mb_list])
def generate_ram_content(ram_list): return "".join([f'{INDENT}{{n:"{r["name"]}",p:{r["price"]}}},\n' for r in ram_list])

# -------------------------- 更新函数 --------------------------
def update_html_prices(price_dict):  # CPU更新，保留不变
    try:
        with open(HTML_FILE,"r",encoding="utf-8") as f: lines = f.readlines()
        cnt=0
        for i in range(START_LINE, END_LINE+1):
            if i>=len(lines): break
            if not re.search(r"p:\d+(?:\.\d+)?", lines[i]): continue
            name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", lines[i]).strip()
            new_p = fuzzy_match_price(name, price_dict)
            if new_p:
                lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_p}", lines[i])
                cnt+=1
        with open(HTML_FILE,"w",encoding="utf-8") as f: f.writelines(lines)
        return cnt
    except: return 0

# 【修复·核心】按「品牌+容量+频率」精准更新现有内存
def update_exist_ram_prices():
    try:
        with open(HTML_FILE,"r",encoding="utf-8") as f: lines = f.readlines()
        ram_dict = fetch_raw_ram_prices()
        # 定位内存范围
        start = end = -1
        for i, line in enumerate(lines):
            if start == -1 and RAM_EXIST_START in line: start = i
            if RAM_EXIST_END in line: end = i
        if start == -1 or end == -1: print("❌ 未找到内存范围"); return 0

        cnt=0
        for i in range(start, end+1):
            line = lines[i]
            if not re.search(r"p:\d+(?:\.\d+)?", line): continue
            # 提取当前内存的精准特征
            ram_name = re.sub(r'<[^>]+>|p:\d+(?:\.\d+)?', "", line).strip()
            feat = extract_ram_feature(ram_name)
            if feat not in ram_dict: continue

            # 匹配价格 + 阿斯加特加价
            price = ram_dict[feat]
            new_p = str(float(price)+RAM_ASC_TECH_ADD) if "阿斯加特" in ram_name else price
            lines[i] = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_p}", line)
            cnt+=1
            print(f"✅ 精准匹配：{feat} | 新价格：{new_p}")

        with open(HTML_FILE,"w",encoding="utf-8") as f: f.writelines(lines)
        print(f"🎉 内存更新完成：{cnt} 个")
        return cnt
    except Exception as e:
        print(f"❌ 内存更新失败：{e}")
        return 0

# 显卡/主板/内存 插入更新（完全不变）
def update_gpu_by_mark():
    try:
        with open(HTML_FILE,"r",encoding="utf-8") as f: content = f.read()
        new_cont = generate_gpu_content(fetch_gpu_prices())
        final = re.sub(re.escape(GPU_START_MARK)+r".*?"+re.escape(GPU_END_MARK), new_cont.strip(), content, flags=re.DOTALL)
        with open(HTML_FILE,"w",encoding="utf-8") as f: f.write(final)
    except: pass

def update_mb_accurate():
    try:
        with open(HTML_FILE,"r",encoding="utf-8") as f: lines = f.readlines()
        idx = next((i for i,l in enumerate(lines) if MB_TARGET_LINE in l), -1)
        if idx==-1: return
        pos = idx+1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]: del lines[pos]
        lines.insert(pos, generate_mb_content(fetch_mb_prices()))
        with open(HTML_FILE,"w",encoding="utf-8") as f: f.writelines(lines)
    except: pass

def update_ram_accurate():
    try:
        with open(HTML_FILE,"r",encoding="utf-8") as f: lines = f.readlines()
        idx = next((i for i,l in enumerate(lines) if RAM_INSERT_TARGET in l), -1)
        if idx==-1: return
        pos = idx+1
        while pos < len(lines) and lines[pos].startswith(INDENT) and '{n:"' in lines[pos]: del lines[pos]
        lines.insert(pos, generate_ram_content(fetch_processed_ram()))
        with open(HTML_FILE,"w",encoding="utf-8") as f: f.writelines(lines)
    except: pass

# CPU双加价逻辑（完全不变）
def fuzzy_match_price(name, price_dict):
    if not price_dict: return None
    model = extract_hardware_model(name)
    best, score = process.extractOne(model, price_dict.keys())
    if score < MATCH_THRESHOLD: return None
    p = price_dict[best]
    if model == "r55600": return str(float(p)+50)
    if "R5-5500X3D" in name or model == "r55500x3d": return str(float(p)+39)
    return p

# -------------------------- 主函数（完全不变） --------------------------
if __name__ == "__main__":
    print("===== 内存精准匹配修复版 =====")
    cpu_prices = fetch_latest_prices()
    if cpu_prices: update_html_prices(cpu_prices)
    update_exist_ram_prices()   # 精准匹配更新内存
    update_gpu_by_mark()
    update_mb_accurate()
    update_ram_accurate()
    print("===== 全部执行完成 =====")
