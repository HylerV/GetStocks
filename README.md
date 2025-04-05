# 股票分析系统

这是一个基于 FastAPI 和 Vue.js 的股票分析系统，提供板块选股和技术分析功能。

## 功能特点

- 板块选股
- 技术分析（斐波那契回调）
- 历史走势图表
- 实时数据更新

## 技术栈

- 后端：FastAPI + akshare
- 前端：Vue 3 + Element Plus + ECharts
- 数据源：akshare

## 安装说明

### 后端设置

1. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行后端服务：
```bash
cd backend
uvicorn main:app --reload
```

### 前端设置

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 运行开发服务器：
```bash
npm run dev
```

## 使用说明

1. 访问 http://localhost:3000 打开前端页面
2. 在左侧选择或搜索板块
3. 查看右侧的股票列表
4. 点击股票查看详细分析

## API 文档

访问 http://localhost:8000/docs 查看完整的 API 文档。

## 注意事项

- 确保已安装 Python 3.8+ 和 Node.js 16+
- 需要稳定的网络连接以获取实时数据
- 建议使用 Chrome 或 Firefox 浏览器


细化一下需求
（1）我需要为股票分析系统设计PostgreSQL数据库，包含以下数据：
- 板块信息（名称/代码）
- 股票基本信息（代码/名称/流通市值等）
- 斐波那契分析结果
- 历史价格数据
要求：
1. 使用stock_analysis数据库
2. 需要包含数据更新时间戳
3. 建立合理的表关系
4. 考虑数据更新时的去重逻辑
（2）基于FastAPI构建RESTful API，需要实现：
1. 板块列表获取接口（对应原get_all_boards）
2. 成分股获取接口（对应原get_board_stocks）
3. 技术分析接口（对应原calculate_fib_with_dates）
4. 分页查询接口（支持前端分布加载）

要求：
- 使用ORM管理数据库
- 添加请求频率限制
- 实现异常处理中间件
- 支持异步数据获取
（3）使用Vue构建前端，需要：
1. 板块选择组件（支持搜索和分页）
2. 股票列表虚拟滚动组件
3. 斐波那契分析结果可视化
4. 实时数据更新指示

要求：
- 使用对应组件库
- 实现请求重试机制
- 支持WebSocket实时更新
- 添加加载状态骨架屏