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
