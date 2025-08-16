import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
import io
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

class ReservationMatcherWeb:
    def __init__(self):
        self.meituan_file = None
        self.reservation_file = None
        self.merged_df = pd.DataFrame()
        self.original_df = pd.DataFrame()
        
    def smart_table_match(self, reservation_table, meituan_table):
        """智能桌牌号匹配函数"""
        # 提取数字部分
        def extract_numbers(table_str):
            if pd.isna(table_str):
                return None
            numbers = re.findall(r'\d+', str(table_str))
            return ''.join(numbers) if numbers else None
        
        # 判断是否为外卖订单
        def is_takeout(table_str):
            if pd.isna(table_str):
                return False
            table_str = str(table_str).lower()
            takeout_keywords = ['外卖', 'takeout', '配送', '打包']
            return any(keyword in table_str for keyword in takeout_keywords)
        
        # 完全匹配（最高优先级）
        if str(reservation_table) == str(meituan_table):
            return True, "完全匹配"
        
        # 数字部分匹配（包括外卖订单）
        res_numbers = extract_numbers(reservation_table)
        mt_numbers = extract_numbers(meituan_table)
        
        if res_numbers and mt_numbers and res_numbers == mt_numbers:
            # 区分外卖和堂食的数字匹配
            if is_takeout(meituan_table):
                return True, "外卖匹配"
            else:
                return True, "数字匹配"
        
        return False, "无匹配"
    
    def show_record_details(self, selected_record, display_df, selected_idx):
        """显示选中记录的详细信息"""
        st.divider()
        st.subheader("🔍 记录详情")
        
        # 创建两列布局
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 预订信息")
            reservation_info = {
                "日期": selected_record.get('日期', ''),
                "桌牌号": selected_record.get('桌牌号', ''),
                "预订人": selected_record.get('预订人', ''),
                "市别": selected_record.get('市别', ''),
                "匹配状态": selected_record.get('匹配状态', ''),
                "匹配类型": selected_record.get('匹配类型', '')
            }
            
            for key, value in reservation_info.items():
                st.text(f"{key}: {value}")
        
        with col2:
            st.markdown("### 🛒 美团订单信息")
            if selected_record.get('匹配状态') == '已匹配':
                meituan_info = {
                    "下单时间": selected_record.get('下单时间', ''),
                    "桌牌号": selected_record.get('桌牌号', ''),
                    "支付合计": selected_record.get('支付合计', ''),
                    "结账方式": selected_record.get('结账方式', ''),
                    "下单时间格式化": selected_record.get('下单时间_格式化', '')
                }
                
                for key, value in meituan_info.items():
                    st.text(f"{key}: {value}")
                
                # 移除匹配按钮
                st.markdown("---")
                if st.button("❌ 移除此匹配", key=f"remove_{selected_idx}", type="secondary"):
                    self.remove_match(selected_record, selected_idx)
                    st.rerun()
            else:
                st.info("此记录未匹配到美团订单")
    
    def remove_match(self, selected_record, selected_idx):
        """移除匹配记录"""
        try:
            # 在merged_df中找到对应记录并移除匹配信息
            mask = (
                (self.merged_df['日期'] == selected_record['日期']) &
                (self.merged_df['桌牌号'] == selected_record['桌牌号']) &
                (self.merged_df['预订人'] == selected_record['预订人']) &
                (self.merged_df['市别'] == selected_record['市别'])
            )
            
            # 更新匹配状态和相关字段
            self.merged_df.loc[mask, '匹配状态'] = '未匹配'
            self.merged_df.loc[mask, '匹配类型'] = '未匹配'
            self.merged_df.loc[mask, '支付合计'] = None
            self.merged_df.loc[mask, '下单时间'] = None
            self.merged_df.loc[mask, '下单时间_格式化'] = None
            self.merged_df.loc[mask, '结账方式'] = None
            
            st.success("✅ 已成功移除匹配")
            
        except Exception as e:
            st.error(f"❌ 移除匹配失败: {str(e)}")
        
    def load_files(self):
        """文件上传界面"""
        # 美团订单文件上传
        st.write("**美团订单文件**")
        meituan_uploaded = st.file_uploader(
            "选择美团订单Excel文件", 
            type=['xlsx', 'xls'],
            key="meituan"
        )
        
        if meituan_uploaded:
            try:
                # 尝试不同的header设置来读取美团文件
                meituan_df = None
                for header_row in [2, 1, 0, None]:
                    try:
                        temp_df = pd.read_excel(meituan_uploaded, header=header_row)
                        # 检查是否包含关键列
                        if any('营业日期' in str(col) for col in temp_df.columns) and \
                           any('桌牌号' in str(col) for col in temp_df.columns):
                            meituan_df = temp_df
                            break
                    except:
                        continue
                
                if meituan_df is None:
                    st.error("无法识别美团文件格式，请检查文件是否正确")
                    return
                
                self.meituan_file = meituan_df
                
                # 清理数据：移除完全空的列和行
                self.meituan_file = self.meituan_file.dropna(how='all', axis=1)  # 删除全空列
                self.meituan_file = self.meituan_file.dropna(how='all', axis=0)  # 删除全空行
                
                # 转换所有列为字符串类型以避免类型冲突
                for col in self.meituan_file.columns:
                    if self.meituan_file[col].dtype == 'object':
                        self.meituan_file[col] = self.meituan_file[col].astype(str)
                    
                # 智能检测列名
                date_col = None
                table_col = None
                customer_col = None
                
                for col in self.meituan_file.columns:
                    if any(keyword in str(col) for keyword in ['营业日期', '日期', 'date']):
                        date_col = col
                    if any(keyword in str(col) for keyword in ['桌牌号', '桌号', '台号']):
                        table_col = col
                    if any(keyword in str(col) for keyword in ['客户', '姓名', '顾客']):
                        customer_col = col
                
                missing_cols = []
                if not date_col: missing_cols.append('日期相关列')
                if not table_col: missing_cols.append('桌牌号相关列')
                
                if missing_cols:
                    st.error(f"缺少必要列: {', '.join(missing_cols)}")
                else:
                    st.success(f"✅ 美团文件已加载 ({len(self.meituan_file)} 条记录)")
                    
                    with st.expander("预览美团数据", expanded=False):
                        # 创建显示用的DataFrame副本
                        display_df = self.meituan_file.copy()
                        
                        # 添加水平滚动样式
                        st.markdown("""
                        <style>
                        .stDataFrame {
                            overflow-x: auto;
                        }
                        .stDataFrame > div {
                            overflow-x: auto;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.dataframe(display_df, use_container_width=True)
                    
            except Exception as e:
                st.error(f"美团文件加载失败: {str(e)}")
            
            st.divider()
            
            # 预订记录文件上传
            st.write("**预订记录文件**")
            reservation_uploaded = st.file_uploader(
                "选择预订记录Excel文件", 
                type=['xlsx', 'xls'],
                key="reservation"
            )
            
            if reservation_uploaded:
                try:
                    # 读取Excel文件的所有工作表
                    excel_file = pd.ExcelFile(reservation_uploaded)
                    all_sheets_data = []
                    
                    # 简化显示信息
                    valid_sheets = 0
                    total_records = 0
                    
                    # 逐个读取每个工作表
                    for sheet_name in excel_file.sheet_names:
                        try:
                            sheet_df = pd.read_excel(reservation_uploaded, sheet_name=sheet_name)
                            
                            # 清理数据：移除完全空的列和行
                            sheet_df = sheet_df.dropna(how='all', axis=1)  # 删除全空列
                            sheet_df = sheet_df.dropna(how='all', axis=0)  # 删除全空行
                            
                            # 如果工作表有数据，添加到列表中
                            if not sheet_df.empty:
                                # 添加工作表名称列用于标识数据来源
                                sheet_df['数据来源工作表'] = sheet_name
                                all_sheets_data.append(sheet_df)
                                valid_sheets += 1
                                total_records += len(sheet_df)
                        except Exception as e:
                            continue  # 静默跳过错误的工作表
                    
                    # 合并所有工作表的数据
                    if all_sheets_data:
                        self.reservation_file = pd.concat(all_sheets_data, ignore_index=True)
                        
                        # 转换所有列为字符串类型以避免类型冲突
                        for col in self.reservation_file.columns:
                            if self.reservation_file[col].dtype == 'object':
                                self.reservation_file[col] = self.reservation_file[col].astype(str)
                        
                        st.success(f"✅ 预订文件已加载 ({len(self.reservation_file)} 条记录)")
                    else:
                        st.error("没有找到有效数据")
                        self.reservation_file = pd.DataFrame()
                    
                    with st.expander("👀 预览预订数据", expanded=False):
                        # 创建显示用的DataFrame副本
                        display_df = self.reservation_file.copy()
                        
                        # 添加水平滚动样式
                        st.markdown("""
                        <style>
                        .stDataFrame {
                            overflow-x: auto;
                        }
                        .stDataFrame > div {
                            overflow-x: auto;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.dataframe(display_df, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"❌ 预订文件加载失败: {str(e)}")
            

    
    def validate_files(self):
        """验证文件是否已加载"""
        if self.meituan_file is None or self.reservation_file is None:
            return False, "请先上传美团订单文件和预订记录文件"
        
        if self.meituan_file.empty or self.reservation_file.empty:
            return False, "上传的文件为空，请检查文件内容"
        
        return True, "文件验证通过"
    
    def match_data(self):
        """数据匹配核心逻辑 - 使用与桌面版完全相同的匹配算法"""
        try:
            # 读取美团数据 - 使用与桌面版相同的处理方式
            df = self.meituan_file.copy()
            
            # 数据清洗和预处理
            df = df[df['订单状态'] == '已结账']
            df = df[df['营业日期'] != '--']
            
            # 改进的支付金额提取
            def extract_payment(payment_str):
                if pd.isna(payment_str):
                    return None
                try:
                    # 查找所有数字（包括负数和小数）
                    numbers = re.findall(r'-?\d+\.?\d*', str(payment_str))
                    if numbers:
                        return float(numbers[0])
                except (ValueError, IndexError):
                    pass
                return None
                
            df['支付合计'] = df['结账方式'].apply(extract_payment)
            df['营业日期'] = pd.to_datetime(df['营业日期'], errors='coerce')
            df['下单时间'] = pd.to_datetime(df['下单时间'], errors='coerce')
            
            # 根据下单时间判断市别
            def determine_market_period(order_time):
                if pd.isna(order_time):
                    return None
                try:
                    hour = pd.to_datetime(order_time).hour
                    # 午市: 6:00-16:00, 晚市: 16:00-24:00
                    if 6 <= hour < 16:
                        return '午市'
                    elif 16 <= hour <= 23:
                        return '晚市'
                    else:
                        return None  # 非营业时间
                except:
                    return None
            
            df['市别'] = df['下单时间'].apply(determine_market_period)
            
            # 选择需要的列，保留下单时间和结账方式用于显示
            mt_df = df[['营业日期', '桌牌号', '下单时间', '支付合计', '市别', '结账方式']].copy()
            # 过滤掉非营业时间的订单
            mt_df = mt_df[mt_df['市别'].notna()]
            
            # 格式化下单时间为更易读的格式
            try:
                mt_df['下单时间_格式化'] = mt_df['下单时间'].dt.strftime('%H:%M:%S')
            except AttributeError:
                # 如果不是datetime类型，尝试转换后格式化
                mt_df['下单时间'] = pd.to_datetime(mt_df['下单时间'], errors='coerce')
                mt_df['下单时间_格式化'] = mt_df['下单时间'].dt.strftime('%H:%M:%S')
            
            # 提取下单时间的日期部分用于匹配
            mt_df['下单日期'] = mt_df['下单时间'].dt.date
            
            # 读取预订数据
            merged_all = pd.DataFrame()
            
            # 处理预订数据 - 支持多工作表
            if hasattr(self.reservation_file, 'sheet_names'):
                # 如果是ExcelFile对象，处理多个工作表
                for sheet_name in self.reservation_file.sheet_names:
                    try:
                        day_df = pd.read_excel(self.reservation_file, sheet_name=sheet_name)
                        
                        # 检查必要的列是否存在
                        required_cols = ['姓名', '预订人']
                        missing_cols = [col for col in required_cols if col not in day_df.columns]
                        if missing_cols:
                            continue
                            
                        # 数据清洗
                        day_df = day_df[day_df['姓名'].notna() & day_df['预订人'].notna()]
                        
                        # 预订人姓名标准化处理
                        def standardize_name(name):
                            if pd.isna(name):
                                return name
                            name_str = str(name).strip()
                            # 处理同义词
                            if name_str in ['平和', '平哥']:
                                return '平和'
                            # 处理刘霞和刘的映射
                            if name_str in ['刘霞', '刘']:
                                return '刘霞'
                            # 处理周和周思玗的映射
                            if name_str in ['周', '周思玗']:
                                return '周思玗'
                            # 处理大小写统一（sk -> SK）
                            if name_str.lower() == 'sk':
                                return 'SK'
                            return name_str
                        
                        day_df['预订人'] = day_df['预订人'].apply(standardize_name)
                        
                        # 选择和重命名列
                        available_cols = ['日期', '市别', '包厢', '姓名', '预订人', '经手人']
                        existing_cols = [col for col in available_cols if col in day_df.columns]
                        day_df = day_df[existing_cols].copy()
                        
                        # 标准化列名
                        col_mapping = {'包厢': '桌牌号', '姓名': '客户姓名'}
                        day_df.rename(columns=col_mapping, inplace=True)
                        
                        # 处理日期
                        if '日期' in day_df.columns:
                            day_df['日期'] = pd.to_datetime(
                                day_df['日期'].astype(str).str.split().str[0], 
                                errors='coerce'
                            )
                        
                        # 合并数据 - 改进的匹配逻辑
                        if '日期' in day_df.columns and '桌牌号' in day_df.columns and '市别' in day_df.columns:
                            # 为每个预订记录找到最佳匹配的美团订单
                            merged_records = []
                            
                            for _, reservation in day_df.iterrows():
                                # 找到同一日期、市别的所有美团订单，然后使用智能桌牌号匹配
                                reservation_date = reservation['日期'].date() if hasattr(reservation['日期'], 'date') else reservation['日期']
                                
                                # 先按日期和市别筛选
                                candidate_orders = mt_df[
                                    (mt_df['下单日期'] == reservation_date) &
                                    (mt_df['市别'] == reservation['市别'])
                                ].copy()
                                
                                # 使用智能匹配找到桌牌号匹配的订单
                                matching_orders = []
                                match_info = []
                                
                                for _, order in candidate_orders.iterrows():
                                    is_match, match_type = self.smart_table_match(
                                        reservation['桌牌号'], 
                                        order['桌牌号']
                                    )
                                    if is_match:
                                        matching_orders.append(order)
                                        match_info.append(match_type)
                                
                                matching_orders = pd.DataFrame(matching_orders) if matching_orders else pd.DataFrame()
                                
                                if not matching_orders.empty:
                                    # 为每个匹配的订单创建独立记录
                                    for idx, (_, order) in enumerate(matching_orders.iterrows()):
                                        merged_record = reservation.copy()
                                        merged_record['支付合计'] = order['支付合计']
                                        merged_record['下单时间'] = order['下单时间']
                                        merged_record['下单时间_格式化'] = order['下单时间_格式化']
                                        merged_record['结账方式'] = order['结账方式']
                                        merged_record['匹配类型'] = match_info[idx] if idx < len(match_info) else '未知'
                                        merged_records.append(merged_record)
                                else:
                                    # 没有匹配的订单
                                    merged_record = reservation.copy()
                                    merged_record['支付合计'] = None
                                    merged_record['下单时间'] = None
                                    merged_record['下单时间_格式化'] = None
                                    merged_record['结账方式'] = None
                                    merged_record['匹配类型'] = '未匹配'
                                    merged_records.append(merged_record)
                            
                            if merged_records:
                                merged = pd.DataFrame(merged_records)
                                merged_all = pd.concat([merged_all, merged], ignore_index=True)
                                
                    except Exception as e:
                        continue
            else:
                # 如果是单个DataFrame，直接处理
                day_df = self.reservation_file.copy()
                
                # 检查必要的列是否存在
                required_cols = ['姓名', '预订人']
                missing_cols = [col for col in required_cols if col not in day_df.columns]
                if missing_cols:
                    return False, f"预订文件缺少必要列: {missing_cols}"
                    
                # 数据清洗
                day_df = day_df[day_df['姓名'].notna() & day_df['预订人'].notna()]
                
                # 选择和重命名列
                available_cols = ['日期', '市别', '包厢', '姓名', '预订人', '经手人']
                existing_cols = [col for col in available_cols if col in day_df.columns]
                day_df = day_df[existing_cols].copy()
                
                # 标准化列名
                col_mapping = {'包厢': '桌牌号', '姓名': '客户姓名'}
                day_df.rename(columns=col_mapping, inplace=True)
                
                # 处理日期
                if '日期' in day_df.columns:
                    day_df['日期'] = pd.to_datetime(
                        day_df['日期'].astype(str).str.split().str[0], 
                        errors='coerce'
                    )
                
                # 合并数据 - 改进的匹配逻辑
                if '日期' in day_df.columns and '桌牌号' in day_df.columns and '市别' in day_df.columns:
                    # 为每个预订记录找到最佳匹配的美团订单
                    merged_records = []
                    
                    for _, reservation in day_df.iterrows():
                        # 找到同一日期、桌牌号、市别的所有美团订单（使用下单时间的日期进行匹配）
                        reservation_date = reservation['日期'].date() if hasattr(reservation['日期'], 'date') else reservation['日期']
                        matching_orders = mt_df[
                            (mt_df['下单日期'] == reservation_date) &
                            (mt_df['桌牌号'] == reservation['桌牌号']) &
                            (mt_df['市别'] == reservation['市别'])
                        ].copy()
                        
                        if not matching_orders.empty:
                            # 为每个匹配的订单创建独立记录
                            for _, order in matching_orders.iterrows():
                                merged_record = reservation.copy()
                                merged_record['支付合计'] = order['支付合计']
                                merged_record['下单时间'] = order['下单时间']
                                merged_record['下单时间_格式化'] = order['下单时间_格式化']
                                merged_record['结账方式'] = order['结账方式']
                                merged_records.append(merged_record)
                        else:
                            # 没有匹配的订单
                            merged_record = reservation.copy()
                            merged_record['支付合计'] = None
                            merged_record['下单时间'] = None
                            merged_record['下单时间_格式化'] = None
                            merged_record['结账方式'] = None
                            merged_records.append(merged_record)
                    
                    if merged_records:
                        merged_all = pd.DataFrame(merged_records)
            
            # 数据后处理
            if not merged_all.empty:
                # 添加匹配状态列
                merged_all['匹配状态'] = merged_all['支付合计'].apply(
                    lambda x: '已匹配' if pd.notna(x) else '未匹配'
                )
                
                # 格式化数据
                if '支付合计' in merged_all.columns:
                    merged_all['支付合计'] = merged_all['支付合计'].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else ""
                    )
                    
                # 排序
                sort_cols = []
                if '日期' in merged_all.columns:
                    sort_cols.append('日期')
                if '桌牌号' in merged_all.columns:
                    sort_cols.append('桌牌号')
                if sort_cols:
                    merged_all.sort_values(sort_cols, inplace=True, ignore_index=True)
            
            self.merged_df = merged_all
            self.original_df = merged_all.copy()  # 保存原始数据
            
            # 显示统计信息
            total_records = len(self.merged_df)
            matched_records = len(self.merged_df[self.merged_df['匹配状态'] == '已匹配']) if '匹配状态' in self.merged_df.columns else 0
            
            return True, f"匹配完成！总记录: {total_records}, 已匹配: {matched_records}, 未匹配: {total_records - matched_records}"
            
        except Exception as e:
            return False, f"匹配失败: {str(e)}"
    
    def display_results(self):
        """显示匹配结果"""
        if self.merged_df.empty:
            st.warning("暂无数据")
            return
        
        # 显示匹配统计信息
        if '匹配类型' in self.merged_df.columns:
            st.subheader("📊 匹配统计")
            match_stats = self.merged_df['匹配类型'].value_counts()
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                complete_match = match_stats.get('完全匹配', 0)
                st.metric("完全匹配", complete_match, help="桌牌号完全相同的匹配")
            
            with col2:
                number_match = match_stats.get('数字匹配', 0)
                st.metric("数字匹配", number_match, help="桌牌号数字部分相同的堂食匹配")
            
            with col3:
                takeout_match = match_stats.get('外卖匹配', 0)
                st.metric("外卖匹配", takeout_match, help="预订改为外卖配送的匹配")
            
            with col4:
                no_match = match_stats.get('未匹配', 0)
                st.metric("未匹配", no_match, help="未找到对应美团订单")
            
            with col5:
                total_records = len(self.merged_df)
                match_rate = round((total_records - no_match) / total_records * 100, 1) if total_records > 0 else 0
                st.metric("匹配率", f"{match_rate}%", help="成功匹配的记录比例")
            
            st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "显示内容",
                ["全部记录", "已匹配记录", "未匹配记录"]
            )
            # 保存筛选条件到session_state
            st.session_state.filter_option = filter_option
        
        with col2:
            search_keyword = st.text_input("搜索预订人", placeholder="输入预订人姓名进行搜索")
            # 保存搜索关键词到session_state
            st.session_state.search_keyword = search_keyword
        
        # 应用筛选
        display_df = self.merged_df.copy()
        
        if filter_option == "已匹配记录":
            display_df = display_df[display_df['匹配状态'] == '已匹配']
        elif filter_option == "未匹配记录":
            display_df = display_df[display_df['匹配状态'] == '未匹配']
        
        if search_keyword:
            if '预订人' in display_df.columns:
                # 标准化搜索关键词
                def standardize_search_keyword(keyword):
                    keyword = keyword.strip()
                    if keyword in ['平和', '平哥']:
                        return ['平和', '平哥']  # 返回所有同义词
                    elif keyword in ['刘霞', '刘']:
                        return ['刘霞', '刘']  # 返回刘霞和刘的所有变体
                    elif keyword in ['周', '周思玗']:
                        return ['周', '周思玗']  # 返回周和周思玗的所有变体
                    elif keyword.lower() == 'sk':
                        return ['SK', 'sk', 'Sk', 'sK']  # 返回所有大小写变体
                    else:
                        return [keyword]
                
                search_terms = standardize_search_keyword(search_keyword)
                # 创建搜索条件，匹配任何一个同义词
                search_condition = False
                for term in search_terms:
                    search_condition |= display_df['预订人'].astype(str).str.contains(term, case=False, na=False)
                display_df = display_df[search_condition]
        
        # 显示数据表格（简化版）
        st.subheader(f"📋 数据表格 ({len(display_df)} 条记录)")
        
        if not display_df.empty:
            # 配置核心列显示（简化信息）
            columns_to_show = ['日期', '桌牌号', '预订人', '市别', '匹配状态', '匹配类型']
            available_columns = [col for col in columns_to_show if col in display_df.columns]
            
            # 创建显示用的DataFrame副本并处理数据类型
            table_df = display_df[available_columns].copy()
            
            # 格式化显示
            for col in table_df.columns:
                if col == '匹配状态':
                    table_df[col] = table_df[col].apply(lambda x: '✅已匹配' if str(x) == '已匹配' else '❌未匹配')
                else:
                    table_df[col] = table_df[col].astype(str).replace('nan', '')
            
            # 重命名列标题使其更简洁
            column_rename = {
                '日期': '📅日期',
                '桌牌号': '🪑桌号', 
                '预订人': '👤预订人',
                '市别': '🏪市别',
                '匹配状态': '📊状态'
            }
            table_df = table_df.rename(columns=column_rename)
            
            # 添加水平滚动的表格显示
            st.markdown("""
            <style>
            .stDataFrame {
                overflow-x: auto;
            }
            .stDataFrame > div {
                overflow-x: auto;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # 使用可选择的数据表格
            selected_rows = st.dataframe(
                table_df,
                use_container_width=True,
                height=None,  # 移除高度限制，显示所有内容
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # 处理行选择和详情显示
            if selected_rows.selection.rows:
                selected_idx = selected_rows.selection.rows[0]
                if selected_idx < len(display_df):
                    selected_record = display_df.iloc[selected_idx]
                    self.show_record_details(selected_record, display_df, selected_idx)
            
            # 手动匹配功能
            if filter_option == "未匹配记录" and not display_df.empty:
                self.manual_match_interface(display_df)
        else:
            st.info("📝 没有符合条件的记录")
    
    def manual_match_interface(self, unmatched_df):
        """手动匹配界面"""
        st.write("**🔧 手动匹配**")
        
        if unmatched_df.empty:
            return
        
        # 选择要匹配的预订记录（简化显示）
        reservation_options = []
        for idx, row in unmatched_df.iterrows():
            # 格式化日期，只显示年月日
            date_str = 'N/A'
            if pd.notna(row.get('日期')):
                try:
                    if hasattr(row.get('日期'), 'strftime'):
                        date_str = row.get('日期').strftime('%Y-%m-%d')
                    else:
                        date_str = str(row.get('日期')).split(' ')[0]  # 取空格前的日期部分
                except:
                    date_str = str(row.get('日期', 'N/A'))
            
            option_text = f"📅{date_str} | 🪑{row.get('桌牌号', 'N/A')}桌 | 🏪{row.get('市别', 'N/A')} | 👤{row.get('预订人', 'N/A')}"
            reservation_options.append((option_text, idx))
        
        selected_reservation = st.selectbox(
            "选择要匹配的预订记录",
            options=reservation_options,
            format_func=lambda x: x[0]
        )
        
        if selected_reservation and self.meituan_file is not None:
            reservation_idx = selected_reservation[1]
            reservation_record = unmatched_df.loc[reservation_idx]
            
            # 获取相关的美团订单
            reservation_date = reservation_record['日期']
            if hasattr(reservation_date, 'date'):
                reservation_date = reservation_date.date()
            
            # 处理美团数据，确保支付合计字段正确提取
            def extract_payment(payment_str):
                if pd.isna(payment_str):
                    return None
                try:
                    # 查找所有数字（包括负数和小数）
                    numbers = re.findall(r'-?\d+\.?\d*', str(payment_str))
                    if numbers:
                        return float(numbers[0])
                except (ValueError, IndexError):
                    pass
                return None
            
            # 复制美团文件并处理支付合计
            meituan_processed = self.meituan_file.copy()
            if '支付合计' not in meituan_processed.columns and '结账方式' in meituan_processed.columns:
                meituan_processed['支付合计'] = meituan_processed['结账方式'].apply(extract_payment)
            
            # 安全地比较日期（使用下单时间的日期进行匹配）
            try:
                if '下单时间' in meituan_processed.columns:
                    # 确保下单时间是datetime类型
                    meituan_dates = pd.to_datetime(meituan_processed['下单时间'], errors='coerce')
                    related_meituan = meituan_processed[
                        meituan_dates.dt.date == reservation_date
                    ]
                else:
                    related_meituan = meituan_processed
            except (AttributeError, TypeError):
                related_meituan = meituan_processed
            
            if related_meituan.empty:
                related_meituan = meituan_processed
            
            st.write("**📋 可选择的美团订单:**")
            st.write("💡 *点击表格中的行来选择美团订单（支持多选，按住Ctrl键可选择多个）*")
            
            # 显示美团订单详细信息表格（可选择）
            if not related_meituan.empty:
                # 选择要显示的核心列（包含日期、时间、金额）
                display_columns = ['营业日期', '桌牌号', '下单时间', '支付合计', '结账方式']
                available_columns = [col for col in display_columns if col in related_meituan.columns]
                
                if available_columns:
                    meituan_display = related_meituan[available_columns].copy()
                    # 格式化显示
                    for col in meituan_display.columns:
                        if col == '支付合计':
                            meituan_display[col] = meituan_display[col].apply(lambda x: f"¥{x}" if pd.notna(x) and str(x) != 'nan' else '')
                        else:
                            meituan_display[col] = meituan_display[col].astype(str).replace('nan', '')
                    
                    # 重命名列标题使其更简洁
                    column_rename = {
                        '营业日期': '📅营业日期',
                        '桌牌号': '🪑桌号',
                        '下单时间': '⏰下单时间', 
                        '支付合计': '💰支付合计',
                        '结账方式': '💳结账方式'
                    }
                    meituan_display = meituan_display.rename(columns=column_rename)
                    
                    # 使用可选择的数据框（支持多选）
                    selected_rows = st.dataframe(
                        meituan_display,
                        use_container_width=True,
                        height=200,
                        hide_index=False,
                        selection_mode="multi-row",
                        key="meituan_selector",
                        on_select="rerun"
                    )
                    
                    # 获取选中的行（支持多选）
                    selected_meituan_indices = []
                    if selected_rows and 'selection' in selected_rows and 'rows' in selected_rows['selection']:
                        if selected_rows['selection']['rows']:
                            for selected_row_idx in selected_rows['selection']['rows']:
                                actual_idx = related_meituan.index[selected_row_idx]
                                selected_meituan_indices.append(actual_idx)
                    
                    # 显示选中的订单数量
                    if selected_meituan_indices:
                        st.info(f"已选择 {len(selected_meituan_indices)} 个美团订单")
            
            # 确认匹配按钮
            if st.button("确认匹配", type="primary"):
                if selected_meituan_indices:
                    # 获取原始预订记录
                    original_reservation = self.merged_df.loc[reservation_idx].copy()
                    
                    # 为每个选中的美团订单创建匹配记录
                    new_records = []
                    for i, meituan_idx in enumerate(selected_meituan_indices):
                        meituan_record = related_meituan.loc[meituan_idx]
                        
                        # 创建新的匹配记录
                        new_record = original_reservation.copy()
                        new_record['匹配状态'] = '已匹配'
                        new_record['下单时间'] = str(meituan_record.get('下单时间', ''))
                        new_record['下单时间_格式化'] = str(meituan_record.get('下单时间', ''))
                        new_record['结账方式'] = str(meituan_record.get('结账方式', ''))
                        
                        # 如果是第一个记录，更新原记录；否则添加新记录
                        if i == 0:
                            # 更新原记录
                            for col in new_record.index:
                                self.merged_df.at[reservation_idx, col] = new_record[col]
                        else:
                            # 添加新记录到列表
                            new_records.append(new_record)
                    
                    # 将新记录添加到DataFrame
                    if new_records:
                        new_df = pd.DataFrame(new_records)
                        self.merged_df = pd.concat([self.merged_df, new_df], ignore_index=True)
                    
                    st.success(f"匹配成功！已为 {len(selected_meituan_indices)} 个美团订单创建匹配记录。页面将自动刷新")
                    st.rerun()
                else:
                    st.warning("请先选择要匹配的美团订单")
    
    def export_results(self):
        """导出结果"""
        if self.merged_df.empty:
            st.warning("暂无数据")
            return
        
        # 导出选项
        export_option = st.selectbox(
            "导出选项",
            ["仅搜索", "全部（按时间排列）"]
        )
        
        # 获取当前搜索和筛选条件
        if 'filter_option' not in st.session_state:
            st.session_state.filter_option = "全部记录"
        if 'search_keyword' not in st.session_state:
            st.session_state.search_keyword = ""
        
        # 准备导出数据
        if export_option == "仅搜索":
            # 获取当前显示的搜索结果（只包含匹配成功的）
            export_df = self.get_filtered_data()
            export_df = export_df[export_df['匹配状态'] == '已匹配']  # 只导出匹配成功的
            
            # 根据搜索关键词生成文件名
            search_keyword = getattr(st.session_state, 'search_keyword', "")
            if search_keyword.strip():
                filename_suffix = f"{search_keyword.strip()}（美团匹配清单）"
            else:
                filename_suffix = "搜索结果"
        else:
            # 全部匹配成功的数据，按时间排列
            export_df = self.merged_df[self.merged_df['匹配状态'] == '已匹配'].copy()
            if '日期' in export_df.columns:
                export_df = export_df.sort_values('日期')
            filename_suffix = "全部匹配"
        
        if export_df.empty:
            st.warning("没有匹配成功的数据可导出")
            return
        
        # 准备导出的列
        export_columns = ['下单时间', '预订人', '桌牌号', '支付合计', '结账方式', '匹配类型']
        
        # 检查并选择可用的列
        available_columns = []
        for col in export_columns:
            if col in export_df.columns:
                available_columns.append(col)
            elif col == '预订人' and '客户姓名' in export_df.columns:
                available_columns.append('客户姓名')
                export_df = export_df.rename(columns={'客户姓名': '预订人'})
        
        # 创建导出用的DataFrame
        final_export_df = export_df[available_columns].copy()
        
        # 按日期排序（如果有下单时间列）
        if '下单时间' in final_export_df.columns:
            final_export_df = final_export_df.sort_values('下单时间')
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_export_df.to_excel(writer, sheet_name='匹配结果', index=False)
            
            # 获取工作表并设置格式
            worksheet = writer.sheets['匹配结果']
            
            # 设置Excel格式
            from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
            
            # 定义样式
            header_font = Font(bold=True, size=12)
            header_fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
            center_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # 设置表头样式
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
                cell.border = border
            
            # 设置数据行样式
            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = center_alignment
                    cell.border = border
            
            # 智能调整列宽
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                # 计算列的最大内容长度
                for cell in column:
                    try:
                        cell_value = str(cell.value) if cell.value is not None else ""
                        # 中文字符按2个字符计算宽度
                        char_count = sum(2 if ord(char) > 127 else 1 for char in cell_value)
                        if char_count > max_length:
                            max_length = char_count
                    except:
                        pass
                
                # 根据列内容设置合适的宽度
                if column_letter == 'A':  # 下单时间列
                    adjusted_width = max(22, min(max_length + 4, 28))
                elif column_letter == 'B':  # 预订人列
                    adjusted_width = max(15, min(max_length + 3, 25))
                elif column_letter == 'C':  # 桌牌号列
                    adjusted_width = max(12, min(max_length + 3, 18))
                elif column_letter == 'D':  # 支付合计列
                    adjusted_width = max(15, min(max_length + 3, 22))
                elif column_letter == 'E':  # 结账方式列
                    adjusted_width = max(25, min(max_length + 5, 40))  # 增加结账方式列宽度
                elif column_letter == 'F':  # 匹配类型列
                    adjusted_width = max(12, min(max_length + 3, 18))
                else:
                    adjusted_width = max(15, min(max_length + 3, 35))
                
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # 设置行高
            for row in range(1, worksheet.max_row + 1):
                worksheet.row_dimensions[row].height = 35  # 增加行高以适应多行内容
            
            # 特别处理表头行高
            worksheet.row_dimensions[1].height = 30
        
        excel_data = output.getvalue()
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"匹配结果_{filename_suffix}_{timestamp}.xlsx"
        
        st.download_button(
            label=f"📥 下载Excel ({len(final_export_df)}条记录)",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    def get_filtered_data(self):
        """获取当前筛选和搜索后的数据"""
        display_df = self.merged_df.copy()
        
        # 应用筛选（从session_state获取当前筛选条件）
        filter_option = getattr(st.session_state, 'filter_option', "全部记录")
        search_keyword = getattr(st.session_state, 'search_keyword', "")
        
        if filter_option == "已匹配记录":
            display_df = display_df[display_df['匹配状态'] == '已匹配']
        elif filter_option == "未匹配记录":
            display_df = display_df[display_df['匹配状态'] == '未匹配']
        
        if search_keyword:
            if '预订人' in display_df.columns:
                # 标准化搜索关键词
                def standardize_search_keyword(keyword):
                    keyword = keyword.strip()
                    if keyword in ['平和', '平哥']:
                        return ['平和', '平哥']  # 返回所有同义词
                    elif keyword in ['刘霞', '刘']:
                        return ['刘霞', '刘']  # 返回刘霞和刘的所有变体
                    elif keyword in ['周', '周思玗']:
                        return ['周', '周思玗']  # 返回周和周思玗的所有变体
                    elif keyword.lower() == 'sk':
                        return ['SK', 'sk', 'Sk', 'sK']  # 返回所有大小写变体
                    else:
                        return [keyword]
                
                search_terms = standardize_search_keyword(search_keyword)
                # 创建搜索条件，匹配任何一个同义词
                search_condition = False
                for term in search_terms:
                    search_condition |= display_df['预订人'].astype(str).str.contains(term, case=False, na=False)
                display_df = display_df[search_condition]
        
        return display_df
    
    def normalize_customer_name(self, name):
        """标准化预订人姓名"""
        if pd.isna(name) or str(name).strip() == '':
            return None
        
        name = str(name).strip()
        
        # 转换为小写进行比较
        name_lower = name.lower()
        
        # 定义姓名映射规则
        name_mappings = {
            'sk': 'SK',  # sk -> SK
            '平': '平哥',  # 平 -> 平哥
            '平哥': '平哥',  # 平哥保持不变
            '周': '周',  # 周保持不变
        }
        
        # 检查是否需要映射
        for key, value in name_mappings.items():
            if name_lower == key.lower():
                return value
        
        # 如果没有特殊映射，返回原始名称（保持原有大小写）
        return name
    
    def get_standardized_customers(self):
        """获取标准化后的预订人列表"""
        if '预订人' not in self.merged_df.columns:
            return []
        
        # 标准化所有预订人姓名
        standardized_names = self.merged_df['预订人'].apply(self.normalize_customer_name)
        standardized_names = standardized_names.dropna().unique()
        
        return sorted([name for name in standardized_names if name])
    
    def show_data_analysis(self):
        """显示数据分析页面"""
        st.header("📈 预订人数据分析")
        
        if self.merged_df.empty:
            st.warning("暂无数据，请先在'文件处理'标签页中上传文件并进行匹配")
            return
        
        # 创建两列布局
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🔍 预订人搜索")
            
            # 获取标准化后的预订人列表
            if '预订人' in self.merged_df.columns:
                all_customers = self.get_standardized_customers()
                
                # 搜索框
                search_customer = st.selectbox(
                    "选择预订人",
                    options=["请选择..."] + all_customers,
                    key="customer_analysis_search"
                )
                
                # 或者输入搜索
                manual_search = st.text_input(
                    "或手动输入预订人姓名",
                    placeholder="输入预订人姓名进行搜索",
                    key="manual_customer_search"
                )
                
                # 确定最终搜索的客户
                target_customer = None
                if manual_search.strip():
                    target_customer = manual_search.strip()
                elif search_customer != "请选择...":
                    target_customer = search_customer
                
                if target_customer:
                    st.success(f"已选择：{target_customer}")
                    
                    # 分析按钮
                    if st.button("📊 开始分析", type="primary", use_container_width=True):
                        st.session_state.analysis_customer = target_customer
                        st.rerun()
            else:
                st.error("数据中未找到'预订人'字段")
        
        with col2:
            st.subheader("📊 分析结果")
            
            # 检查是否有选择的客户进行分析
            if hasattr(st.session_state, 'analysis_customer') and st.session_state.analysis_customer:
                customer_name = st.session_state.analysis_customer
                
                # 筛选该客户的数据（使用标准化姓名匹配）
                standardized_customer_names = self.merged_df['预订人'].apply(self.normalize_customer_name)
                customer_data = self.merged_df[standardized_customer_names == customer_name]
                
                if customer_data.empty:
                    st.warning(f"未找到预订人'{customer_name}'的相关数据")
                else:
                    # 显示基本统计信息
                    st.markdown(f"### 👤 {customer_name} 的预订统计")
                    
                    # 创建指标卡片
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    
                    with metric_col1:
                        total_orders = len(customer_data)
                        st.metric("总预订次数", total_orders)
                    
                    with metric_col2:
                        matched_orders = len(customer_data[customer_data['匹配状态'] == '已匹配'])
                        st.metric("成功匹配", matched_orders)
                    
                    with metric_col3:
                        if matched_orders > 0:
                            match_rate = round((matched_orders / total_orders) * 100, 1)
                            st.metric("匹配率", f"{match_rate}%")
                        else:
                            st.metric("匹配率", "0%")
                    
                    with metric_col4:
                        # 计算总消费金额（仅匹配成功的订单）
                        matched_data = customer_data[customer_data['匹配状态'] == '已匹配']
                        if not matched_data.empty and '支付合计' in matched_data.columns:
                            # 提取支付金额的数字部分
                            amounts = matched_data['支付合计'].astype(str).str.extract(r'([0-9.]+)').astype(float)
                            total_amount = amounts.sum().iloc[0] if not amounts.empty else 0
                            st.metric("总消费金额", f"¥{total_amount:.2f}")
                        else:
                            st.metric("总消费金额", "¥0.00")
                    
                    st.divider()
                    
                    # 可视化图表
                    chart_col1, chart_col2 = st.columns(2)
                    
                    with chart_col1:
                        # 工作日vs周末分析（仅分析已匹配数据）
                        st.markdown("#### 📅 工作日vs周末分析")
                        if '日期' in customer_data.columns:
                            # 只分析已匹配的数据
                            matched_data = customer_data[customer_data['匹配状态'] == '已匹配'].copy()
                            
                            if not matched_data.empty:
                                # 转换日期格式并分析工作日/周末
                                matched_data['日期'] = pd.to_datetime(matched_data['日期'], errors='coerce')
                                customer_data_copy = matched_data.dropna(subset=['日期'])
                            else:
                                customer_data_copy = pd.DataFrame()  # 空数据框
                            
                            if not customer_data_copy.empty:
                                # 添加星期几列 (0=周一, 6=周日)
                                customer_data_copy['weekday'] = customer_data_copy['日期'].dt.dayofweek
                                customer_data_copy['day_type'] = customer_data_copy['weekday'].apply(
                                    lambda x: '周末' if x >= 5 else '工作日'
                                )
                                
                                # 统计工作日vs周末的预订次数
                                day_type_counts = customer_data_copy['day_type'].value_counts()
                                
                                if not day_type_counts.empty:
                                    fig_daytype = px.bar(
                                        x=day_type_counts.index,
                                        y=day_type_counts.values,
                                        title=f"{customer_name} 的工作日vs周末预订分布（已匹配数据）",
                                        labels={'x': '日期类型', 'y': '预订次数'},
                                        color=day_type_counts.index,
                                        color_discrete_map={
                                            '工作日': '#3b82f6',
                                            '周末': '#f59e0b'
                                        }
                                    )
                                    fig_daytype.update_layout(
                                        height=300,
                                        font=dict(family="Microsoft YaHei, SimHei, sans-serif"),
                                        showlegend=False
                                    )
                                    st.plotly_chart(fig_daytype, use_container_width=True)
                                    
                                    # 显示统计信息
                                    workday_count = day_type_counts.get('工作日', 0)
                                    weekend_count = day_type_counts.get('周末', 0)
                                    total_count = workday_count + weekend_count
                                    
                                    if total_count > 0:
                                        workday_pct = round((workday_count / total_count) * 100, 1)
                                        weekend_pct = round((weekend_count / total_count) * 100, 1)
                                        
                                        st.markdown(f"""
                                        **📊 统计摘要（已匹配数据）：**
                                        - 工作日预订：{workday_count}次 ({workday_pct}%)
                                        - 周末预订：{weekend_count}次 ({weekend_pct}%)
                                        """)
                                else:
                                    st.info("暂无有效的已匹配日期数据进行工作日/周末分析")
                            else:
                                st.info("该预订人暂无已匹配的数据，无法进行工作日/周末分析")
                        else:
                            st.info("数据中缺少日期字段，无法进行工作日/周末分析")
                    
                    with chart_col2:
                        # 预订时间趋势图
                        st.markdown("#### 📅 预订时间趋势")
                        if '日期' in customer_data.columns:
                            # 按日期统计预订次数
                            date_counts = customer_data['日期'].value_counts().sort_index()
                            
                            if not date_counts.empty:
                                 fig_line = px.line(
                                     x=date_counts.index,
                                     y=date_counts.values,
                                     title=f"{customer_name} 的预订时间趋势",
                                     labels={'x': '日期', 'y': '预订次数'}
                                 )
                                 fig_line.update_layout(
                                      height=300,
                                      font=dict(family="Microsoft YaHei, SimHei, sans-serif"),
                                      xaxis=dict(
                                          tickformat='%Y年%m月%d日',
                                          tickangle=45
                                      )
                                  )
                                 st.plotly_chart(fig_line, use_container_width=True)
                            else:
                                st.info("暂无日期数据")
                        else:
                            st.info("数据中未包含日期信息")
                    
                    # 桌牌号偏好分析
                    if '桌牌号' in customer_data.columns:
                        st.markdown("#### 🪑 桌牌号偏好分析")
                        table_counts = customer_data['桌牌号'].value_counts().head(10)
                        
                        if not table_counts.empty:
                             fig_bar = px.bar(
                                 x=table_counts.values,
                                 y=table_counts.index,
                                 orientation='h',
                                 title=f"{customer_name} 的桌牌号偏好 (前10)",
                                 labels={'x': '预订次数', 'y': '桌牌号'}
                             )
                             fig_bar.update_layout(
                                 height=400,
                                 font=dict(family="Microsoft YaHei, SimHei, sans-serif")
                             )
                             st.plotly_chart(fig_bar, use_container_width=True)
                    
                    # 详细数据表格
                    st.markdown("#### 📋 详细预订记录")
                    
                    # 选择要显示的列
                    display_columns = ['日期', '桌牌号', '匹配状态', '匹配类型']
                    if '支付合计' in customer_data.columns:
                        display_columns.append('支付合计')
                    if '下单时间' in customer_data.columns:
                        display_columns.append('下单时间')
                    
                    available_columns = [col for col in display_columns if col in customer_data.columns]
                    
                    if available_columns:
                        display_data = customer_data[available_columns].copy()
                        
                        # 按日期排序
                        if '日期' in display_data.columns:
                            display_data = display_data.sort_values('日期', ascending=False)
                        
                        st.dataframe(
                            display_data,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 导出该客户的数据
                        if st.button(f"📥 导出 {customer_name} 的数据", use_container_width=True):
                            # 创建Excel文件
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                display_data.to_excel(writer, sheet_name=f'{customer_name}_预订记录', index=False)
                            
                            excel_data = output.getvalue()
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{customer_name}_预订分析_{timestamp}.xlsx"
                            
                            st.download_button(
                                label=f"下载 {customer_name} 的预订数据",
                                data=excel_data,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning("无可显示的详细数据")
            else:
                st.info("请在左侧选择一个预订人进行分析")
                
                # 显示整体统计概览
                st.markdown("### 📊 整体数据概览")
                
                # 最活跃的预订人Top 10
                if '预订人' in self.merged_df.columns:
                    # 使用标准化后的姓名进行统计
                    standardized_names = self.merged_df['预订人'].apply(self.normalize_customer_name)
                    valid_customers = standardized_names.dropna()
                    top_customers = valid_customers.value_counts().head(10)
                    
                    if not top_customers.empty:
                         st.markdown("#### 🏆 最活跃预订人 (Top 10)")
                         
                         fig_top = px.bar(
                             x=top_customers.values,
                             y=top_customers.index,
                             orientation='h',
                             title="最活跃的预订人排行榜",
                             labels={'x': '预订次数', 'y': '预订人'}
                         )
                         fig_top.update_layout(
                             height=400,
                             font=dict(family="Microsoft YaHei, SimHei, sans-serif")
                         )
                         st.plotly_chart(fig_top, use_container_width=True)

def main():
    # 在嵌入主应用时避免重复设置页面配置
    try:
        st.set_page_config(
            page_title="鹭府预定匹配工具 v2.0",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
    except Exception:
        # 已在主应用中设置过，忽略
        pass
    
    # 简洁现代的CSS样式
    st.markdown("""
    <style>
    .main {
        padding: 1rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #e1e5e9;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 2rem;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        font-weight: 500;
        color: #64748b;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background: transparent;
        color: #0f172a;
        border-bottom-color: #3b82f6;
    }
    .stFileUploader {
        border: 2px dashed #cbd5e1;
        border-radius: 8px;
        padding: 2rem;
        background: #f8fafc;
        transition: all 0.2s ease;
    }
    .stFileUploader:hover {
        border-color: #3b82f6;
        background: #f1f5f9;
    }
    .metric-container {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    .stAlert {
        border-radius: 8px;
        border: none;
    }
    .stAlert[data-baseweb="notification"][kind="success"] {
        background: #ecfdf5;
        color: #059669;
        border-left: 4px solid #059669;
    }
    .stAlert[data-baseweb="notification"][kind="error"] {
        background: #fef2f2;
        color: #dc2626;
        border-left: 4px solid #dc2626;
    }
    .stAlert[data-baseweb="notification"][kind="warning"] {
        background: #fffbeb;
        color: #d97706;
        border-left: 4px solid #d97706;
    }
    .stAlert[data-baseweb="notification"][kind="info"] {
        background: #eff6ff;
        color: #2563eb;
        border-left: 4px solid #2563eb;
    }
    .stDataFrame {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
    }
    h1, h2, h3 {
        color: #0f172a;
        font-weight: 600;
    }
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"] {
        background: #3b82f6;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2563eb;
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 简洁的标题
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #0f172a; font-weight: 600; font-size: 2rem; margin: 0;'>鹭府预定匹配工具</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化应用
    if 'app' not in st.session_state:
        st.session_state.app = ReservationMatcherWeb()
    
    app = st.session_state.app
    
    # 三个主要标签页
    tab1, tab2, tab3 = st.tabs(["📁 文件处理", "📊 结果查看", "📈 数据分析"])
    
    # 标签页内容
    with tab1:
        # 文件上传和数据匹配合并
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📤 文件上传")
            app.load_files()
            
        with col2:
            st.subheader("⚡ 数据匹配")
            
            # 验证文件
            is_valid, message = app.validate_files()
            
            if not is_valid:
                st.warning(message)
            else:
                st.success("文件已就绪")
                
                if st.button("🚀 开始匹配", type="primary", use_container_width=True):
                    with st.spinner("匹配中..."):
                        success, result_message = app.match_data()
                        
                    if success:
                        st.success(result_message)
                        st.info("请切换到'结果查看'标签页")
                    else:
                        st.error(result_message)
    
    with tab2:
        # 查看结果和导出合并
        col1, col2 = st.columns([3, 1])
        
        with col1:
            app.display_results()
            
        with col2:
            st.subheader("📥 导出")
            app.export_results()
    
    with tab3:
        # 数据分析标签页
        app.show_data_analysis()
    


if __name__ == "__main__":
    main()