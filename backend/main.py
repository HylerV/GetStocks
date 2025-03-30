from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import akshare as ak
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="股票分析系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StockAnalysis(BaseModel):
    code: str
    name: str
    current_price: float
    market_cap: float
    prev_low_hfq: Optional[float]
    prev_high_hfq: Optional[float]
    fib_hfq: Optional[float]
    prev_low_qfq: Optional[float]
    prev_high_qfq: Optional[float]
    fib_qfq: Optional[float]
    breakthrough_status: str

@app.get("/api/boards")
async def get_boards():
    """获取所有板块列表"""
    try:
        logger.info("开始获取板块列表")
        boards = ak.stock_board_concept_name_em()
        result = boards[['板块名称', '板块代码']].to_dict('records')
        logger.info(f"成功获取板块列表，共 {len(result)} 个板块")
        return result
    except Exception as e:
        logger.error(f"获取板块列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取板块列表失败: {str(e)}")

@app.get("/api/board/{board_code}/stocks")
async def get_board_stocks(board_code: str):
    """获取指定板块的股票列表并进行技术分析"""
    try:
        logger.info(f"开始获取板块 {board_code} 的成分股")
        
        # 获取成分股
        try:
            board_stocks = ak.stock_board_concept_cons_em(symbol=board_code)
            logger.info(f"原始成分股数量：{len(board_stocks) if board_stocks is not None else 0}")
        except Exception as e:
            logger.error(f"获取板块成分股数据时出错: {str(e)}")
            return {"stocks": [], "analysis_results": []}

        if board_stocks is None or board_stocks.empty:
            logger.warning(f"板块 {board_code} 没有成分股数据")
            return {"stocks": [], "analysis_results": []}
            
        # 获取代码列
        if '代码' in board_stocks.columns:
            code_column = '代码'
        elif '股票代码' in board_stocks.columns:
            code_column = '股票代码'
        else:
            logger.error(f"找不到代码列，可用的列: {board_stocks.columns.tolist()}")
            return {"stocks": [], "analysis_results": []}
            
        board_codes = board_stocks[code_column].astype(str).str.zfill(6).tolist()
        
        # 获取全市场数据
        all_stocks = ak.stock_zh_a_spot_em()
        if all_stocks is None or all_stocks.empty:
            return {"stocks": [], "analysis_results": []}
            
        # 统一代码格式
        all_stocks['代码'] = all_stocks['代码'].astype(str).str.zfill(6)
            
        # 筛选条件
        filtered = all_stocks[
            (all_stocks['代码'].isin(board_codes)) &
            (all_stocks['流通市值'] / 1e8 >= 15) &
            (all_stocks['流通市值'] / 1e8 <= 100) &
            (all_stocks['最新价'] <= 50) &
            (~all_stocks['名称'].str.contains('ST')) &
            (all_stocks['代码'].str.startswith(('600', '601', '603', '605', '000', '001', '002'))) &
            (all_stocks['名称'].str.contains('智能|AI|机器视觉|人工智能|自然语言处理|机器人|工业4.0|物联网|大数据|云计算|区块链|数字经济|元宇宙'))
        ]
        
        logger.info(f"初步筛选数量: {len(filtered)}")
        
        if filtered.empty:
            return {"stocks": [], "analysis_results": []}
            
        # 分析结果
        analysis_results = []
        for _, stock in filtered.iterrows():
            code = stock['代码']
            try:
                # 获取后复权数据
                hist_hfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").set_index('日期')
                low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq = calculate_fib_with_dates(hist_hfq)
                
                if not low_date:
                    continue
                    
                # 获取前复权数据
                hist_qfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").set_index('日期')
                prev_low_qfq = round(hist_qfq.loc[low_date, '最低'], 2) if low_date in hist_qfq.index else None
                prev_high_qfq = round(hist_qfq.loc[high_date, '最高'], 2) if high_date in hist_qfq.index else None
                
                if prev_low_qfq and prev_high_qfq:
                    fib_qfq = round(prev_low_qfq + (prev_high_qfq - prev_low_qfq) * 0.618, 2)
                else:
                    fib_qfq = None
                
                analysis_results.append({
                    '代码': code,
                    '名称': stock['名称'],
                    '最新价（除权）': stock['最新价'],
                    '后复权前低价': prev_low_hfq,
                    '后复权前高价': prev_high_hfq,
                    '后复权0.618位': fib_hfq,
                    '除权前低价': prev_low_qfq,
                    '除权前高价': prev_high_qfq,
                    '除权0.618位': fib_qfq
                })
                
                logger.info(f"处理中：{code} {stock['名称']}...")
                
            except Exception as e:
                logger.error(f"处理股票 {code} 时出错: {str(e)}")
                continue
        
        if analysis_results:
            logger.info("\n最终分析结果:")
            for result in analysis_results:
                logger.info(f"{result}")
        
        return {
            "stocks": filtered[['代码', '名称', '最新价', '流通市值']].to_dict('records'),
            "analysis_results": analysis_results
        }
        
    except Exception as e:
        logger.error(f"获取板块成分股失败: {str(e)}")
        return {"stocks": [], "analysis_results": []}

