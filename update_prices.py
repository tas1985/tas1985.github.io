import re
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process

# -------------------------- 配置项 --------------------------
SOURCE_URL = "http://0532.name/cpu_list"
HTML_FILE = "index.html"
START_LINE = 760
END_LINE = 816
MATCH_THRESHOLD = 60  # 纯型号匹配，极低阈值也能精准命中
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# -------------------------- 【核心】提取硬件纯型号（绝杀功能） --------------------------
def extract_hardware_model(name):
    """
    自动提取CPU/显卡/硬件核心型号，删除所有参数、描述、主频、核心数
    例：i5-14600KF 3.5G 十四核 → 直接提取 i514600kf
    """
    if not name:
        return ""
    
    # 1. 清理所有代码符号：{n:"  "} 等无用字符
    name = re.sub(r'[{n:"\",}]', '', name)
    
    # 2. 统一小写 + 移除空格/横杠
    name = name.lower().replace(" ", "").replace("-", "")
    
    # 3. 【核心正则】匹配 Intel/AMD/英伟达 所有主流型号
    # 匹配：i3/i5/i7/i9、r3/r5/r7/r9、rtx/gtx、12400f/4060/7800x等纯型号
    pattern = re.compile(
        r'(i[3579]\d+[a-z0-9]*)|'          # Intel CPU: i514600kf
        r'(r[3579]\d+[a-z0-9]*)|'          # AMD CPU: r77800x
        r'(rtx\d+[a-z0-9]*)|'              # 英伟达显卡: rtx4060
        r'(gtx\d+[a-z0-9]*)|'              # 老显卡: gtx1660
        r'(amd\d+[a-z0-9]*)|'              # AMD显卡
        r'(\d+gb)|'                        # 内存/硬盘容量
        r'(\d+[a-z]+\d*)'                  # 其他硬件型号
    )
    
    match = pattern.search(name)
    if match:
        # 返回匹配到的纯型号
        return [m for m in match.groups() if m][0]
    
    # 无匹配则返回清理后的名称
    return name

# -------------------------- 1. 爬取价格（提取纯型号） --------------------------
def fetch_latest_prices():
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n").strip()
        price_dict = {}

        # 匹配名称+价格
        pattern = re.compile(r"([^\n￥]+?)[：\s]*￥(\d+(?:\.\d+)?)")
        matches = pattern.findall(text)

        for name, price in matches:
            # 提取源站纯型号
            model = extract_hardware_model(name)
            if model:
                price_dict[model] = price
                print(f"源站：{name} → 纯型号：{model} | 价格：{price}")

        print(f"\n✅ 成功爬取 {len(price_dict)} 个配件")
        return price_dict

    except Exception as e:
        print(f"❌ 爬取失败：{str(e)}")
        return {}

# -------------------------- 2. 纯型号精准匹配 --------------------------
def fuzzy_match_price(target_name, price_dict):
    if not price_dict:
        return None

    # 提取HTML配件的纯型号
    target_model = extract_hardware_model(target_name)
    print(f"\n┌── HTML原始：{target_name}")
    print(f"└── 提取纯型号：{target_model}")

    # 最强乱序/部分匹配算法
    best_match, score = process.extractOne(
        target_model,
        price_dict.keys(),
        scorer=process.fuzz.token_set_ratio
    )

    if score >= MATCH_THRESHOLD:
        print(f"✅ 匹配成功：{best_match} (相似度:{score}%)")
        return price_dict[best_match]
    else:
        print(f"❌ 匹配失败：保留原价")
        return None

# -------------------------- 3. 更新HTML --------------------------
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

            # 提取配件名称
            item_name = re.sub(r"<[^>]+>|p:\d+(?:\.\d+)?", "", line).strip()
            if not item_name:
                continue

            # 匹配并替换价格
            new_price = fuzzy_match_price(item_name, price_dict)
            if new_price:
                new_line = re.sub(r"p:\d+(?:\.\d+)?", f"p:{new_price}", line)
                lines[i] = new_line
                update_count += 1

        # 保存文件
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"\n🎉 更新完成！成功更新 {update_count} 个配件价格！")

    except Exception as e:
        print(f"❌ 修改失败：{str(e)}")

# -------------------------- 主函数 --------------------------
if __name__ == "__main__":
    print("===== 硬件纯型号匹配版 - 价格自动更新 =====")
    prices = fetch_latest_prices()
    if prices:
        update_html_prices(prices)
    print("===== 执行结束 =====")
