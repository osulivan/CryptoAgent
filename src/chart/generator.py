"""
K线图生成器
使用mplfinance绘制K线图和技术指标
"""
import io
import base64
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

import mplfinance as mpf
import matplotlib.pyplot as plt

from .indicators import calculate_indicator, get_indicator_config, parse_indicator_name


class ChartGenerator:
    """K线图生成器"""
    
    def __init__(self, save_dir: str = "charts"):
        """
        初始化图表生成器
        
        Args:
            save_dir: 图表保存目录
        """
        self.save_dir = save_dir
        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)
    
    def generate_chart(
        self,
        klines: List[List],
        indicators: Optional[List[str]] = None,
        title: str = "K线图",
        figsize: tuple = (14, 10),
        save_local: bool = True
    ) -> Dict[str, Any]:
        """
        生成K线图，返回base64编码的PNG，并可选择保存到本地
        
        Args:
            klines: OKX返回的K线数据 [[ts, open, high, low, close, vol, volCcy], ...]
            indicators: 要显示的技术指标列表，如 ['sma(20)', 'bollinger', 'rsi']
            title: 图表标题
            figsize: 图表尺寸
            save_local: 是否保存到本地文件
        
        Returns:
            包含base64图片和本地文件路径的字典
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = title.replace(" ", "_").replace("/", "_")
        filename = f"{safe_title}_{timestamp}.png"
        filepath = os.path.join(self.save_dir, filename)
        
        # 1. 转换为DataFrame
        df = self._klines_to_dataframe(klines)
        
        if df.empty:
            raise ValueError("K线数据为空")
        
        # 2. 计算所有指标
        overlay_data = {}  # 主图叠加指标数据 {name: series}
        panel_data = []    # 副图指标数据列表 [(name, config, result), ...]
        indicator_values = {}  # 存储指标的最新数值 {ind_name: value_or_dict}
        
        if indicators:
            for ind_name in indicators:
                name, params = parse_indicator_name(ind_name)
                config = get_indicator_config(ind_name)
                
                # 计算指标
                try:
                    result = calculate_indicator(df, ind_name)
                    # 如果返回 None，说明数据点不足，跳过该指标
                    if result is None:
                        print(f"指标 {ind_name} 数据点不足，已跳过")
                        continue
                except Exception as e:
                    print(f"计算指标 {ind_name} 失败: {e}")
                    continue
                
                # 提取最新数值
                try:
                    if config.get('is_multi'):
                        # 多线指标（如布林带、MACD、KDJ、ADX）
                        if isinstance(result, pd.DataFrame):
                            latest = result.iloc[-1]
                            values = latest.to_dict()
                            
                            # 根据指标类型格式化输出
                            if name in ['bollinger', 'bbands']:
                                # 布林带只显示上中下轨
                                formatted = {}
                                for k, v in values.items():
                                    if 'BBL' in k:
                                        formatted['下轨'] = float(v)
                                    elif 'BBM' in k:
                                        formatted['中轨'] = float(v)
                                    elif 'BBU' in k:
                                        formatted['上轨'] = float(v)
                                indicator_values[ind_name] = formatted
                            elif name in ['macd']:
                                # MACD显示DIF、DEA、柱状图
                                formatted = {}
                                for k, v in values.items():
                                    if 'MACD_' in k and 'h' not in k and 's' not in k:
                                        formatted['DIF'] = float(v)
                                    elif 'MACDh' in k:
                                        formatted['柱状图'] = float(v)
                                    elif 'MACDs' in k:
                                        formatted['DEA'] = float(v)
                                indicator_values[ind_name] = formatted
                            elif name in ['kdj', 'stoch']:
                                # KDJ显示K、D、J（如果有）
                                formatted = {}
                                for k, v in values.items():
                                    if 'STOCHk' in k:
                                        formatted['K'] = float(v)
                                    elif 'STOCHd' in k:
                                        formatted['D'] = float(v)
                                indicator_values[ind_name] = formatted
                            elif name in ['adx']:
                                # ADX显示ADX、+DI、-DI
                                formatted = {}
                                for k, v in values.items():
                                    if k == 'ADX_14':
                                        formatted['ADX'] = float(v)
                                    elif 'DMP' in k:
                                        formatted['+DI'] = float(v)
                                    elif 'DMN' in k:
                                        formatted['-DI'] = float(v)
                                indicator_values[ind_name] = formatted
                            else:
                                indicator_values[ind_name] = {k: float(v) if isinstance(v, (int, float)) else v for k, v in values.items()}
                    else:
                        # 单线指标（如SMA、EMA、RSI、ATR）
                        if isinstance(result, pd.DataFrame):
                            series = result.iloc[:, 0]
                        else:
                            series = result
                        indicator_values[ind_name] = float(series.iloc[-1])
                except Exception as e:
                    print(f"提取指标 {ind_name} 数值失败: {e}")
                
                if config['type'] == 'overlay':
                    # 主图叠加指标（如均线、布林带）
                    overlay_data[ind_name] = (result, config)
                elif config['type'] == 'panel':
                    # 副图指标
                    panel_data.append((ind_name, config, result))
        
        # 3. 准备mplf的addplot列表
        addplots = []
        overlay_labels = []  # 存储主图指标标签
        
        # 处理主图叠加指标
        # 为不同参数的均线定义颜色池
        ma_colors = ['blue', 'red', 'green', 'purple', 'orange', 'cyan', 'magenta', 'brown']
        sma_color_idx = 0
        ema_color_idx = 0
        
        for ind_name, (result, config) in overlay_data.items():
            name, params = parse_indicator_name(ind_name)
            
            if name in ['sma', 'ema']:
                # 移动平均线 - 不同参数使用不同颜色
                length = params.get('length', list(params.values())[0] if params else 20)
                if isinstance(result, pd.DataFrame):
                    series = result.iloc[:, 0]
                else:
                    series = result
                # SMA和EMA分别使用不同的颜色池，避免重复
                if name == 'sma':
                    color = ma_colors[sma_color_idx % len(ma_colors)]
                    sma_color_idx += 1
                else:
                    color = ma_colors[ema_color_idx % len(ma_colors)]
                    ema_color_idx += 1
                label = f"{name.upper()}({length})"
                overlay_labels.append((label, color))
                addplots.append(
                    mpf.make_addplot(series, color=color, width=1.5, panel=0, label=label)
                )
            elif config.get('is_multi'):
                # 多线指标（如布林带）
                if name in ['bollinger', 'bbands']:
                    cols = result.columns
                    lower_col = [c for c in cols if 'BBL' in c][0] if any('BBL' in c for c in cols) else cols[0]
                    middle_col = [c for c in cols if 'BBM' in c][0] if any('BBM' in c for c in cols) else cols[1]
                    upper_col = [c for c in cols if 'BBU' in c][0] if any('BBU' in c for c in cols) else cols[2]
                    # 获取布林带参数用于标签
                    length = params.get('length', 20)
                    std = params.get('std', 2.0)
                    addplots.extend([
                        mpf.make_addplot(result[lower_col], color='blue', width=1.0, linestyle='--', panel=0, label=f'BB Lower({length},{std})'),
                        mpf.make_addplot(result[middle_col], color='orange', width=1.5, panel=0, label=f'BB Middle({length},{std})'),
                        mpf.make_addplot(result[upper_col], color='blue', width=1.0, linestyle='--', panel=0, label=f'BB Upper({length},{std})'),
                    ])
                    # 添加布林带标签到图例列表
                    overlay_labels.append((f'BB Lower({length},{std})', 'blue'))
                    overlay_labels.append((f'BB Middle({length},{std})', 'orange'))
                    overlay_labels.append((f'BB Upper({length},{std})', 'blue'))
        
        # 处理副图指标 - 每个指标一个独立面板
        next_panel = 2  # 从panel 2开始（panel 0是K线，panel 1是成交量）
        num_panels = len(panel_data)
        # 根据面板数量动态调整高度：主图:成交量:副图 = 4:1.5:每个副图1.5
        panel_ratios = [4, 1.5] + [1.5] * num_panels
        
        # 存储每个面板的图例信息 {panel_num: [(label, color), ...]}
        panel_legends = {}
        
        for ind_name, config, result in panel_data:
            name, params = parse_indicator_name(ind_name)
            panel_legends[next_panel] = []
            
            if config.get('is_multi'):
                # 多线指标
                if isinstance(result, pd.DataFrame):
                    cols = result.columns
                    if any('MACD' in c for c in cols):
                        # MACD - 先添加柱体，再添加线条，这样线条会显示在柱体前面
                        macd_col = [c for c in cols if 'MACD_' in c and 'S' not in c][0] if any('MACD_' in c and 'S' not in c for c in cols) else cols[0]
                        signal_col = [c for c in cols if 'MACDs' in c][0] if any('MACDs' in c for c in cols) else cols[1]
                        hist_col = [c for c in cols if 'MACDh' in c][0] if any('MACDh' in c for c in cols) else cols[2]
                        # 分离正负柱体数据
                        hist_positive = result[hist_col].copy()
                        hist_negative = result[hist_col].copy()
                        hist_positive[hist_positive < 0] = 0
                        hist_negative[hist_negative > 0] = 0
                        # 添加MACD标签到图例列表
                        panel_legends[next_panel].append(('MACD Line', 'blue'))
                        panel_legends[next_panel].append(('Signal Line', 'red'))
                        # 第一个addplot设置ylabel，secondary_y=False让标签显示在左边
                        # 零上柱体用红色，零下柱体用绿色（与K线颜色一致）
                        addplots.extend([
                            mpf.make_addplot(hist_positive, panel=next_panel, type='bar', color='#ef5350', alpha=0.6, secondary_y=False),
                            mpf.make_addplot(hist_negative, panel=next_panel, type='bar', color='#26a69a', alpha=0.6, secondary_y=False),
                            mpf.make_addplot(result[macd_col], panel=next_panel, color='blue', ylabel='MACD', width=1.5, secondary_y=False),
                            mpf.make_addplot(result[signal_col], panel=next_panel, color='red', width=1.5, secondary_y=False),
                        ])
                    elif any('STOCH' in c for c in cols):
                        # KDJ
                        k_col = [c for c in cols if 'STOCHk' in c][0] if any('STOCHk' in c for c in cols) else cols[0]
                        d_col = [c for c in cols if 'STOCHd' in c][0] if any('STOCHd' in c for c in cols) else cols[1]
                        panel_legends[next_panel].append(('K', 'blue'))
                        panel_legends[next_panel].append(('D', 'orange'))
                        addplots.extend([
                            mpf.make_addplot(result[k_col], panel=next_panel, color='blue', ylabel='KDJ'),
                            mpf.make_addplot(result[d_col], panel=next_panel, color='orange'),
                        ])
                    elif any('ADX' in c for c in cols):
                        # ADX
                        adx_col = [c for c in cols if 'ADX' in c and 'D' not in c][0] if any('ADX' in c and 'D' not in c for c in cols) else cols[0]
                        dmp_col = [c for c in cols if 'DMP' in c][0] if any('DMP' in c for c in cols) else cols[1]
                        dmn_col = [c for c in cols if 'DMN' in c][0] if any('DMN' in c for c in cols) else cols[2]
                        panel_legends[next_panel].append(('ADX', 'black'))
                        panel_legends[next_panel].append(('+DI', 'green'))
                        panel_legends[next_panel].append(('-DI', 'red'))
                        addplots.extend([
                            mpf.make_addplot(result[adx_col], panel=next_panel, color='black', ylabel='ADX'),
                            mpf.make_addplot(result[dmp_col], panel=next_panel, color='green'),
                            mpf.make_addplot(result[dmn_col], panel=next_panel, color='red'),
                        ])
            else:
                # 单线指标
                color = config.get('color', 'purple')
                ylabel = name.upper() if name else 'IND'
                if isinstance(result, pd.DataFrame):
                    series = result.iloc[:, 0]
                else:
                    series = result
                addplots.append(
                    mpf.make_addplot(series, panel=next_panel, color=color, ylabel=ylabel)
                )
            
            next_panel += 1
        
        # 4. 设置图表样式
        mc = mpf.make_marketcolors(
            up='#ef5350',      # 涨 - 红色
            down='#26a69a',    # 跌 - 绿色
            edge='inherit',
            wick='inherit',
            volume='in'
        )
        
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            gridcolor='lightgray',
            gridaxis='both',
            rc={'font.size': 10}
        )
        
        # 5. 生成图表
        buf = io.BytesIO()
        
        # 根据面板数量动态调整图表高度
        # 基础高度8，每个副图增加1.5高度
        base_height = 8
        dynamic_height = base_height + num_panels * 1.5 if num_panels > 0 else base_height
        dynamic_figsize = (figsize[0], dynamic_height)
        
        # 准备参数
        plot_kwargs = {
            'type': 'candle',
            'style': style,
            'title': title,
            'ylabel': 'Price',
            'volume': True,
            'figsize': dynamic_figsize,
            'panel_ratios': tuple(panel_ratios),
        }
        
        if addplots:
            plot_kwargs['addplot'] = addplots
        
        try:
            # 创建图表并获取figure对象
            fig, axes = mpf.plot(df, **plot_kwargs, returnfig=True)
            
            # 添加主图图例（SMA/EMA标签）
            if overlay_labels:
                ax_main = axes[0]
                legend_lines = []
                legend_labels = []
                for label, color in overlay_labels:
                    line, = ax_main.plot([], [], color=color, linewidth=1.5, label=label)
                    legend_lines.append(line)
                    legend_labels.append(label)
                
                if legend_lines:
                    ax_main.legend(legend_lines, legend_labels, loc='upper left', fontsize=9)
            
            # 为副图面板添加图例（左上角）
            # mplfinance的axes结构比较复杂，需要根据ylabel来找到正确的axes
            # 建立panel_num到axes索引的映射
            panel_to_axes = {}
            for i, ax in enumerate(axes):
                ylabel = ax.get_ylabel()
                # 根据ylabel找到对应的panel
                if 'RSI' in ylabel:
                    panel_to_axes[2] = i  # RSI在panel 2
                elif 'MACD' in ylabel:
                    panel_to_axes[3] = i  # MACD在panel 3
                elif 'KDJ' in ylabel:
                    panel_to_axes[4] = i  # KDJ在panel 4
                elif 'ATR' in ylabel:
                    panel_to_axes[2] = i  # ATR在panel 2
                elif 'ADX' in ylabel:
                    panel_to_axes[3] = i  # ADX在panel 3
                elif 'OBV' in ylabel:
                    panel_to_axes[4] = i  # OBV在panel 4
                elif 'CCI' in ylabel:
                    panel_to_axes[5] = i  # CCI在panel 5
            
            for panel_num, legend_items in panel_legends.items():
                if legend_items and panel_num in panel_to_axes:
                    ax_index = panel_to_axes[panel_num]
                    if ax_index < len(axes):
                        ax_panel = axes[ax_index]
                        legend_lines = []
                        legend_labels = []
                        for label, color in legend_items:
                            line, = ax_panel.plot([], [], color=color, linewidth=1.5, label=label)
                            legend_lines.append(line)
                            legend_labels.append(label)
                        
                        if legend_lines:
                            ax_panel.legend(legend_lines, legend_labels, loc='upper left', fontsize=8)
            
            # 保存图表
            fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
            plt.close(fig)
            
        except Exception as e:
            print(f"绘图错误: {e}")
            # 简化版本重试
            simple_kwargs = {
                'type': 'candle',
                'style': style,
                'title': title,
                'volume': True,
                'savefig': dict(fname=buf, format='png', dpi=120, bbox_inches='tight'),
            }
            mpf.plot(df, **simple_kwargs)
        
        buf.seek(0)
        img_data = buf.read()
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        # 保存到本地文件
        local_path = None
        if save_local:
            try:
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                local_path = filepath
                print(f"图表已保存到: {filepath}")
            except Exception as e:
                print(f"保存图表到本地失败: {e}")
        
        return {
            "base64": img_base64,
            "local_path": local_path,
            "filename": filename if save_local else None,
            "indicator_values": indicator_values
        }
    
    def _klines_to_dataframe(self, klines: List[List]) -> pd.DataFrame:
        """
        将OKX K线数据转换为DataFrame
        
        OKX格式: [[timestamp, open, high, low, close, vol, volCcy, volCcyQuote, confirm], ...]
        时间戳是毫秒
        """
        if not klines:
            return pd.DataFrame()
        
        # OKX返回的数据是倒序的（最新在前），需要反转
        klines = klines[::-1]
        
        # OKX可能返回7列或9列数据，只取前7列
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'
        ])
        
        # 只保留需要的列
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy']]
        
        # 转换数据类型
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'volCcy']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 时间戳转日期 (毫秒 -> 秒)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # mplfinance需要特定列名
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        return df
    
    def get_latest_data_summary(self, klines: List[List]) -> Dict[str, Any]:
        """获取最新数据的摘要信息"""
        if not klines:
            return {}
        
        latest = klines[0]  # OKX返回最新数据在第一个
        
        return {
            "latest_price": float(latest[4]),
            "latest_open": float(latest[1]),
            "latest_high": float(latest[2]),
            "latest_low": float(latest[3]),
            "latest_volume": float(latest[6]),
            "data_points": len(klines),
            "timestamp": int(latest[0]),
            "timestamp_iso": pd.to_datetime(int(latest[0]), unit='ms').isoformat(),
        }
