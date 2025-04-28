from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio
import logging
import pandas as pd
import numpy as np
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import get_db, Board, Stock, FibonacciAnalysis, PriceHistory, update_or_create
from GetStocks import get_all_boards, get_board_stocks, get_stock_detail
import akshare as ak

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Stock Analysis API")

# 创建限速器
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 配置CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3001",
    "http://127.0.0.1:3001"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            'board': [],
            'market': []
        }

    async def connect(self, websocket: WebSocket, mode: str):
        await websocket.accept()
        self.active_connections[mode].append(websocket)
        # 发送初始状态
        await websocket.send_json({
            "type": "init",
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket, mode: str):
        if websocket in self.active_connections[mode]:
            self.active_connections[mode].remove(websocket)

    async def broadcast_to_mode(self, message: Any, mode: str):
        for connection in self.active_connections[mode]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {str(e)}")

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Stock Analysis API is running"}

@app.get("/api/boards")
async def get_boards_api(
    request: Request,
    mode: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None
):
    """获取板块列表"""
    try:
        boards = get_all_boards()
        if not boards:
            raise HTTPException(status_code=404, detail="未找到板块数据")
            
        # 根据模式过滤
        if mode == "board":
            boards = [b for b in boards if b.get('type') == 'board']
        elif mode == "market":
            boards = [b for b in boards if b.get('type') == 'market']
        
        # 搜索过滤
        if search:
            boards = [b for b in boards if search.lower() in b.get('name', '').lower()]
            
        # 计算总数
        total = len(boards)
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        boards_page = boards[start:end]
            
        return {
            "items": boards_page,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"获取板块列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_code}/stocks")
async def get_board_stocks_api(
    request: Request,
    board_code: str
):
    """获取指定板块的股票列表"""
    try:
        stocks = get_board_stocks(board_code)
        if not stocks:
            raise HTTPException(status_code=404, detail=f"未找到板块[{board_code}]的股票数据")
            
        return {
            "items": stocks,
            "total": len(stocks)
        }
    except Exception as e:
        logger.error(f"获取板块[{board_code}]股票列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{board_code}")
async def get_stocks_api(
    request: Request,
    board_code: str
):
    """获取股票列表（兼容旧API）"""
    try:
        stocks = get_board_stocks(board_code)
        if not stocks:
            raise HTTPException(status_code=404, detail="未找到股票数据")
            
        return {
            "success": True,
            "data": stocks
        }
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{stock_code}/detail")
async def get_stock_detail_api(
    request: Request,
    stock_code: str
):
    """获取股票详情（兼容旧API）"""
    try:
        stock = get_stock_detail(stock_code)
        if not stock:
            raise HTTPException(status_code=404, detail="未找到股票详情")
            
        return {
            "success": True,
            "data": stock
        }
    except Exception as e:
        logger.error(f"获取股票详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks/{stock_code}")
async def get_stock_api(
    request: Request,
    stock_code: str
):
    """获取股票详情"""
    try:
        stock = get_stock_detail(stock_code)
        if not stock:
            raise HTTPException(status_code=404, detail=f"未找到股票[{stock_code}]详情")
            
        return stock
    except Exception as e:
        logger.error(f"获取股票[{stock_code}]详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接处理"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            
            # 根据消息类型处理
            if data.get("type") == "subscribe":
                code = data.get("code")
                if code:
                    # 获取最新数据
                    if code.startswith("BK"):
                        result = get_board_stocks(code)
                    else:
                        result = get_stock_detail(code)
                        
                    # 发送更新
                    await websocket.send_json({
                        "type": "update",
                        "code": code,
                        "data": result
                    })
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
    finally:
        await websocket.close()

async def update_data(mode: str):
    """定时更新数据"""
    update_interval = 5 if mode == 'board' else 1  # 板块5秒，个股1秒
    while True:
        try:
            await manager.broadcast_to_mode({
                "type": f"{mode}_update",
                "message": f"{mode}数据已更新",
                "timestamp": datetime.now().isoformat()
            }, mode)
        except Exception as e:
            logger.error(f"数据更新失败: {str(e)}")
        await asyncio.sleep(update_interval)

@app.on_event("startup")
async def startup_event():
    # 启动两个更新任务
    asyncio.create_task(update_data('board'))
    asyncio.create_task(update_data('market'))