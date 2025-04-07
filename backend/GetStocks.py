import akshare as ak
import pandas as pd
import requests
import time
from retrying import retry
import logging
import json
import traceback

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置参数
MAIRUI_LICENSE = "F49B3680-B2E3-4466-8183-E9EDFF77A987"
EASTMONEY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Referer': 'http://quote.eastmoney.com/'
}

def get_all_boards():
    """获取有效板块列表（兼容处理）"""
    logger.info("=== 开始获取板块列表 ===")
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def fetch():
        try:
            logger.info("获取板块数据中...")
            df = ak.stock_board_concept_name_em()
            logger.info(f"原始板块数据: {len(df)}行")
            
            # 清洗数据确保代码格式正确
            df = df[['板块名称', '板块代码']].dropna()
            df['板块代码'] = df['板块代码'].apply(lambda x: f"BK{x.split('.')[0]}" if '.' in x else x)
            
            # 转换为API需要的格式
            boards = []
            # 添加全市场选项
            boards.append({
                'code': 'ALL',
                'name': '全市场',
                'type': 'market'
            })
            
            # 添加其他板块
            for _, row in df[df['板块代码'].str.startswith('BK')].iterrows():
                boards.append({
                    'code': row['板块代码'],
                    'name': row['板块名称'],
                    'type': 'board'
                })
            
            logger.info(f"处理后板块数量: {len(boards)}")
            if boards:
                logger.info(f"样例板块: {boards[0] if boards else '无'}")
            return boards
        except Exception as e:
            logger.error(f"板块数据异常: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    try:
        boards = fetch()
        logger.info(f"获取板块列表完成: {len(boards)}个")
        return boards
    except:
        logger.error("获取板块列表失败")
        return []

def get_all_market_stocks():
    """获取全市场股票数据"""
    logger.info("=== 开始获取全市场股票 ===")
    
    try:
        logger.info("正在获取A股列表...")
        df = ak.stock_zh_a_spot_em()
        logger.info(f"A股列表获取成功: {len(df)}行")
        
        if df.empty:
            logger.warning("A股列表为空")
            return []
            
        # 确保代码格式正确
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        
        # 应用筛选条件
        start_count = len(df)
        logger.info(f"原始股票数量: {start_count}")
        
        filtered_df = df[
            (df['代码'].str.startswith(('600', '000', '001'))) &  # 主板股票
            (~df['名称'].str.contains('ST')) &                    # 非ST股票
            (df['流通市值'].astype(float).between(15e8, 100e8)) & # 流通市值15-100亿
            (df['最新价'].astype(float) <= 50)                    # 股价不超过50元
        ]
        
        filtered_count = len(filtered_df)
        logger.info(f"筛选后股票数量: {filtered_count}，筛选率: {filtered_count/start_count:.2%}")
        
        # 转换为API格式
        stocks = []
        for _, row in filtered_df.iterrows():
            try:
                stocks.append({
                    'code': row['代码'],
                    'name': row['名称'],
                    'current_price': float(row['最新价']),
                    'market_cap': round(float(row['流通市值'])/1e8, 2),
                    'type': 'stock'
                })
            except Exception as e:
                logger.error(f"处理股票数据失败 {row['代码']}: {str(e)}")
                continue
        
        logger.info(f"全市场模式: 共获取{len(stocks)}只股票")
        if stocks:
            logger.info(f"样例股票: {stocks[0] if stocks else '无'}")
        return stocks
    except Exception as e:
        logger.error(f"获取全市场数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def get_board_stocks(board_code):
    """多源成分股获取（优先级：akshare > 东方财富 > 麦蕊智数）"""
    logger.info(f"=== 开始获取板块[{board_code}]成分股 ===")
    
    # 全市场模式
    if board_code == 'ALL':
        logger.info("检测到全市场模式，切换到全市场获取")
        return get_all_market_stocks()
    
    # 验证板块代码
    if not board_code.startswith("BK"):
        logger.error(f"无效板块代码: {board_code}")
        return []
    
    # 方案一：使用akshare接口
    try:
        logger.info("[主接口] 尝试使用akshare获取成分股")
        df = ak.stock_board_concept_cons_em(symbol=board_code)
        
        if not df.empty:
            logger.info(f"[主接口] akshare获取成功: {len(df)}只股票")
            
            # 转换为API需要的格式
            stocks = []
            for _, row in df.iterrows():
                try:
                    code = row['代码'] if '代码' in df.columns else row['股票代码'] if '股票代码' in df.columns else row['symbol']
                    code = str(code).zfill(6)
                    
                    # 过滤条件：主板股票，非ST，流通市值15-100亿，股价<=50
                    if (code.startswith(('600', '000', '001')) and 
                        'ST' not in row['名称'] and 
                        15e8 <= float(row['流通市值']) <= 100e8 and 
                        float(row['最新价']) <= 50):
                        
                        stocks.append({
                            'code': code,
                            'name': row['名称'],
                            'current_price': float(row['最新价']),
                            'market_cap': round(float(row['流通市值'])/1e8, 2),
                            'type': 'stock'
                        })
                except Exception as e:
                    logger.error(f"处理股票[{code if 'code' in locals() else '未知'}]数据失败: {str(e)}")
                    continue
            
            logger.info(f"[主接口] 过滤后获取到{len(stocks)}只股票")
            if stocks:
                logger.info(f"样例股票: {stocks[0] if stocks else '无'}")
            return stocks
    except Exception as e:
        logger.error(f"[主接口] akshare失败: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 方案二：东方财富直接接口
    try:
        logger.info("[备用1] 尝试使用东方财富接口")
        codes = fetch_eastmoney(board_code)
        
        if codes:
            logger.info(f"[备用1] 东方财富获取成功: {len(codes)}只股票")
            
            # 获取股票详细信息
            df = ak.stock_zh_a_spot_em()
            df['代码'] = df['代码'].astype(str).str.zfill(6)
            
            stocks = []
            for code in codes:
                try:
                    stock_info = df[df['代码'] == code]
                    if stock_info.empty:
                        continue
                    
                    stock_info = stock_info.iloc[0]
                    
                    # 过滤条件：主板股票，非ST，流通市值15-100亿，股价<=50
                    if (code.startswith(('600', '000', '001')) and 
                        'ST' not in stock_info['名称'] and 
                        15e8 <= float(stock_info['流通市值']) <= 100e8 and 
                        float(stock_info['最新价']) <= 50):
                        
                        stocks.append({
                            'code': code,
                            'name': stock_info['名称'],
                            'current_price': float(stock_info['最新价']),
                            'market_cap': round(float(stock_info['流通市值'])/1e8, 2),
                            'type': 'stock'
                        })
                except Exception as e:
                    logger.error(f"处理股票[{code}]数据失败: {str(e)}")
                    continue
            
            logger.info(f"[备用1] 过滤后获取到{len(stocks)}只股票")
            if stocks:
                logger.info(f"样例股票: {stocks[0] if stocks else '无'}")
            return stocks
    except Exception as e:
        logger.error(f"[备用1] 东方财富失败: {str(e)}")
        logger.error(traceback.format_exc())
    
    # 默认返回空列表
    logger.warning(f"板块[{board_code}]所有获取方式均失败")
    return []

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def fetch_eastmoney(board_code):
    """东方财富直接接口（动态参数）"""
    logger.info(f"尝试从东方财富获取板块[{board_code}]成分股")
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
    
    try:
        response = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get('data', {}).get('diff'):
            codes = [item["f12"] for item in data["data"]["diff"]]
            logger.info(f"东方财富获取成功: {len(codes)}只股票")
            return codes
        else:
            logger.warning("东方财富返回空数据")
            return []
    except Exception as e:
        logger.error(f"东方财富请求失败: {str(e)}")
        raise
    
def get_hist_data(symbol, adjust_type):
    """获取历史数据"""
    logger.info(f"获取股票[{symbol}]的{adjust_type}历史数据")
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            adjust=adjust_type
        )
        if df.empty:
            logger.warning(f"股票[{symbol}]历史数据为空")
            return None
            
        processed_df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }).set_index('date')
        
        logger.info(f"成功获取{len(processed_df)}行历史数据")
        return processed_df
    except Exception as e:
        logger.error(f"历史数据获取失败: {symbol} {str(e)[:100]}")
        logger.error(traceback.format_exc())
        return None

