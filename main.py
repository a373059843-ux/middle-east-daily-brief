"""
main.py — 中东新闻仪表盘入口
    python main.py --fetch         # 仅抓取今日 RSS
    python main.py --serve         # 启动 HTTP 服务 + 定时调度
    python main.py --fetch --serve # 抓取后启动服务
"""
import argparse
import http.server
import os
import sys
import time
import threading
import webbrowser
from datetime import date

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HTTP_PORT, MAX_ARTICLE_AGE_HOURS, SCHEDULE_TIMES
from fetcher import fetch_all
from storage import save_digest, cleanup_old
from generator import generate


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


# ==== 抓取+生成流程 ====
def run_fetch():
    today = date.today()
    print(f"\n{'='*50}")
    print(f"[{today}] 开始抓取中东新闻 (仅保留最近 {MAX_ARTICLE_AGE_HOURS} 小时)...")
    articles = fetch_all()
    save_digest(today, articles)
    generate(today)
    cleanup_old()
    print(f"[DONE] 本次收录 {len(articles)} 篇文章\n")


# ==== 调度线程 ====
def _scheduler_loop():
    import schedule as schedule_lib

    for t in SCHEDULE_TIMES:
        schedule_lib.every().day.at(t).do(run_fetch)
        print(f"[SCHEDULE] 已注册定时任务: 每天 {t}")

    while True:
        schedule_lib.run_pending()
        time.sleep(30)


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()


# ==== HTTP 服务器 ====
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def do_GET(self):
        # 根路径重定向到 /index.html
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return
        # 支持日期查询参数，映射到对应日期的 HTML
        if self.path.startswith("/?date="):
            qs = self.path.split("?date=", 1)[1].split("&")[0]
            try:
                d = date.fromisoformat(qs)
                generate(d)
                self.send_response(301)
                self.send_header("Location", "/index.html")
                self.end_headers()
                return
            except ValueError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid date format. Use YYYY-MM-DD.")
                return
        # 日期端点（REST 风格）：/date/YYYY-MM-DD
        if self.path.startswith("/date/") and self.path.endswith(".html"):
            date_str = self.path[6:-5]
            try:
                d = date.fromisoformat(date_str)
                generate(d)
                self.send_response(301)
                self.send_header("Location", "/index.html")
                self.end_headers()
                return
            except ValueError:
                self.send_error(400)
                return
        super().do_GET()

    def log_message(self, fmt, *args):
        print(f"[HTTP] {args[0]}")


def start_server():
    server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), CustomHandler)
    url = f"http://localhost:{HTTP_PORT}"
    print(f"[HTTP] 仪表盘服务已启动 → {url}")
    print(f"[HTTP] 按 Ctrl+C 停止服务")
    # 自动打开浏览器
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HTTP] 服务已停止")


# ==== 主入口 ====
def main():
    parser = argparse.ArgumentParser(description="Middle East Daily Brief Dashboard")
    parser.add_argument("--fetch", action="store_true", help="立即抓取 RSS 新闻")
    parser.add_argument("--serve", action="store_true", help="启动 HTTP 仪表盘服务")
    parser.add_argument("--port", type=int, default=HTTP_PORT, help=f"HTTP 端口 (默认: {HTTP_PORT})")
    parser.add_argument("--date", type=str, help="指定日期 YYYY-MM-DD (与 --fetch 结合使用)")
    args = parser.parse_args()

    # 修改全局端口
    if args.port != HTTP_PORT:
        import config
        config.HTTP_PORT = args.port

    if args.date:
        d = date.fromisoformat(args.date)
    else:
        d = date.today()

    if args.fetch:
        if args.date:
            print(f"[INFO] 抓取指定日期: {d}")
        run_fetch()
        # 如果指定了历史日期则生成指定日期的仪表盘，否则已通过 run_fetch 生成今天的
        if args.date and args.date != date.today().isoformat():
            generate(d)

    if args.serve:
        # 确保生成当天的仪表盘
        generate(d)
        start_scheduler()
        start_server()
    elif not args.fetch:
        # 无任何参数时显示帮助
        parser.print_help()
        print("\n示例:")
        print("  python main.py --fetch           # 抓取今日新闻并生成仪表盘")
        print("  python main.py --serve           # 启动服务 & 定时抓取")
        print("  python main.py --fetch --serve   # 抓取 + 启动服务")
        print("  python main.py --date 2026-06-01 --fetch  # 补抓指定日期")


if __name__ == "__main__":
    main()
