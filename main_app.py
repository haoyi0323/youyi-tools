#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具集合网站 - 主应用
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import importlib
import sys

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

class ToolboxApp:
    def __init__(self):
        self.tools_config = self.load_tools_config()
        self.setup_page_config()
        
    def setup_page_config(self):
        """设置页面配置"""
        st.set_page_config(
            page_title="工具集合网站",
            page_icon="🧰",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
    def load_tools_config(self):
        """加载工具配置"""
        config_file = Path(__file__).parent / "tools_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 默认配置
            default_config = {
                "tools": [
                    {
                        "id": "reservation_matcher",
                        "name": "鹭府预定匹配工具",
                        "description": "智能匹配美团订单与预订记录，支持数据分析和导出",
                        "category": "数据处理",
                        "icon": "📊",
                        "module": "streamlit_app",
                        "class": "ReservationMatcherWeb",
                        "tags": ["数据匹配", "Excel处理", "美团订单", "预订管理"],
                        "featured": True,
                        "created_date": "2025-01-01"
                    }
                ],
                "categories": [
                    {"id": "data_processing", "name": "数据处理", "icon": "📊"},
                    {"id": "file_tools", "name": "文件工具", "icon": "📁"},
                    {"id": "text_tools", "name": "文本工具", "icon": "📝"},
                    {"id": "image_tools", "name": "图片工具", "icon": "🖼️"},
                    {"id": "utilities", "name": "实用工具", "icon": "🔧"}
                ]
            }
            self.save_tools_config(default_config)
            return default_config
    
    def save_tools_config(self, config):
        """保存工具配置"""
        config_file = Path(__file__).parent / "tools_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def render_header(self):
        """渲染页面头部"""
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: -1rem -1rem 2rem -1rem; color: white;'>
            <h1 style='margin: 0; font-size: 3rem; font-weight: 700;'>🧰 工具集合网站</h1>
            <p style='margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;'>一站式在线工具平台，提高工作效率</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_search_and_filter(self):
        """渲染搜索和筛选区域"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 搜索工具",
                placeholder="输入工具名称、描述或标签...",
                key="search_query"
            )
        
        with col2:
            categories = ["全部分类"] + [cat["name"] for cat in self.tools_config["categories"]]
            selected_category = st.selectbox(
                "📂 选择分类",
                categories,
                key="selected_category"
            )
        
        with col3:
            sort_options = ["最新", "最热", "名称", "分类"]
            sort_by = st.selectbox(
                "🔄 排序方式",
                sort_options,
                key="sort_by"
            )
        
        return search_query, selected_category, sort_by
    
    def filter_tools(self, search_query, selected_category, sort_by):
        """筛选和排序工具"""
        tools = self.tools_config["tools"].copy()
        
        # 搜索筛选
        if search_query:
            search_query = search_query.lower()
            tools = [
                tool for tool in tools
                if search_query in tool["name"].lower() 
                or search_query in tool["description"].lower()
                or any(search_query in tag.lower() for tag in tool["tags"])
            ]
        
        # 分类筛选
        if selected_category != "全部分类":
            tools = [tool for tool in tools if tool["category"] == selected_category]
        
        # 排序
        if sort_by == "最新":
            tools.sort(key=lambda x: x.get("created_date", ""), reverse=True)
        elif sort_by == "名称":
            tools.sort(key=lambda x: x["name"])
        elif sort_by == "分类":
            tools.sort(key=lambda x: x["category"])
        
        return tools
    
    def render_tool_card(self, tool):
        """渲染工具卡片"""
        with st.container():
            st.markdown(f"""
            <div style='
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1rem 0;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
                cursor: pointer;
            ' onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)'"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)'">
                <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                    <span style='font-size: 2rem; margin-right: 1rem;'>{tool["icon"]}</span>
                    <div>
                        <h3 style='margin: 0; color: #1a1a1a; font-size: 1.3rem;'>{tool["name"]}</h3>
                        <span style='color: #666; font-size: 0.9rem;'>📂 {tool["category"]}</span>
                    </div>
                </div>
                <p style='color: #555; margin-bottom: 1rem; line-height: 1.5;'>{tool["description"]}</p>
                <div style='margin-bottom: 1rem;'>
                    {"".join([f'<span style="background: #f0f2f6; color: #4a5568; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.8rem; margin-right: 0.5rem;">#{tag}</span>' for tag in tool["tags"]])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"🚀 使用 {tool['name']}", key=f"use_{tool['id']}", use_container_width=True):
                st.session_state.current_tool = tool["id"]
                st.rerun()
    
    def render_tools_grid(self, tools):
        """渲染工具网格"""
        if not tools:
            st.info("🔍 没有找到匹配的工具，请尝试其他搜索条件")
            return
        
        # 统计信息
        st.markdown(f"**找到 {len(tools)} 个工具**")
        
        # 工具网格 - 每行3个
        cols_per_row = 3
        for i in range(0, len(tools), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, tool in enumerate(tools[i:i+cols_per_row]):
                with cols[j]:
                    self.render_tool_card(tool)
    
    def load_tool_module(self, tool_id):
        """动态加载工具模块"""
        tool = next((t for t in self.tools_config["tools"] if t["id"] == tool_id), None)
        if not tool:
            return None
        
        try:
            module_name = tool["module"]
            class_name = tool["class"]
            
            # 动态导入模块
            module = importlib.import_module(module_name)
            tool_class = getattr(module, class_name)
            
            return tool_class()
        except Exception as e:
            st.error(f"加载工具失败: {str(e)}")
            return None
    
    def render_tool_interface(self, tool_id):
        """渲染工具界面"""
        tool = next((t for t in self.tools_config["tools"] if t["id"] == tool_id), None)
        if not tool:
            st.error("工具不存在")
            return
        
        # 返回按钮
        col1, col2 = st.columns([1, 8])
        with col1:
            if st.button("⬅️ 返回", key="back_to_home"):
                if 'current_tool' in st.session_state:
                    del st.session_state.current_tool
                st.rerun()
        
        with col2:
            st.markdown(f"## {tool['icon']} {tool['name']}")
        
        st.divider()
        
        # 加载工具
        tool_instance = self.load_tool_module(tool_id)
        if tool_instance:
            # 根据不同工具类型调用不同方法
            if tool_id == "reservation_matcher":
                self.render_reservation_matcher(tool_instance)
            else:
                st.error("未知的工具类型")
    
    def render_reservation_matcher(self, tool_instance):
        """渲染预定匹配工具"""
        # 创建标签页
        tab1, tab2, tab3 = st.tabs(["📁 文件处理", "📊 结果查看", "📈 数据分析"])
        
        with tab1:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📤 文件上传")
                tool_instance.load_files()
                
            with col2:
                st.subheader("⚡ 数据匹配")
                
                is_valid, message = tool_instance.validate_files()
                
                if not is_valid:
                    st.warning(message)
                else:
                    st.success("文件已就绪")
                    
                    if st.button("🚀 开始匹配", type="primary", use_container_width=True):
                        with st.spinner("匹配中..."):
                            success, result_message = tool_instance.match_data()
                            
                        if success:
                            st.success(result_message)
                            st.info("请切换到'结果查看'标签页")
                        else:
                            st.error(result_message)
        
        with tab2:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                tool_instance.display_results()
                
            with col2:
                st.subheader("📥 导出")
                tool_instance.export_results()
        
        with tab3:
            tool_instance.show_data_analysis()
    
    def render_footer(self):
        """渲染页面底部"""
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; padding: 2rem 0;'>
            <p>© 2025 工具集合网站 | 提高工作效率的在线工具平台</p>
            <p>如需添加新工具或建议，请联系管理员</p>
        </div>
        """, unsafe_allow_html=True)
    
    def apply_custom_css(self):
        """应用自定义CSS样式"""
        st.markdown("""
        <style>
        .main {
            padding: 1rem 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
            border: none;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .stSelectbox > div > div {
            border-radius: 8px;
        }
        
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #e1e5e9;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            border-bottom: 2px solid #e1e5e9;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 3rem;
            padding: 0 2rem;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            font-weight: 500;
            color: #64748b;
        }
        
        .stTabs [aria-selected="true"] {
            background: transparent;
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tool-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        </style>
        """, unsafe_allow_html=True)
    
    def run(self):
        """运行主应用"""
        self.apply_custom_css()
        
        # 检查是否选择了工具
        if hasattr(st.session_state, 'current_tool') and st.session_state.current_tool:
            self.render_tool_interface(st.session_state.current_tool)
        else:
            # 显示工具列表
            self.render_header()
            
            # 搜索和筛选
            search_query, selected_category, sort_by = self.render_search_and_filter()
            
            # 筛选工具
            filtered_tools = self.filter_tools(search_query, selected_category, sort_by)
            
            # 显示工具网格
            self.render_tools_grid(filtered_tools)
            
            # 页面底部
            self.render_footer()

def main():
    app = ToolboxApp()
    app.run()

if __name__ == "__main__":
    main()