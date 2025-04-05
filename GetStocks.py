import akshare as ak
import pandas as pd
import requests
import time
from retrying import retry

# ======================
# 配置参数
# ======================
MAIRUI_LICENSE = "F49B3680-B2E3-4466-8183-E9EDFF77A987"  # 替换为实际授权码

EASTMONEY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Referer': 'http://quote.eastmoney.com/'
}


def get_all_boards():
    """获取有效板块列表（兼容处理）"""
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def fetch():
        try:
            df = ak.stock_board_concept_name_em()
            # 清洗数据确保代码格式正确
            df = df[['板块名称', '板块代码']].dropna()
            df['板块代码'] = df['板块代码'].apply(lambda x: f"BK{x.split('.')[0]}" if '.' in x else x)
            # 转换为API需要的格式
            boards = []
            for _, row in df[df['板块代码'].str.startswith('BK')].iterrows():
                boards.append({
                    'code': row['板块代码'],
                    'name': row['板块名称']
                })
            return boards
        except Exception as e:
            print(f"板块数据异常: {str(e)}")
            return []
    
    try:
        return fetch()
    except:
        return []
    
def get_board_stocks(board_code):
    """多源成分股获取（优先级：akshare > 东方财富 > 麦蕊智数）"""
    stocks = []

    # 验证板块代码
    if not board_code.startswith("BK"):
        print(f"⚠️ 无效板块代码: {board_code}")
        return []
    
    print(f"\n{'='*30}\n正在获取 [{board_code}] 成分股")
    
    # 方案一：使用akshare接口
    try:
        df = ak.stock_board_concept_cons_em(symbol=board_code)
        if not df.empty:
            print("[主接口] akshare获取成功")
            code_col = 'symbol' if 'symbol' in df.columns else '股票代码'
            df['股票代码'] = df[code_col].astype(str).str.zfill(6)
            # 转换为API需要的格式
            for _, row in df.iterrows():
                stocks.append({
                    'code': row['股票代码'],
                    'name': row['名称'] if '名称' in df.columns else '',
                    'current_price': row['最新价'] if '最新价' in df.columns else 0,
                    'market_cap': round(float(row['流通市值'])/1e8, 2) if '流通市值' in df.columns else 0
                })
            return stocks
    except Exception as e:
        print(f"[主接口] akshare失败: {str(e)}")
    
    # 方案二：东方财富直接接口
    try:
        codes = fetch_eastmoney(board_code)
        if codes:
            print("[备用1] 东方财富获取成功")
            # 获取股票详细信息
            stocks = []
            for code in codes:
                try:
                    stock_info = ak.stock_zh_a_spot_em()
                    stock_info = stock_info[stock_info['代码'] == code].iloc[0]
                    stocks.append({
                        'code': code,
                        'name': stock_info['名称'],
                        'current_price': stock_info['最新价'],
                        'market_cap': round(float(stock_info['流通市值'])/1e8, 2)
                    })
                except:
                    continue
            return stocks
    except Exception as e:
        print(f"[备用1] 东方财富失败: {str(e)}")
    
    # 方案三：麦蕊智数接口
    try:
        api_url = f"http://api.mairuiapi.com/concept/hold/{MAIRUI_LICENSE}"
        params = {"bkdm": board_code[2:], "market": "cn"}
        
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0:
            for item in data:
                if 'dm' in item:
                    try:
                        code = item['dm']
                        stock_info = ak.stock_zh_a_spot_em()
                        stock_info = stock_info[stock_info['代码'] == code].iloc[0]
                        stocks.append({
                            'code': code,
                            'name': stock_info['名称'],
                            'current_price': stock_info['最新价'],
                            'market_cap': round(float(stock_info['流通市值'])/1e8, 2)
                        })
                    except:
                        continue
            print(f"成功获取成分股数量：{len(stocks)}")
        else:
            print("⚠️ 接口返回空数据")
            
    except Exception as e:
        print(f"成分股获取失败: {str(e)}")
    
    return stocks

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def fetch_eastmoney(board_code):
    """东方财富直接接口（动态参数）"""
    numeric_code = board_code[2:]  # 去除BK前缀
    url = "http://62.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "500",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9cern",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": f"b:{numeric_code}",
        "fields": "f12,f14",
        "_": int(time.time()*1000)  # 动态时间戳防缓存
    }
    
    response = requests.get(url, params=params, headers=EASTMONEY_HEADERS)
    response.raise_for_status()
    data = response.json()
    
    if data.get('data', {}).get('diff'):
        return [item["f12"] for item in data["data"]["diff"]]
    return []