def get_stock_detail(stock_code):
    """获取股票详细信息（包括技术分析）"""
    logger.info(f"=== 获取股票[{stock_code}]详情 ===")
    try:
        # 获取基本信息
        df = ak.stock_zh_a_spot_em()
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        stock_info = df[df['代码'] == stock_code]
        
        if stock_info.empty:
            logger.error(f"股票代码[{stock_code}]不存在")
            return None
            
        stock_info = stock_info.iloc[0]
        
        # 构建基本结果
        result = {
            'code': stock_code,
            'name': stock_info['名称'],
            'current_price': float(stock_info['最新价']),
            'market_cap': round(float(stock_info['流通市值'])/1e8, 2),
            'type': 'stock'
        }
        
        # 获取历史数据
        hist_hfq = get_hist_data(stock_code, "hfq")
        if hist_hfq is None:
            logger.warning(f"股票[{stock_code}]后复权数据获取失败")
            return result
            
        hist_qfq = get_hist_data(stock_code, "qfq")
        if hist_qfq is None:
            logger.warning(f"股票[{stock_code}]前复权数据获取失败")
            return result
        
        # 历史K线数据
        result['kdata'] = []
        for index, row in hist_hfq.iterrows():
            try:
                result['kdata'].append({
                    'date': index.strftime('%Y-%m-%d'),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']) if 'volume' in row else 0
                })
            except:
                continue
        
        # 计算斐波那契回调
        fib_data = calculate_fib_with_dates(hist_hfq)
        
        if all(x is not None for x in fib_data):
            low_date, high_date, hfq_low, hfq_high, hfq_fib = fib_data
            
            # 在前复权数据中查找对应日期的价格
            if low_date in hist_qfq.index and high_date in hist_qfq.index:
                qfq_low = round(hist_qfq.loc[low_date, 'low'], 2)
                qfq_high = round(hist_qfq.loc[high_date, 'high'], 2)
                qfq_fib = round(qfq_low + (qfq_high - qfq_low) * 0.618, 2)
                
                # 计算突破状态
                is_breakthrough = float(stock_info['最新价']) > qfq_fib
                
                # 添加斐波那契分析结果
                result['fibonacci'] = {
                    'hfq': {
                        'low': hfq_low,
                        'high': hfq_high,
                        'fib618': hfq_fib,
                    },
                    'qfq': {
                        'low': qfq_low,
                        'high': qfq_high,
                        'fib618': qfq_fib
                    },
                    'dates': {
                        'low_date': low_date.strftime('%Y-%m-%d'),
                        'high_date': high_date.strftime('%Y-%m-%d')
                    },
                    'breakthrough': '是' if is_breakthrough else '否'
                }
            else:
                logger.warning(f"前复权数据中缺少关键日期: low_date={low_date}, high_date={high_date}")
        
        logger.info(f"股票[{stock_code}]详情获取成功")
        return result
    except Exception as e:
        logger.error(f"获取股票[{stock_code}]详情失败: {str(e)}")
        logger.error(traceback.format_exc())
        return None

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
        logger.error(f"波段计算错误: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None, None, None, None

def test_data_retrieval():
    """测试数据获取是否正常工作"""
    logger.info("=== 开始测试数据获取 ===")
    
    # 测试获取板块列表
    boards = get_all_boards()
    logger.info(f"板块列表: {len(boards)}个")
    
    # 测试全市场模式
    all_stocks = get_all_market_stocks()
    logger.info(f"全市场股票: {len(all_stocks)}只")
    
    # 测试板块模式
    if boards and len(boards) > 1:
        test_board = boards[1]  # 第二个板块(跳过ALL)
        board_stocks = get_board_stocks(test_board['code'])
        logger.info(f"板块[{test_board['name']}]股票: {len(board_stocks)}只")
    
    # 测试股票详情
    if all_stocks:
        test_stock = all_stocks[0]
        stock_detail = get_stock_detail(test_stock['code'])
        logger.info(f"股票[{test_stock['name']}]详情获取{'成功' if stock_detail else '失败'}")
    
    logger.info("=== 数据获取测试完成 ===")
    
    return {
        "boards_count": len(boards),
        "all_stocks_count": len(all_stocks),
        "board_stocks_count": len(board_stocks) if 'board_stocks' in locals() else 0,
        "stock_detail_success": stock_detail is not None if 'stock_detail' in locals() else False
    }

if __name__ == "__main__":
    logger.info("测试数据获取中...")
    test_results = test_data_retrieval()
    logger.info(f"测试结果: {json.dumps(test_results, indent=2)}") 