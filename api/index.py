#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel 部署入口文件
"""

from http.server import BaseHTTPRequestHandler
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 返回简单的 HTML 页面，提示用户 Streamlit 应用无法直接在 Vercel 上运行
        html_content = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>工具集合网站</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: white;
                    padding: 3rem;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    margin: 2rem;
                }
                .icon {
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }
                h1 {
                    color: #333;
                    margin-bottom: 1rem;
                    font-size: 2.5rem;
                }
                p {
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 2rem;
                    font-size: 1.1rem;
                }
                .btn {
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 1rem 2rem;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: 600;
                    transition: transform 0.3s ease;
                    margin: 0.5rem;
                }
                .btn:hover {
                    transform: translateY(-2px);
                }
                .note {
                    background: #f8f9fa;
                    padding: 1.5rem;
                    border-radius: 10px;
                    margin-top: 2rem;
                    border-left: 4px solid #667eea;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">🧰</div>
                <h1>工具集合网站</h1>
                <p>很抱歉，Streamlit 应用无法直接在 Vercel 的无服务器环境中运行。</p>
                <p>建议使用以下平台部署 Streamlit 应用：</p>
                
                <a href="https://render.com" class="btn" target="_blank">🚀 Render</a>
                <a href="https://railway.app" class="btn" target="_blank">🚄 Railway</a>
                <a href="https://share.streamlit.io" class="btn" target="_blank">☁️ Streamlit Cloud</a>
                
                <div class="note">
                    <strong>💡 部署建议：</strong><br>
                    推荐使用 Render 或 Railway 平台，它们专为后端应用设计，支持长时间运行的 Streamlit 应用，并且可以绑定自定义域名 youyi.work。
                </div>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
        return
    
    def do_POST(self):
        self.do_GET()