@retry(stop_max_attempt_number=3, wait_fixed=3000)
def fetch_mairui_concept(board_code):
    """根据麦芯文档获取板块成分股"""
    api_url = f"http://api.mairuiapi.com/concept/hold/{MAIRUI_LICENSE}"
    params = {
        "bkdm": board_code[2:],  # 去除BK前缀
        "market": "cn"
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # 解析数据（根据实际返回结构调整）
        if isinstance(data, list):
            return [item['dm'] for item in data if 'dm' in item]
        return []
    except Exception as e:
        print(f"麦蕊接口异常: {str(e)}")
        return []

def calculate_fib_with_dates(hist_data):
    """动态识别波段"""
    try:
        if not all(col in hist_data.columns for col in ['low', 'high']):
            raise ValueError("历史数据缺少必要列")
        
        hist_sorted = hist_data.sort_index(ascending=True)
        
        # 寻找最近显著低点
        low_roll = hist_sorted['low'].rolling(10, min_periods=5).min()
        low_candidates = hist_sorted[hist_sorted['low'] == low_roll]
        
        if low_candidates.empty:
            return None, None, None, None, None
            
        low_date = low_candidates.index[-1]
        prev_low = round(low_candidates.iloc[-1]['low'], 2)
        
        # 在低点之后寻找高点
        high_window = hist_sorted.loc[low_date:]
        if len(high_window) < 5:
            return None, None, None, None, None
            
        high_date = high_window['high'].idxmax()
        prev_high = round(high_window.loc[high_date, 'high'], 2)
        
        fib_level = round(prev_low + (prev_high - prev_low) * 0.618, 2)
        return low_date, high_date, prev_low, prev_high, fib_level
    except Exception as e:
        print(f"波段计算错误: {str(e)}")
        return None, None, None, None, None

def get_hist_data(symbol, adjust_type):
    """获取历史数据"""
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            adjust=adjust_type
        )
        return df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close'
        }).set_index('date')
    except Exception as e:
        print(f"历史数据获取失败: {symbol} {str(e)[:50]}")
        return None

def select_board():
    """增强版板块选择（增加全市场模式）"""
    boards = get_all_boards()
    
    print("\n操作指引：")
    print("- 输入板块名称进行筛选")
    print("- 输入 * 进行全市场筛选")
    print("- 输入 q 退出程序")
    
    while True:
        keyword = input("\n请输入操作指令:").strip()
        
        # 全市场模式
        if keyword == "*":
            return {"模式": "全市场"}
        
        # 退出指令
        if keyword.lower() == 'q':
            return None
        
        # 板块筛选模式
        matched = boards[boards['板块名称'].str.contains(keyword, case=False)]
        if len(matched) == 1:
            selected = matched.iloc[0]
            if selected['板块代码'].startswith("BK"):
                return selected.to_dict()
            print("⚠️ 无效板块代码格式")
        elif len(matched) > 1:
            print(f"找到{len(matched)}个匹配项：")
            print(matched['板块名称'].tolist())
        else:
            print("⚠️ 未找到相关板块")

