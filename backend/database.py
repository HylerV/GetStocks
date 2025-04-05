from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# 创建数据库连接
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:initpass@localhost:5432/stock_analysis"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Board(Base):
    __tablename__ = "boards"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stocks = relationship("Stock", back_populates="board")

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    current_price = Column(Float)
    market_cap = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    board_id = Column(Integer, ForeignKey("boards.id"))
    board = relationship("Board", back_populates="stocks")
    fib_analysis = relationship("FibonacciAnalysis", back_populates="stock", uselist=False)
    price_history = relationship("PriceHistory", back_populates="stock")

class FibonacciAnalysis(Base):
    __tablename__ = "fibonacci_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    prev_low_hfq = Column(Float)
    prev_high_hfq = Column(Float)
    fib_hfq = Column(Float)
    prev_low_qfq = Column(Float)
    prev_high_qfq = Column(Float)
    fib_qfq = Column(Float)
    breakthrough_status = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    stock = relationship("Stock", back_populates="fib_analysis")

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime)
    open = Column(Float)
    close = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    stock = relationship("Stock", back_populates="price_history")
    
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uix_stock_date'),
    )

# 创建所有表
Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 更新或创建记录
def update_or_create(db, model, filter_kwargs, update_kwargs):
    instance = db.query(model).filter_by(**filter_kwargs).first()
    if instance:
        for key, value in update_kwargs.items():
            setattr(instance, key, value)
        return instance
    else:
        instance = model(**{**filter_kwargs, **update_kwargs})
        db.add(instance)
        return instance