import akshare as ak
import pandas as pd

def get_all_boards():
    return ak.stock_board_concept_name_em()[['板块名称', '板块代码']]

def calculate_fib_with_dates(hist_hfq):
    """动态识别波段（后复权）"""
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
        
        # 计算斐波那契位
        fib_hfq = round(prev_low_hfq + (prev_high_hfq - prev_low_hfq) * 0.618, 2)
        
        return low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq
    except:
        return None, None, None, None, None
    
def select_board():
    """修复版板块选择函数"""
    boards = get_all_boards()
    
    print("\n可用板块示例：")
    print(boards['板块名称'].head(20).tolist())
    
    while True:
        keyword = input("\n请输入板块关键字（输入q退出）:").strip()
        if keyword.lower() == 'q':
            return None  # 明确返回None
        
        matched = boards[boards['板块名称'].str.contains(keyword)]
        if len(matched) == 0:
            print("⚠️ 未找到相关板块")
            return None  # 明确返回None
        elif len(matched) == 1:
            return matched.iloc[0].to_dict()  # 转换为字典
        else:
            print(f"找到{len(matched)}个匹配项：")
            print(matched['板块名称'].tolist())
            print("请精确输入关键字")

def main():
    board_info = select_board()
    # 统一判断返回值是否为None
    if board_info is None:
        print("退出程序")
        return
    
    # 访问字典值
    print(f"\n✅ 当前板块：{board_info['板块名称']}")
    board_code = board_info['板块代码']
    
    # 获取成分股
    try:
        board_stocks = ak.stock_board_concept_cons_em(symbol=board_code)
        board_codes = board_stocks['代码'].tolist()
        print(f"原始成分股数量：{len(board_codes)}")
    except Exception as e:
        print(f"❌ 获取成分股失败：{e}")
        return
    
    # 获取全市场数据
    all_stocks = ak.stock_zh_a_spot_em()
    
    # 筛选条件
    filtered = all_stocks[
        (all_stocks['代码'].isin(board_codes)) &
        (all_stocks['流通市值'] / 1e8 >= 15) &
        (all_stocks['流通市值'] / 1e8 <= 100) &
        (all_stocks['最新价'] <= 50) &
        (~all_stocks['名称'].str.contains('ST')) &
        (all_stocks['代码'].astype(str).str.startswith(('6', '000')))
    ]
    print(f"\n初步筛选数量：{len(filtered)}")
    
    if len(filtered) == 0:
        print("❌ 筛选条件过严，请调整以下条件：")
        print("- 流通市值范围\n- 股价限制\n- 主板要求")
        return
    
    print("\n候选股示例：")
    print(filtered[['代码', '名称', '最新价', '流通市值']].head())
    
    # 技术分析（保留所有字段）
    results = []
    for _, row in filtered.iterrows():
        code = row['代码']
        print(f"\n处理中：{code} {row['名称']}...")
        try:
            hist_hfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").set_index('日期')
            low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq = calculate_fib_with_dates(hist_hfq)
            
            if not low_date:
                print(f"{code} 未找到有效波段")
                continue
                
            # 前复权映射
            hist_qfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").set_index('日期')
            prev_low_qfq = hist_qfq.loc[low_date, '最低'] if low_date in hist_qfq.index else None
            prev_high_qfq = hist_qfq.loc[high_date, '最高'] if high_date in hist_qfq.index else None
            fib_qfq = round(prev_low_qfq + (prev_high_qfq - prev_low_qfq)*0.618, 2) if all([prev_low_qfq, prev_high_qfq]) else None
            
            results.append({
                '代码': code,
                '名称': row['名称'],
                '最新价（除权）': row['最新价'],
                '流通市值(亿)': round(row['流通市值']/1e8, 2),
                '后复权前低价': prev_low_hfq,
                '后复权前高价': prev_high_hfq,
                '后复权0.618位': fib_hfq,
                '除权前低价': prev_low_qfq,
                '除权前高价': prev_high_qfq,
                '除权0.618位': fib_qfq,
                '突破状态': '是' if (fib_qfq and row['最新价'] > fib_qfq) else '否'
            })
        except Exception as e:
            print(f"❌ 处理失败：{str(e)[:50]}...")
            results.append({
                '代码': code,
                '名称': row['名称'],
                '错误信息': str(e)[:50]
            })
    
    # 结果输出
    if results:
        result_df = pd.DataFrame(results)
        print("\n最终分析结果：")
        print(result_df)
    else:
        print("⚠️ 所有股票分析失败，请检查网络或数据源")

if __name__ == "__main__":
    main()