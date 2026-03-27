"""
技术指标计算模块
使用pandas-ta库
支持动态参数格式，如：sma(20), ema(12), bbands(20,2.0)
"""
import re
import pandas as pd
import pandas_ta as ta


def parse_indicator_name(indicator_str: str):
    """
    解析指标名称，支持格式：
    - "sma" → ('sma', {})
    - "sma(20)" → ('sma', {'length': 20})
    - "bbands(20,2.0)" → ('bbands', {'length': 20, 'std': 2.0})
    - "macd(12,26,9)" → ('macd', {'fast': 12, 'slow': 26, 'signal': 9})
    """
    match = re.match(r'^(\w+)(\((.*)\))?$', indicator_str)
    if not match:
        return indicator_str, {}
    
    name = match.group(1)
    args_str = match.group(3)
    
    if not args_str:
        return name, {}
    
    # 解析参数
    args = []
    kwargs = {}
    parts = args_str.split(',')
    
    for i, part in enumerate(parts):
        part = part.strip()
        if '=' in part:
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip()
            # 尝试转换类型
            if val.lower() in ('true', 'false'):
                kwargs[key] = val.lower() == 'true'
            elif '.' in val:
                try:
                    kwargs[key] = float(val)
                except ValueError:
                    kwargs[key] = val
            else:
                try:
                    kwargs[key] = int(val)
                except ValueError:
                    kwargs[key] = val
        else:
            # 位置参数
            if '.' in part:
                try:
                    args.append(float(part))
                except ValueError:
                    args.append(part)
            else:
                try:
                    args.append(int(part))
                except ValueError:
                    args.append(part)
    
    # 将位置参数映射到关键字参数
    # 根据指标类型定义参数名
    param_mapping = {
        'sma': ['length'],
        'ema': ['length'],
        'rsi': ['length'],
        'atr': ['length'],
        'cci': ['length'],
        'willr': ['length'],
        'adx': ['length'],
        'aroon': ['length'],
        'mfi': ['length'],
        'bbands': ['length', 'std'],
        'bollinger': ['length', 'std'],
        'macd': ['fast', 'slow', 'signal'],
        'kdj': ['k', 'd', 'smooth_k'],
        'stoch': ['k', 'd', 'smooth_k'],
    }
    
    if name in param_mapping and args:
        param_names = param_mapping[name]
        for i, arg in enumerate(args):
            if i < len(param_names):
                kwargs[param_names[i]] = arg
    elif args:
        # 通用处理：使用arg0, arg1等作为键
        for i, arg in enumerate(args):
            kwargs[f'arg{i}'] = arg
    
    return name, kwargs


def calculate_indicator(df: pd.DataFrame, indicator_str: str):
    """
    计算技术指标，支持动态参数
    
    Args:
        df: 包含OHLCV的DataFrame
        indicator_str: 指标名称，如 "sma(20)", "ema(12)"
    
    Returns:
        计算后的指标DataFrame或Series
    """
    name, kwargs = parse_indicator_name(indicator_str)
    
    # 检查数据点是否足够计算指标，不足则返回 None（不显示该指标）
    data_length = len(df)
    if name in ['sma', 'ema']:
        length = kwargs.get('length', 20)
        if data_length < length:
            return None
    elif name in ['rsi', 'atr', 'cci', 'willr', 'adx', 'aroon', 'mfi']:
        length = kwargs.get('length', 14)
        if data_length < length:
            return None
    elif name in ['bbands', 'bollinger']:
        length = kwargs.get('length', 20)
        if data_length < length:
            return None
    elif name == 'macd':
        slow = kwargs.get('slow', 26)
        if data_length < slow:
            return None
    elif name in ['kdj', 'stoch']:
        k = kwargs.get('k', 9)
        if data_length < k:
            return None
    
    # 指标映射（基础版本）
    indicator_maps = {
        # 移动平均线
        'sma': lambda df, **kw: df.ta.sma(**kw) if kw else df.ta.sma(length=20),
        'ema': lambda df, **kw: df.ta.ema(**kw) if kw else df.ta.ema(length=20),
        
        # 布林带
        'bbands': lambda df, **kw: df.ta.bbands(**kw) if kw else df.ta.bbands(length=20, std=2.0),
        'bollinger': lambda df, **kw: df.ta.bbands(**kw) if kw else df.ta.bbands(length=20, std=2.0),
        
        # 动量指标
        'rsi': lambda df, **kw: df.ta.rsi(**kw) if kw else df.ta.rsi(length=14),
        'macd': lambda df, **kw: df.ta.macd(**kw) if kw else df.ta.macd(fast=12, slow=26, signal=9),
        'kdj': lambda df, **kw: df.ta.stoch(**kw) if kw else df.ta.stoch(k=9, d=3, smooth_k=3),
        'stoch': lambda df, **kw: df.ta.stoch(**kw) if kw else df.ta.stoch(k=9, d=3, smooth_k=3),
        'cci': lambda df, **kw: df.ta.cci(**kw) if kw else df.ta.cci(length=20),
        'willr': lambda df, **kw: df.ta.willr(**kw) if kw else df.ta.willr(length=14),
        
        # 波动率指标
        'atr': lambda df, **kw: df.ta.atr(**kw) if kw else df.ta.atr(length=14),
        
        # 趋势指标
        'adx': lambda df, **kw: df.ta.adx(**kw) if kw else df.ta.adx(length=14),
        'aroon': lambda df, **kw: df.ta.aroon(**kw) if kw else df.ta.aroon(length=14),
        
        # 成交量指标
        'obv': lambda df, **kw: df.ta.obv(**kw),
        'vwap': lambda df, **kw: df.ta.vwap(**kw),
        'mfi': lambda df, **kw: df.ta.mfi(**kw) if kw else df.ta.mfi(length=14),
    }
    
    if name in indicator_maps:
        return indicator_maps[name](df, **kwargs)
    else:
        raise ValueError(f"不支持的指标: {name}")


