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