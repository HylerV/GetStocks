import akshare as ak
import pandas as pd

def calculate_fib_with_dates(hist_hfq):
    """动态识别波段并返回关键日期和价格（后复权）"""
    try:
        hist_sorted = hist_hfq.sort_index(ascending=True)
        
        # 寻找最近显著低点（10日窗口）
        low_roll = hist_sorted['最低'].rolling(10, min_periods=5).min()
        low_candidates = hist_sorted[hist_sorted['最低'] == low_roll]
        if low_candidates.empty:
            return None, None, None, None, None
        
        # 取最后一个低点
        low_date = low_candidates.index[-1]
        prev_low_hfq = round(low_candidates.iloc[-1]['最低'], 2)
        
        # 在低点之后寻找高点
        high_window = hist_sorted.loc[low_date:]
        if len(high_window) < 5:
            return None, None, None, None, None
        
        high_date = high_window['最高'].idxmax()
        prev_high_hfq = round(high_window.loc[high_date, '最高'], 2)
        
        # 计算斐波那契位（后复权）
        fib_hfq = round(prev_low_hfq + (prev_high_hfq - prev_low_hfq) * 0.618, 2)
        
        return low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq
    except:
        return None, None, None, None, None

# 全流程整合
all_stocks = ak.stock_zh_a_spot_em()

# 筛选条件
filtered = all_stocks[
    (all_stocks['流通市值'] / 1e8 >= 15) &  # 流通市值15-100亿
    (all_stocks['流通市值'] / 1e8 <= 100) &
    (all_stocks['最新价'] <= 50) &
    (~all_stocks['名称'].str.contains('ST')) &
    (all_stocks['代码'].astype(str).str.startswith(('600', '601', '603', '605', '000', '001', '002'))) &
    (all_stocks['名称'].str.contains('智能|AI|机器视觉|人工智能|自然语言处理'))
]

print("初步筛选数量:", len(filtered))

results = []
for _, row in filtered.iterrows():
    code = row['代码']
    try:
        # 获取后复权数据（技术分析用）
        hist_hfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").set_index('日期')
        
        # 获取关键日期和价格
        low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq = calculate_fib_with_dates(hist_hfq)
        if not low_date:
            continue
        
        # 获取前复权数据（实际交易价）
        hist_qfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").set_index('日期')
        
        # 映射到除权价
        prev_low_qfq = round(hist_qfq.loc[low_date, '最低'], 2) if low_date in hist_qfq.index else None
        prev_high_qfq = round(hist_qfq.loc[high_date, '最高'], 2) if high_date in hist_qfq.index else None
        
        # 计算除权斐波那契位
        if prev_low_qfq and prev_high_qfq:
            fib_qfq = round(prev_low_qfq + (prev_high_qfq - prev_low_qfq) * 0.618, 2)
        else:
            fib_qfq = None
        
        results.append({
            '代码': code,
            '名称': row['名称'],
            '最新价（除权）': row['最新价'],
            '后复权前低价': prev_low_hfq,
            '后复权前高价': prev_high_hfq,
            '后复权0.618位': fib_hfq,
            '除权前低价': prev_low_qfq,
            '除权前高价': prev_high_qfq,
            '除权0.618位': fib_qfq
        })
    except Exception as e:
        print(f"处理失败 {code}: {e}")

# 结果展示
result_df = pd.DataFrame(results)
print("\n最终分析结果:")
print(result_df[['代码', '名称', '最新价（除权）', 
               '后复权前低价', '后复权前高价', '后复权0.618位',
               '除权前低价', '除权前高价', '除权0.618位']])