@app.get("/api/stock/{code}/analysis")
async def get_stock_analysis(code: str):
    """获取单个股票的技术分析数据"""
    try:
        logger.info(f"开始获取股票 {code} 的技术分析数据")
        
        # 获取后复权数据
        hist_hfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="hfq").set_index('日期')
        low_date, high_date, prev_low_hfq, prev_high_hfq, fib_hfq = calculate_fib_with_dates(hist_hfq)
        
        if not low_date:
            logger.warning(f"股票 {code} 未找到有效波段")
            raise HTTPException(status_code=404, detail="未找到有效波段")
        
        # 获取前复权数据
        hist_qfq = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").set_index('日期')
        prev_low_qfq = hist_qfq.loc[low_date, '最低'] if low_date in hist_qfq.index else None
        prev_high_qfq = hist_qfq.loc[high_date, '最高'] if high_date in hist_qfq.index else None
        fib_qfq = round(prev_low_qfq + (prev_high_qfq - prev_low_qfq)*0.618, 2) if all([prev_low_qfq, prev_high_qfq]) else None
        
        # 获取当前价格
        current_data = ak.stock_zh_a_spot_em()
        stock_info = current_data[current_data['代码'] == code].iloc[0]
        
        result = {
            'code': code,
            'name': stock_info['名称'],
            'current_price': stock_info['最新价'],
            'market_cap': round(stock_info['流通市值']/1e8, 2),
            'prev_low_hfq': prev_low_hfq,
            'prev_high_hfq': prev_high_hfq,
            'fib_hfq': fib_hfq,
            'prev_low_qfq': prev_low_qfq,
            'prev_high_qfq': prev_high_qfq,
            'fib_qfq': fib_qfq,
            'breakthrough_status': '是' if (fib_qfq and stock_info['最新价'] > fib_qfq) else '否'
        }
        
        logger.info(f"成功获取股票 {code} 的技术分析数据")
        return result
        
    except Exception as e:
        logger.error(f"获取股票技术分析数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取股票技术分析数据失败: {str(e)}")

