# -*- coding: utf-8 -*-
"""
鲁信环境 · 企业制度门户 —— 前端静态服务
仅托管 HTML/CSS/JS/图片，数据一律通过 AJAX 请求后端 API。

启动：  python3 serve.py
访问：  http://127.0.0.1:3000
后台：  http://127.0.0.1:3000/#/admin

环境变量：
  HOST  默认 127.0.0.1
  PORT  默认 3000
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '3000'))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        # 便于本地调试，避免浏览器强缓存 JS
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def main():
    srv = None
    port = PORT
    for _ in range(21):
        try:
            srv = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            port += 1
    if srv is None:
        print(f'启动失败：{PORT}-{port} 端口均被占用')
        return

    shown = '127.0.0.1' if HOST in ('0.0.0.0', '', '*') else HOST
    url = f'http://{shown}:{port}'
    print('=' * 60)
    print('  鲁信环境 · 企业制度门户  前端已启动')
    print(f'  门户首页   : {url}/')
    print(f'  管理后台   : {url}/#/admin')
    print('  请确认 backend 已启动，且 config.js 中 API_BASE 指向后端')
    print('  停止服务   : Ctrl+C')
    print('=' * 60)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