def get_indicator_config(indicator_str: str):
    """
    获取指标配置（用于绘图）
    
    Returns:
        {'type': 'overlay'/'panel', 'panel': int, 'color': str, ...}
    """
    name, _ = parse_indicator_name(indicator_str)
    
    # 指标配置
    configs = {
        # 移动平均线
        'sma': {'type': 'overlay', 'color': 'blue'},
        'ema': {'type': 'overlay', 'color': 'orange'},
        
        # 布林带
        'bbands': {'type': 'overlay', 'is_multi': True},
        'bollinger': {'type': 'overlay', 'is_multi': True},
        
        # 动量指标
        'rsi': {'type': 'panel', 'panel': 2, 'color': 'purple'},
        'macd': {'type': 'panel', 'panel': 2, 'is_multi': True},
        'kdj': {'type': 'panel', 'panel': 2, 'is_multi': True},
        'stoch': {'type': 'panel', 'panel': 2, 'is_multi': True},
        'cci': {'type': 'panel', 'panel': 3, 'color': 'blue'},
        'willr': {'type': 'panel', 'panel': 3, 'color': 'red'},
        
        # 波动率指标
        'atr': {'type': 'panel', 'panel': 3, 'color': 'brown'},
        
        # 趋势指标
        'adx': {'type': 'panel', 'panel': 2, 'is_multi': True},
        'aroon': {'type': 'panel', 'panel': 2, 'is_multi': True},
        
        # 成交量指标
        'obv': {'type': 'panel', 'panel': 2, 'color': 'green'},
        'vwap': {'type': 'overlay', 'color': 'purple'},
        'mfi': {'type': 'panel', 'panel': 2, 'color': 'orange'},
    }
    
    return configs.get(name, {'type': 'panel', 'panel': 2, 'color': 'gray'})


# 保留旧的接口，向后兼容
INDICATOR_FUNCTIONS = {
    'ma5': lambda df: df.ta.sma(length=5),
    'ma10': lambda df: df.ta.sma(length=10),
    'ma20': lambda df: df.ta.sma(length=20),
    'ma60': lambda df: df.ta.sma(length=60),
    'ema12': lambda df: df.ta.ema(length=12),
    'ema26': lambda df: df.ta.ema(length=26),
    'bollinger': lambda df: df.ta.bbands(length=20, std=2.0),
    'rsi': lambda df: df.ta.rsi(length=14),
    'macd': lambda df: df.ta.macd(fast=12, slow=26, signal=9),
    'kdj': lambda df: df.ta.stoch(k=9, d=3, smooth_k=3),
    'atr': lambda df: df.ta.atr(length=14),
}
