import requests
from bs4 import BeautifulSoup
import datetime

# 目标抓取地址
URL = "http://0532.name/cpu_list"
# 输出到网站的文件路径
OUTPUT_FILE = "index.html"

def get_cpu_prices():
    """抓取CPU实时价格"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 提取页面所有文本（适配目标网站结构）
        content = soup.get_text(separator="\n", strip=True)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>CPU实时价格 - 每日自动更新</title>
            <style>
                body {{ font-family: Arial; margin: 30px; line-height: 1.6; }}
                .time {{ color: #666; font-size: 14px; }}
                pre {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <h1>CPU 实时价格列表</h1>
            <p class="time">更新时间：{now}</p>
            <pre>{content}</pre>
        </body>
        </html>
        """
    except Exception as e:
        return f"抓取失败：{str(e)}"

if __name__ == "__main__":
    html_content = get_cpu_prices()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ 价格已成功更新到网站页面！")