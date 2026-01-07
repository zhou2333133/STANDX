"""
打开GRVT和Variational交易所交易对页面
使用morelogin环境ID管理浏览器配置
"""

import sys
import os
import yaml
import argparse
import requests
from playwright.sync_api import sync_playwright


def start(env_id):
    """启动浏览器配置文件，返回 CDP URL"""
    response = requests.post("http://localhost:40000/api/env/start", 
                            json={"envId": env_id}).json()
    if response.get("code") != 0:
        print(f"启动失败: {response.get('msg', '')}")
        return None
    return f"http://127.0.0.1:{response['data']['debugPort']}"


def get_url(symbol, platform="grvt"):
    """根据交易对和平台生成URL"""
    symbol = symbol.upper()
    urls = {
        "grvt": f"https://grvt.io/exchange/perpetual/{symbol}-USDT",
        "var": f"https://omni.variational.io/perpetual/{symbol}",
        "variational": f"https://omni.variational.io/perpetual/{symbol}"
    }
    return urls.get(platform) or urls.get("grvt")


def normalize_url(url):
    """标准化URL用于比较"""
    return url.split('?')[0].split('#')[0].rstrip('/')


def open_page(playwright, env_id, url, platform_name=""):
    """
    打开指定环境并访问页面，返回页面对象
    如果页面已经打开，会复用已打开的页面
    关闭该环境中的其他所有页面
    """
    cdp_url = start(env_id)
    if cdp_url is None:
        return None
    
    try:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        ctx = browser.contexts[0]
        url_main = normalize_url(url)
        target_page = None
        
        # 检查是否已有匹配的页面
        for page in ctx.pages:
            try:
                if url_main in normalize_url(page.url):
                    target_page = page
                    if page.url != url:
                        page.goto(url, timeout=120000, wait_until="domcontentloaded")
                    break
            except:
                continue
        
        # 如果没有找到匹配的页面，创建新页面
        if target_page is None:
            target_page = ctx.new_page()
            target_page.goto(url, timeout=120000, wait_until="domcontentloaded")
        
        # 关闭其他所有页面
        for page in ctx.pages:
            if page != target_page:
                try:
                    page.close()
                except:
                    pass
        
        return target_page
    except Exception as e:
        print(f"打开页面失败 ({platform_name}): {e}")
        return None


def load_config(yaml_file="config.yaml"):
    """从YAML文件加载配置"""
    # 如果提供的是相对路径，则基于脚本所在目录查找
    if not os.path.isabs(yaml_file):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        yaml_file = os.path.join(script_dir, yaml_file)
    
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"错误: 配置文件 {yaml_file} 不存在")
        return None
    except yaml.YAMLError as e:
        print(f"错误: 解析YAML文件失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='打开GRVT和Variational交易所交易对页面')
    parser.add_argument('-c', '--config', type=str, default='config.yaml',
                       help='指定配置文件路径（默认: config.yaml）')
    args = parser.parse_args()
    
    config = load_config(args.config)
    if not config:
        print(f"错误: 无法加载配置文件 {args.config}")
        sys.exit(1)
    
    grvt_env_id = config.get('grvt_env_id', '')
    var_env_id = config.get('var_env_id', '')
    symbol = config.get('symbol', 'BTC')
    
    if not grvt_env_id or not var_env_id:
        print("错误: 配置文件中缺少必要的环境ID")
        sys.exit(1)
    
    # 配置页面信息
    pages_config = [
        ('grvt', grvt_env_id, get_url(symbol, "grvt")),
        ('var', var_env_id, get_url(symbol, "var"))
    ]
    
    with sync_playwright() as playwright:
        pages = {}
        for name, env_id, url in pages_config:
            page = open_page(playwright, env_id, url, name)
            if page:
                pages[name] = page
                print(f"✓ {name.upper()} 页面已打开")
        
        if not pages:
            print("错误: 所有页面打开失败")
            sys.exit(1)
        
        print(f"\n交易对: {symbol} | 已打开 {len(pages)} 个页面")
        print("按 Ctrl+C 退出")
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序已退出")


if __name__ == "__main__":
    main()