def main():
    selection = select_board()
    if not selection:
        return
    
    # 全市场模式处理
    if "模式" in selection:
        print("\n✅ 当前模式：全市场筛选")
        try:
            all_stocks = ak.stock_zh_a_spot_em()
            all_stocks['代码'] = all_stocks['代码'].astype(str).str.zfill(6)
            board_codes = all_stocks['代码'].tolist()
        except Exception as e:
            print(f"全市场数据获取失败: {str(e)}")
            return
    else:
        # 原有板块处理逻辑
        print(f"\n✅ 当前板块：{selection['板块名称']}")
        board_stocks = get_board_stocks(selection['板块代码'])
        board_codes = board_stocks['股票代码'].tolist() if not board_stocks.empty else []
        if not board_codes:
            print("⚠️ 成分股获取失败，自动切换至全市场模式")
            all_stocks = ak.stock_zh_a_spot_em()
            board_codes = all_stocks['代码'].tolist()

    # 统一筛选条件
    filtered = all_stocks[
        (all_stocks['代码'].isin(board_codes)) &
        (all_stocks['流通市值'].between(15e8, 100e8)) &  # 流通市值15-100亿
        (all_stocks['最新价'] <= 50) &                  # 股价不超过50元
        (~all_stocks['名称'].str.contains('ST')) &     # 排除ST股
        (all_stocks['代码'].str[:3].isin(['600', '000', '001']))  # 主板股票
    ]
    
    print(f"\n筛选结果：{len(filtered)}只")
    if not filtered.empty:
        print("候选股示例：")
        print(filtered[['代码', '名称', '最新价', '流通市值']].head(3))
    
    # 技术分析
    results = []
    for _, row in filtered.iterrows():
        code = row['代码']
        name = row['名称']
        print(f"\n分析中：{code} {name}...")
        
        result = {
            '代码': code,
            '名称': name,
            '最新价': row['最新价'],
            '流通市值(亿)': round(row['流通市值']/1e8, 2),
            '突破状态': '否'  # 默认状态
        }

        try:
            hist_hfq = get_hist_data(code, "hfq")
            hist_qfq = get_hist_data(code, "qfq")

            if hist_hfq is None or hist_qfq is None:
                raise ValueError("历史数据不全")

            if hist_hfq is None or hist_hfq.empty:
                raise ValueError("无有效历史数据")
            
            # 对齐日期索引
            common_dates = hist_hfq.index.intersection(hist_qfq.index)
            hist_hfq = hist_hfq.loc[common_dates]
            hist_qfq = hist_qfq.loc[common_dates]
                
            fib_data = calculate_fib_with_dates(hist_hfq)
            if not fib_data[0]:
                print(f"{code} 未找到有效波段")
                results.append(result)  # 仍然记录
                continue

            low_date, high_date, hfq_low, hfq_high, hfq_fib = fib_data
                
            hist_qfq = get_hist_data(code, "qfq")

            # if hist_qfq is None or hist_qfq.empty:
            #     raise ValueError("无前复权数据")
            
            # 验证日期有效性
            if low_date not in hist_qfq.index or high_date not in hist_qfq.index:
                print(f"{code} 关键日期缺失")
                results.append(result)
                continue
                
            qfq_low = round(hist_qfq.loc[low_date, 'low'], 2)
            qfq_high = round(hist_qfq.loc[high_date, 'high'], 2)
            qfq_fib = round(qfq_low + (qfq_high - qfq_low) * 0.618, 2)
            
            results.append({
                '代码': code,
                '名称': name,
                '最新价': row['最新价'],
                '流通市值(亿)': round(row['流通市值']/1e8, 2),
                '后复权低位': hfq_low,
                '后复权高位': hfq_high,
                '后复权0.618': hfq_fib,
                '前复权低位': qfq_low,
                '前复权高位': qfq_high,
                '前复权0.618': qfq_fib,
                '突破状态': '是' if (qfq_fib and row['最新价'] > qfq_fib) else '否'
            })
        except Exception as e:
            print(f"分析失败：{str(e)[:50]}")
            results.append({
                '代码': code,
                '名称': name,
                '错误信息': str(e)[:50]
            })
    
    # 输出结果
    if results:
        result_df = pd.DataFrame(results)
        print("\n最终分析结果：")
        print(result_df)
    else:
        print("⚠️ 所有股票分析失败")

if __name__ == "__main__":
    print("当前环境检测：")
    print(f"- 授权码状态: {'已配置' if MAIRUI_LICENSE != 'YOUR_LICENSE_KEY' else '未配置'}")
    main()