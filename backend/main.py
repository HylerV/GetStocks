from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json
import asyncio
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import get_db, Board, Stock, FibonacciAnalysis, PriceHistory, update_or_create

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite默认端口
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {str(e)}")

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Stock Analysis API is running"}

@app.get("/api/boards")
@limiter.limit("60/minute")
async def get_boards(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
):
    try:
        query = db.query(Board)
        if search:
            query = query.filter(Board.name.ilike(f"%{search}%"))
        
        total = query.count()
        boards = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": boards,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"获取板块列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取板块列表失败")

@app.get("/api/boards/{board_code}/stocks")
@limiter.limit("60/minute")
async def get_board_stocks(
    request: Request,
    board_code: str,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20
):
    try:
        board = db.query(Board).filter(Board.code == board_code).first()
        if not board:
            raise HTTPException(status_code=404, detail="板块不存在")
        
        query = db.query(Stock).filter(Stock.board_id == board.id)
        total = query.count()
        stocks = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "total": total,
            "items": stocks,
            "page": page,
            "page_size": page_size
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取板块股票失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取板块股票失败")

@app.get("/api/stocks/{stock_code}/analysis")
@limiter.limit("30/minute")
async def get_stock_analysis(
    request: Request,
    stock_code: str,
    db: Session = Depends(get_db)
):
    try:
        stock = db.query(Stock).filter(Stock.code == stock_code).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        analysis = stock.fib_analysis
        if not analysis:
            raise HTTPException(status_code=404, detail="暂无分析数据")
        
        return analysis
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取股票分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取股票分析失败")

@app.get("/api/stocks/{stock_code}/history")
@limiter.limit("30/minute")
async def get_stock_history(
    request: Request,
    stock_code: str,
    db: Session = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    try:
        stock = db.query(Stock).filter(Stock.code == stock_code).first()
        if not stock:
            raise HTTPException(status_code=404, detail="股票不存在")
        
        query = db.query(PriceHistory).filter(PriceHistory.stock_id == stock.id)
        
        if start_date:
            query = query.filter(PriceHistory.date >= datetime.strptime(start_date, "%Y-%m-%d"))
        if end_date:
            query = query.filter(PriceHistory.date <= datetime.strptime(end_date, "%Y-%m-%d"))
        
        history = query.order_by(PriceHistory.date).all()
        return history
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"获取历史数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取历史数据失败")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except Exception as e:
        logger.error(f"WebSocket连接异常: {str(e)}")
    finally:
        manager.disconnect(websocket)

async def update_stock_data():
    """定时更新股票数据"""
    while True:
        try:
            # TODO: 实现数据更新逻辑
            await manager.broadcast(json.dumps({
                "type": "update",
                "message": "数据已更新",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"数据更新失败: {str(e)}")
        await asyncio.sleep(300)  # 5分钟更新一次

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_stock_data())