@app.get("/api/stock/{code}/history")
def get_stock_history(code: str):
    try:
        # 获取最近60天的K线数据
        hist_data = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(60)
        
        # 转换数据格式为前端需要的格式
        history = []
        for _, row in hist_data.iterrows():
            history.append({
                'date': row['日期'],
                'open': float(row['开盘']),
                'close': float(row['收盘']),
                'low': float(row['最低']),
                'high': float(row['最高']),
                'volume': float(row['成交量'])
            })
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/available")
async def get_available_boards():
    """获取包含符合条件股票的板块列表"""
    try:
        logger.info("开始获取有效板块列表")
        logger.info("正在获取全市场数据...")
        
        # 获取全市场数据
        all_stocks = ak.stock_zh_a_spot_em()
        if all_stocks is None or all_stocks.empty:
            logger.error("获取全市场数据失败")
            return {"boards": []}
            
        logger.info(f"获取全市场数据成功，共 {len(all_stocks)} 只股票")
        logger.info(f"数据列名: {all_stocks.columns.tolist()}")
        
        # 初步筛选
        filtered = all_stocks[
            (all_stocks['流通市值'] / 1e8 >= 15) &  # 流通市值15-100亿
            (all_stocks['流通市值'] / 1e8 <= 100) &
            (all_stocks['最新价'] <= 50) &
            (~all_stocks['名称'].str.contains('ST')) &
            (all_stocks['代码'].astype(str).str.startswith(('600', '601', '603', '605', '000', '001', '002'))) &
            (all_stocks['名称'].str.contains('智能|AI|机器视觉|人工智能|自然语言处理'))
        ]
        
        logger.info(f"初步筛选后剩余: {len(filtered)} 只股票")
        
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
                    continue
                
                results.append({
                    'code': code,
                    'name': row['名称'],
                    'current_price': row['最新价'],
                    'prev_low_hfq': prev_low_hfq,
                    'prev_high_hfq': prev_high_hfq,
                    'fib_hfq': fib_hfq,
                    'prev_low_qfq': prev_low_qfq,
                    'prev_high_qfq': prev_high_qfq,
                    'fib_qfq': fib_qfq
                })
                
                logger.info(f"成功处理股票: {code} {row['名称']}")
                
            except Exception as e:
                logger.warning(f"处理股票 {code} 时出错: {str(e)}")
                continue
        
        logger.info(f"找到 {len(results)} 只符合条件的股票")
        
        # 获取这些股票所属的板块
        try:
            boards = ak.stock_board_concept_name_em()
            valid_boards = []
            classified_stocks = set()  # 记录已分类的股票
            
            for _, board_row in boards.iterrows():
                board_code = board_row['板块代码']
                board_name = board_row['板块名称']
                
                try:
                    # 获取板块成分股
                    board_stocks = ak.stock_board_concept_cons_em(symbol=board_code)
                    if board_stocks is None or board_stocks.empty:
                        continue
                    
                    # 检查数据格式
                    if isinstance(board_stocks, pd.DataFrame):
                        # 确保代码列存在
                        code_column = None
                        for col in ['代码', '股票代码', 'code']:
                            if col in board_stocks.columns:
                                code_column = col
                                break
                        
                        if code_column is None:
                            logger.warning(f"板块 {board_name} 找不到代码列，可用的列: {board_stocks.columns.tolist()}")
                            continue
                        
                        # 统一代码格式
                        board_stocks[code_column] = board_stocks[code_column].astype(str).str.zfill(6)
                        
                        # 检查板块中是否包含我们筛选出的股票
                        matching_stocks = []
                        for result in results:
                            if result['code'] in board_stocks[code_column].values:
                                matching_stocks.append(result)
                                classified_stocks.add(result['code'])
                        
                        if matching_stocks:
                            valid_boards.append({
                                'code': board_code,
                                'name': board_name,
                                'matching_stocks': matching_stocks
                            })
                            logger.info(f"板块 {board_name} 包含 {len(matching_stocks)} 只符合条件的股票")
                        
                except Exception as e:
                    logger.warning(f"获取板块 {board_name} 成分股时出错: {str(e)}")
                    continue
            
            # 处理未分类的股票
            unclassified_stocks = [stock for stock in results if stock['code'] not in classified_stocks]
            if unclassified_stocks:
                valid_boards.append({
                    'code': 'OTHER',
                    'name': '未分类股票',
                    'matching_stocks': unclassified_stocks
                })
                logger.info(f"未分类股票数量: {len(unclassified_stocks)}")
            
            logger.info(f"找到 {len(valid_boards)} 个板块（包括未分类股票）")
            return {"boards": valid_boards}
            
        except Exception as e:
            logger.error(f"获取板块列表时出错: {str(e)}")
            return {"boards": []}
            
    except Exception as e:
        logger.error(f"获取有效板块时出错: {str(e)}")
        return {"boards": []}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 