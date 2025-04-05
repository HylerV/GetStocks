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
            # 添加全市场选项
            boards.append({
                'code': 'ALL',
                'name': '全市场'
            })
            # 添加其他板块
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

def get_all_market_stocks():
    """获取全市场股票数据"""
    try:
        df = ak.stock_zh_a_spot_em()
        stocks = []
        for _, row in df.iterrows():
            # 过滤条件：主板股票，非ST，流通市值15-100亿，股价<=50
            if (row['代码'].startswith(('600', '000', '001')) and 
                'ST' not in row['名称'] and 
                15e8 <= float(row['流通市值']) <= 100e8 and 
                float(row['最新价']) <= 50):
                stocks.append({
                    'code': row['代码'],
                    'name': row['名称'],
                    'current_price': float(row['最新价']),
                    'market_cap': round(float(row['流通市值'])/1e8, 2)
                })
        return stocks
    except Exception as e:
        print(f"获取全市场数据失败: {str(e)}")
        return []

def get_board_stocks(board_code):
    """多源成分股获取（优先级：akshare > 东方财富 > 麦蕊智数）"""
    # 全市场模式
    if board_code == 'ALL':
        return get_all_market_stocks()
    
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
                # 过滤条件：主板股票，非ST，流通市值15-100亿，股价<=50
                if (row['股票代码'].startswith(('600', '000', '001')) and 
                    'ST' not in row['名称'] and 
                    15e8 <= float(row['流通市值']) <= 100e8 and 
                    float(row['最新价']) <= 50):
                    stocks.append({
                        'code': row['股票代码'],
                        'name': row['名称'] if '名称' in df.columns else '',
                        'current_price': float(row['最新价']) if '最新价' in df.columns else 0,
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
            df = ak.stock_zh_a_spot_em()
            for code in codes:
                try:
                    stock_info = df[df['代码'] == code].iloc[0]
                    # 过滤条件：主板股票，非ST，流通市值15-100亿，股价<=50
                    if (code.startswith(('600', '000', '001')) and 
                        'ST' not in stock_info['名称'] and 
                        15e8 <= float(stock_info['流通市值']) <= 100e8 and 
                        float(stock_info['最新价']) <= 50):
                        stocks.append({
                            'code': code,
                            'name': stock_info['名称'],
                            'current_price': float(stock_info['最新价']),
                            'market_cap': round(float(stock_info['流通市值'])/1e8, 2)
                        })
                except:
                    continue
            return stocks
    except Exception as e:
        print(f"[备用1] 东方财富失败: {str(e)}")
    
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

def get_stock_history(stock_code, days=120):
    """获取股票历史数据"""
    try:
        # 获取后复权数据
        df_hfq = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="hfq")
        df_hfq = df_hfq.tail(days)  # 获取最近N天数据
        
        # 转换为K线图所需格式
        kdata = []
        for _, row in df_hfq.iterrows():
            kdata.append({
                'time': row['日期'].strftime('%Y-%m-%d'),
                'open': float(row['开盘']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'close': float(row['收盘']),
                'volume': float(row['成交量'])
            })
        return kdata
    except Exception as e:
        print(f"获取历史数据失败: {str(e)}")
        return [] 