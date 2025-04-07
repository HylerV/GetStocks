<template>
  <div class="container">
    <!-- 顶部区域：搜索和模式选择 -->
    <div class="top-bar">
      <div class="left-section">
        <h1 class="app-title">股票分析系统</h1>
      </div>
      <div class="search-section">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索板块或股票"
          clearable
          prefix-icon="el-icon-search"
          @input="handleSearch"
          class="search-input"
        />
        <el-radio-group v-model="mode" @change="handleModeChange" class="mode-toggle">
          <el-radio-button :value="'board'">板块模式</el-radio-button>
          <el-radio-button :value="'all'">全市场模式</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="refreshData" class="refresh-button">
          <i class="el-icon-refresh"></i> 刷新数据
        </el-button>
      </div>
    </div>

    <!-- 中间区域：板块/股票列表 -->
    <div class="main-content">
      <div class="content-header">
        <h2 class="section-title">
          {{ mode === 'board' ? '板块列表' : '全市场股票' }}
          <span v-if="selectedBoard" class="selected-board">- {{ selectedBoard.name }}</span>
        </h2>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalBoards"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
          class="pagination"
        />
      </div>
      
      <!-- 板块列表 -->
      <div v-if="mode === 'board' && !selectedBoard" class="table-container">
        <el-table
          v-loading="loading"
          :data="filteredBoards"
          style="width: 100%"
          highlight-current-row
          stripe
          @row-click="handleBoardClick"
          class="data-table"
        >
          <el-table-column prop="name" label="板块名称" />
          <el-table-column prop="code" label="板块代码" width="110" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" text @click.stop="handleBoardClick(row)">
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 股票列表 -->
      <div v-else class="table-container">
        <el-table
          v-loading="stocksLoading"
          :data="currentStocks"
          style="width: 100%"
          highlight-current-row
          stripe
          @row-click="handleStockClick"
          class="data-table"
        >
          <el-table-column prop="code" label="代码" width="100" fixed="left" />
          <el-table-column prop="name" label="名称" min-width="120" fixed="left" />
          <el-table-column prop="current_price" label="当前价" width="100" sortable />
          <el-table-column prop="market_cap" label="市值(亿)" width="100" sortable />
          <el-table-column prop="hfq_low" label="后复权低位" width="100" sortable />
          <el-table-column prop="hfq_high" label="后复权高位" width="100" sortable />
          <el-table-column prop="hfq_fib" label="后复权0.618" width="120" sortable />
          <el-table-column prop="qfq_low" label="前复权低位" width="100" sortable />
          <el-table-column prop="qfq_high" label="前复权高位" width="100" sortable />
          <el-table-column prop="qfq_fib" label="前复权0.618" width="120" sortable />
          <el-table-column label="突破状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.breakthrough === '是' ? 'success' : 'info'">
                {{ row.breakthrough || '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" text @click.stop="handleStockClick(row)">
                分析
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div v-if="mode === 'board'" class="back-link">
          <el-button text @click="selectedBoard = null" class="back-button">
            <i class="el-icon-back"></i> 返回板块列表
          </el-button>
        </div>
      </div>
    </div>

    <!-- 底部区域：股票详情 -->
    <div v-if="selectedStock" class="stock-detail">
      <div class="detail-header">
        <h2 class="stock-title">
          {{ selectedStock.name }} ({{ selectedStock.code }})
          <span class="stock-price">¥{{ selectedStock.current_price }}</span>
        </h2>
        <el-button type="primary" size="small" @click="selectedStock = null">关闭</el-button>
      </div>
      
      <div class="detail-content">
        <!-- 基本信息卡片 -->
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <h3>基本信息</h3>
            </div>
          </template>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">市值：</span>
              <span class="value">{{ selectedStock.market_cap }} 亿</span>
            </div>
            <div class="info-item">
              <span class="label">突破状态：</span>
              <span class="value">
                <el-tag :type="selectedStock.breakthrough === '是' ? 'success' : 'info'">
                  {{ selectedStock.breakthrough || '否' }}
                </el-tag>
              </span>
            </div>
          </div>
        </el-card>
        
        <!-- 图表卡片 -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <h3>K线图</h3>
              <div class="chart-controls">
                <el-checkbox-group v-model="chartIndicators">
                  <el-checkbox value="MACD">MACD</el-checkbox>
                  <el-checkbox value="BOLL">布林带</el-checkbox>
                  <el-checkbox value="VOL">成交量</el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </template>
          <div ref="chartContainer" class="chart-container"></div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

// 状态变量
const searchKeyword = ref('')
const mode = ref('board')
const loading = ref(false)
const stocksLoading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalBoards = ref(0)
const boards = ref([])
const selectedBoard = ref(null)
const currentStocks = ref([])
const selectedStock = ref(null)
const chartContainer = ref(null)
const chart = ref(null)
const chartIndicators = ref(['MACD', 'BOLL', 'VOL']) // 需要在el-checkbox中使用value属性替代label

// 计算属性
const filteredBoards = computed(() => {
  if (!searchKeyword.value) return boards.value
  return boards.value.filter(board => 
    board.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

// 方法
const fetchBoards = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/boards', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        search: searchKeyword.value
      }
    })
    // 确保response.data.items是一个数组
    boards.value = response.data.items || []
    totalBoards.value = response.data.total || 0
  } catch (error) {
    ElMessage.error('获取板块列表失败')
    console.error('获取板块列表失败:', error)
    boards.value = []
    totalBoards.value = 0
  } finally {
    loading.value = false
  }
}

const fetchStocks = async (boardCode) => {
  try {
    stocksLoading.value = true
    // 使用明确的板块股票API路径避免冲突
    const response = await axios.get(`/api/boards/${boardCode}/stocks`)
    
    // 打印原始数据，查看结构
    console.log('API返回的原始数据:', response.data)
    
    // 确保获取到数据
    const stocksData = response.data.items || response.data.data || []
    
    if (stocksData.length === 0) {
      console.warn('未获取到股票数据')
      // 使用模拟数据测试
      stocksData.push({
        code: '000001',
        name: '平安银行',
        current_price: 10.25,
        market_cap: 35.8,
        fibonacci: {
          hfq: { low: 8.5, high: 12.3, fib618: 9.95 },
          qfq: { low: 8.5, high: 12.3, fib618: 9.95 },
          breakthrough: '是'
        }
      })
    }
    
    // 处理数据，添加斐波那契相关字段
    currentStocks.value = stocksData.map(stock => {
      console.log('处理股票数据:', stock.code, stock.name, stock.fibonacci)
      
      // 尝试各种可能的数据结构解析
      const fibonacci = stock.fibonacci || {}
      const hfq = fibonacci.hfq || {}
      const qfq = fibonacci.qfq || {}
      
      // 提取前后复权数据，优先使用fibonacci结构，其次尝试直接从stock提取
      return {
        ...stock,
        hfq_low: hfq.low || stock.hfq_low || '-',
        hfq_high: hfq.high || stock.hfq_high || '-',
        hfq_fib: hfq.fib618 || stock.hfq_fib || '-',
        qfq_low: qfq.low || stock.qfq_low || '-',
        qfq_high: qfq.high || stock.qfq_high || '-',
        qfq_fib: qfq.fib618 || stock.qfq_fib || '-',
        breakthrough: fibonacci.breakthrough || stock.breakthrough || '否'
      }
    })
    
    console.log('处理后的股票数据:', currentStocks.value)
  } catch (error) {
    ElMessage.error('获取股票列表失败')
    console.error('获取股票列表失败:', error)
    currentStocks.value = []
  } finally {
    stocksLoading.value = false
  }
}

const fetchStockDetail = async (stockCode) => {
  let retries = 0;
  const maxRetries = 3;
  
  while (retries < maxRetries) {
    try {
      stocksLoading.value = true;
      
      // 尝试使用明确的股票详情API
      console.log(`尝试获取股票[${stockCode}]详情...`);
      const detailResponse = await axios.get(`/api/stocks/${stockCode}/detail`, {
        timeout: 30000  // 增加超时时间到30秒
      });
      console.log(`获取到股票[${stockCode}]详情:`, detailResponse.data);
      
      if (detailResponse.data && detailResponse.data.success) {
        const stockDetail = detailResponse.data.data || {};
        
        // 检查返回数据是否有效
        if (!stockDetail.kdata || stockDetail.kdata.length === 0) {
          console.warn(`股票[${stockCode}]的K线数据为空`);
        }
        
        // 提取fibonacci数据，可能在不同的数据结构中
        const fibonacci = stockDetail.fibonacci || {};
        const hfq = fibonacci.hfq || {};
        const qfq = fibonacci.qfq || {};
        
        // 转换并返回数据
        return {
          ...stockDetail,
          code: stockCode,  // 确保保留原始代码
          kdata: stockDetail.kdata || [],
          fibonacci: fibonacci,
          hfq_low: hfq.low || stockDetail.hfq_low || '-',
          hfq_high: hfq.high || stockDetail.hfq_high || '-',
          hfq_fib: hfq.fib618 || stockDetail.hfq_fib || '-',
          qfq_low: qfq.low || stockDetail.qfq_low || '-',
          qfq_high: qfq.high || stockDetail.qfq_high || '-',
          qfq_fib: qfq.fib618 || stockDetail.qfq_fib || '-',
          breakthrough: fibonacci.breakthrough || stockDetail.breakthrough || '否'
        };
      } else {
        console.warn(`股票[${stockCode}]详情响应无效或格式不正确`);
        throw new Error('无效的API响应格式');
      }
    } catch (error) {
      retries++;
      console.error(`获取股票详情失败 (${retries}/${maxRetries}):`, error);
      
      // 特殊处理超时错误
      if (error.code === 'ECONNABORTED') {
        console.warn('API请求超时，可能是数据量太大');
        ElMessage.warning(`数据请求超时，正在重试 (${retries}/${maxRetries})...`);
      }
      
      if (retries >= maxRetries) {
        ElMessage.error(`获取股票详情失败，已重试 ${retries} 次`);
        ElMessage.info(`正在使用模拟数据显示...`);
        return generateMockStockData(stockCode);
      }
      
      // 等待一段时间后重试
      await new Promise(resolve => setTimeout(resolve, 1000));
      ElMessage.warning(`正在重试获取股票详情 (${retries}/${maxRetries})...`);
    } finally {
      stocksLoading.value = false;
    }
  }
}

// 生成模拟股票数据以便于前端测试
const generateMockStockData = (stockCode) => {
  console.log(`为股票[${stockCode}]生成模拟数据`);
  
  // 获取今天日期作为基准
  const today = new Date();
  const kdata = [];
  
  // 生成近90天的模拟K线数据
  for (let i = 90; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    
    // 生成一些随机价格数据，但保持合理的关系
    const basePrice = 10 + Math.random() * 5; // 基准价在10-15之间
    const open = basePrice + (Math.random() - 0.5) * 2;
    const close = basePrice + (Math.random() - 0.5) * 2;
    const high = Math.max(open, close) + Math.random() * 0.5;
    const low = Math.min(open, close) - Math.random() * 0.5;
    const volume = Math.floor(Math.random() * 10000000) + 1000000;
    
    kdata.push({
      date: dateStr,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume: volume
    });
  }
  
  // 生成模拟斐波那契数据
  const currentPrice = parseFloat(kdata[kdata.length - 1].close.toFixed(2));
  const lowPrice = parseFloat((Math.min(...kdata.map(k => k.low)) * 0.95).toFixed(2));
  const highPrice = parseFloat((Math.max(...kdata.map(k => k.high)) * 1.05).toFixed(2));
  const fibPrice = parseFloat((lowPrice + (highPrice - lowPrice) * 0.618).toFixed(2));
  const breakthrough = currentPrice > fibPrice ? '是' : '否';
  
  return {
    code: stockCode,
    name: `${row?.name || '模拟股票'}-${stockCode}`,
    current_price: currentPrice,
    market_cap: parseFloat((currentPrice * 3 * 100000000 / 100000000).toFixed(2)), // 假设3亿流通股
    type: 'stock',
    kdata: kdata,
    fibonacci: {
      hfq: {
        low: lowPrice,
        high: highPrice,
        fib618: fibPrice
      },
      qfq: {
        low: lowPrice,
        high: highPrice,
        fib618: fibPrice
      },
      dates: {
        low_date: kdata[15].date, // 随机日期
        high_date: kdata[60].date  // 随机日期
      },
      breakthrough: breakthrough
    },
    hfq_low: lowPrice,
    hfq_high: highPrice,
    hfq_fib: fibPrice,
    qfq_low: lowPrice,
    qfq_high: highPrice,
    qfq_fib: fibPrice,
    breakthrough: breakthrough,
    is_mock: true // 标记为模拟数据
  };
}

const initChart = () => {
  if (chartContainer.value && !chart.value) {
    // 先清除可能存在的旧图表实例
    if (chart.value) {
      chart.value.dispose();
    }
    // 创建新的图表实例
    try {
      chart.value = echarts.init(chartContainer.value);
      // 添加窗口大小变化的监听器
      window.removeEventListener('resize', handleResize);
      window.addEventListener('resize', handleResize);
    } catch (error) {
      console.error('图表初始化失败:', error);
    }
  }
}

// 窗口大小变化处理
const handleResize = () => {
  if (chart.value) {
    chart.value.resize();
  }
}

const updateChart = (stockData) => {
  if (!chart.value) {
    console.warn('图表实例不存在，无法更新图表');
    return;
  }
  
  if (!stockData || !stockData.kdata || stockData.kdata.length === 0) {
    console.warn('股票数据或K线数据不存在，无法更新图表');
    if (chart.value) {
      // 显示一个空图表
      chart.value.setOption({
        title: {
          text: '暂无K线数据',
          left: 'center',
          top: 'center'
        }
      });
    }
    return;
  }
  
  try {
    // 清空旧图表
    chart.value.clear();
    
    const kdata = stockData.kdata;
    
    // 确保所有数据项都有完整的OHLC属性
    const validKdata = kdata.filter(item => {
      return item && 
             typeof item.date === 'string' &&
             item.open !== undefined && item.open !== null &&
             item.high !== undefined && item.high !== null &&
             item.low !== undefined && item.low !== null &&
             item.close !== undefined && item.close !== null;
    });
    
    if (validKdata.length === 0) {
      console.warn('没有有效的K线数据点');
      chart.value.setOption({
        title: {
          text: '数据格式有误，无法显示图表',
          left: 'center',
          top: 'center'
        }
      });
      return;
    }
    
    // 准备数据
    const dates = validKdata.map(item => item.date);
    const data = validKdata.map(item => [
      parseFloat(item.open) || 0, 
      parseFloat(item.close) || 0, 
      parseFloat(item.low) || 0, 
      parseFloat(item.high) || 0
    ]);
    
    // 准备成交量数据
    const volumes = validKdata.map(item => parseFloat(item.volume || 0));
    
    // 计算MACD指标
    const calcMACD = (closeData, shortPeriod = 12, longPeriod = 26, signalPeriod = 9) => {
      const ema = (data, period) => {
        const k = 2 / (period + 1);
        const result = [];
        for (let i = 0; i < data.length; i++) {
          if (i === 0) {
            result.push(data[i]);
          } else {
            result.push(data[i] * k + result[i - 1] * (1 - k));
          }
        }
        return result;
      };
      
      const closes = closeData.map(item => parseFloat(item[1]));
      const emaShort = ema(closes, shortPeriod);
      const emaLong = ema(closes, longPeriod);
      
      const dif = emaShort.map((short, i) => short - emaLong[i]);
      const emaSignal = ema(dif, signalPeriod);
      
      const macd = dif.map((d, i) => (d - emaSignal[i]) * 2);
      
      return {
        dif,
        dea: emaSignal,
        macd
      };
    };
    
    // 计算布林带
    const calcBOLL = (data, period = 20, multiplier = 2) => {
      const closes = data.map(item => parseFloat(item[1]));
      const result = { upper: [], middle: [], lower: [] };
      
      for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
          result.upper.push('-');
          result.middle.push('-');
          result.lower.push('-');
        } else {
          let sum = 0;
          for (let j = i - period + 1; j <= i; j++) {
            sum += closes[j];
          }
          const ma = sum / period;
          
          let squareSum = 0;
          for (let j = i - period + 1; j <= i; j++) {
            squareSum += Math.pow(closes[j] - ma, 2);
          }
          const std = Math.sqrt(squareSum / period);
          
          result.middle.push(ma);
          result.upper.push(ma + multiplier * std);
          result.lower.push(ma - multiplier * std);
        }
      }
      
      return result;
    };
    
    // 计算MA
    const calcMA = (data, period) => {
      const result = [];
      for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
          result.push('-');
          continue;
        }
        let sum = 0;
        for (let j = i - period + 1; j <= i; j++) {
          sum += parseFloat(data[j][1]); // close价格
        }
        result.push((sum / period).toFixed(2));
      }
      return result;
    };
    
    // 获取指标数据
    const macdData = calcMACD(data);
    const bollData = calcBOLL(data);
    const ma5 = calcMA(data, 5);
    const ma10 = calcMA(data, 10);
    const ma20 = calcMA(data, 20);
    const ma30 = calcMA(data, 30);
    
    // 斐波那契数据
    const fibonacci = stockData.fibonacci || {};
    const fibLevel = parseFloat(fibonacci.qfq?.fib618) || null;
    
    // 确定需要显示的指标
    const showMACD = chartIndicators.value.includes('MACD');
    const showBOLL = chartIndicators.value.includes('BOLL');
    const showVOL = chartIndicators.value.includes('VOL');
    
    // 根据显示的指标数量确定网格布局
    const gridCount = 1 + (showMACD ? 1 : 0) + (showVOL ? 1 : 0);
    const grids = [];
    const xAxes = [];
    const yAxes = [];
    
    // 创建主图网格
    grids.push({
      left: '10%',
      right: '8%',
      top: stockData.is_mock ? '15%' : '10%',
      height: gridCount > 1 ? '50%' : '75%'
    });
    
    // 主图X轴
    xAxes.push({
      type: 'category',
      data: dates,
      gridIndex: 0,
      axisLine: { onZero: false },
      splitLine: { show: false }
    });
    
    // 主图Y轴
    yAxes.push({
      scale: true,
      gridIndex: 0,
      splitArea: { show: true }
    });
    
    // 创建系列数组
    const series = [];
    
    // 添加K线图
    series.push({
      name: 'K线',
      type: 'candlestick',
      data: data,
      itemStyle: {
        color: '#06b06d',
        color0: '#e64b65',
        borderColor: '#06b06d',
        borderColor0: '#e64b65'
      },
      markLine: fibLevel ? {
        symbol: 'none',
        data: [
          {
            name: '斐波那契0.618',
            yAxis: fibLevel,
            lineStyle: {
              color: '#f39c12',
              type: 'dashed',
              width: 2
            }
          }
        ]
      } : undefined
    });
    
    // 添加移动平均线
    series.push({
      name: 'MA5',
      type: 'line',
      data: ma5,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1 }
    });
    
    series.push({
      name: 'MA10',
      type: 'line',
      data: ma10,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1 }
    });
    
    series.push({
      name: 'MA20',
      type: 'line',
      data: ma20,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1 }
    });
    
    series.push({
      name: 'MA30',
      type: 'line',
      data: ma30,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 1 }
    });
    
    // 图例数据
    const legendData = ['K线', 'MA5', 'MA10', 'MA20', 'MA30'];
    
    // 添加布林带
    if (showBOLL) {
      legendData.push('BOLL', 'UB', 'LB');
      
      series.push({
        name: 'BOLL',
        type: 'line',
        data: bollData.middle,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#9b59b6'
        },
        symbol: 'none'
      });
      
      series.push({
        name: 'UB',
        type: 'line',
        data: bollData.upper,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#9b59b6'
        },
        symbol: 'none'
      });
      
      series.push({
        name: 'LB',
        type: 'line',
        data: bollData.lower,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#9b59b6'
        },
        symbol: 'none'
      });
    }
    
    // 添加MACD和成交量指标
    let macdIndex = -1;
    let volIndex = -1;
    
    if (showMACD) {
      macdIndex = 1;
      legendData.push('DIF', 'DEA', 'MACD');
      
      // MACD网格
      grids.push({
        left: '10%',
        right: '8%',
        top: '65%',
        height: '15%'
      });
      
      // MACD X轴
      xAxes.push({
        type: 'category',
        gridIndex: macdIndex,
        data: dates,
        axisLabel: { show: false }
      });
      
      // MACD Y轴
      yAxes.push({
        gridIndex: macdIndex,
        scale: true,
        splitNumber: 2
      });
      
      // MACD指标线
      series.push({
        name: 'DIF',
        type: 'line',
        xAxisIndex: macdIndex,
        yAxisIndex: macdIndex,
        data: macdData.dif,
        lineStyle: { width: 1, color: '#da6ee8' },
        symbol: 'none'
      });
      
      series.push({
        name: 'DEA',
        type: 'line',
        xAxisIndex: macdIndex,
        yAxisIndex: macdIndex,
        data: macdData.dea,
        lineStyle: { width: 1, color: '#ffab65' },
        symbol: 'none'
      });
      
      series.push({
        name: 'MACD',
        type: 'bar',
        xAxisIndex: macdIndex,
        yAxisIndex: macdIndex,
        data: macdData.macd,
        itemStyle: {
          color: function(params) {
            return params.data >= 0 ? '#e64b65' : '#06b06d';
          }
        }
      });
    }
    
    if (showVOL) {
      volIndex = showMACD ? 2 : 1;
      legendData.push('成交量');
      
      // 成交量网格
      grids.push({
        left: '10%',
        right: '8%',
        top: showMACD ? '83%' : '65%',
        height: '12%'
      });
      
      // 成交量X轴
      xAxes.push({
        type: 'category',
        gridIndex: volIndex,
        data: dates
      });
      
      // 成交量Y轴
      yAxes.push({
        scale: true,
        gridIndex: volIndex
      });
      
      // 成交量柱状图
      series.push({
        name: '成交量',
        type: 'bar',
        xAxisIndex: volIndex,
        yAxisIndex: volIndex,
        data: volumes,
        itemStyle: {
          color: function(params, index) {
            return index < validKdata.length && 
                   parseFloat(validKdata[index].close) >= parseFloat(validKdata[index].open) 
                   ? '#e64b65' : '#06b06d';
          }
        }
      });
    }
    
    // 构建最终的图表配置
    const option = {
      animation: false,
      title: stockData.is_mock ? {
        text: '【模拟数据】仅供界面测试',
        subtext: '实际数据可能有差异',
        left: 'center',
        top: 0,
        textStyle: {
          color: '#E74C3C',
          fontWeight: 'bold'
        },
        subtextStyle: {
          color: '#E67E22'
        }
      } : undefined,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: legendData,
        selected: {
          'K线': true,
          'MA5': true, 
          'MA10': true, 
          'MA20': true, 
          'MA30': true,
          'BOLL': showBOLL,
          'UB': showBOLL,
          'LB': showBOLL,
          'DIF': showMACD,
          'DEA': showMACD,
          'MACD': showMACD,
          '成交量': showVOL
        },
        top: stockData.is_mock ? 30 : 0
      },
      axisPointer: {
        link: { xAxisIndex: 'all' }
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: Array.from({length: gridCount}, (_, i) => i),
          start: 80,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          xAxisIndex: Array.from({length: gridCount}, (_, i) => i),
          bottom: 5,
          start: 80,
          end: 100
        }
      ],
      series: series
    };
    
    // 应用配置
    chart.value.setOption(option, true);
    
  } catch (error) {
    console.error('图表渲染错误:', error);
    // 显示错误提示
    try {
      chart.value.dispose();
      chart.value = echarts.init(chartContainer.value);
      chart.value.setOption({
        title: {
          text: '图表渲染出错，请稍后再试',
          left: 'center',
          top: 'center'
        }
      });
    } catch (finalError) {
      console.error('无法显示错误信息:', finalError);
    }
  }
}

// 添加清理函数
const clearChart = () => {
  if (chart.value) {
    window.removeEventListener('resize', handleResize);
    chart.value.dispose();
    chart.value = null;
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchBoards()
}

const handleModeChange = () => {
  currentPage.value = 1;
  selectedBoard.value = null;
  selectedStock.value = null;
  
  if (mode.value === 'all') {
    // 在全市场模式下直接获取所有股票
    fetchStocks('ALL');
  } else {
    // 板块模式下，先加载板块列表
    fetchBoards();
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchBoards()
}

const handleBoardClick = async (row) => {
  selectedBoard.value = row
  selectedStock.value = null
  await fetchStocks(row.code)
}

const handleStockClick = async (row) => {
  try {
    if (!row || !row.code) {
      ElMessage.error('无效的股票数据');
      return;
    }
    
    console.log('点击股票:', row);
    
    // 先显示基础信息
    selectedStock.value = { 
      ...row, 
      breakthrough: row.breakthrough,  // 保持列表页的突破状态一致性
      kdata: [] // 初始时确保kdata存在但为空数组
    };
    
    // 清空旧图表
    clearChart();
    
    // 获取完整的股票详情
    ElMessage.info(`正在加载 ${row.name}(${row.code}) 的详细数据...`);
    
    try {
      const detail = await fetchStockDetail(row.code);
      
      if (detail) {
        // 合并详情数据，但保持突破状态与列表页一致
        selectedStock.value = {
          ...detail,
          breakthrough: row.breakthrough, // 确保突破状态一致性
          name: detail.is_mock ? `【模拟数据】${detail.name}` : detail.name
        };
        
        // 如果是模拟数据，显示提示
        if (detail.is_mock) {
          ElMessage.warning(`正在使用模拟数据显示 ${row.name}(${row.code})，实际数据可能有差异`);
        }
        
        // 重新初始化图表
        nextTick(() => {
          initChart();
          if (chart.value) {
            updateChart(selectedStock.value);
          } else {
            console.error('图表初始化失败');
            ElMessage.error('无法初始化图表，请刷新页面重试');
          }
        });
      } else {
        ElMessage.warning(`获取 ${row.name}(${row.code}) 的K线数据失败，仅显示基本信息`);
      }
    } catch (error) {
      console.error('获取股票详情数据失败:', error);
      ElMessage.error(`无法获取 ${row.name}(${row.code}) 的详细数据`);
    }
  } catch (error) {
    console.error('处理股票点击异常:', error);
    ElMessage.error('无法加载股票详情');
  }
}

const refreshData = async () => {
  if (mode.value === 'all' || selectedBoard.value) {
    const boardCode = selectedBoard.value ? selectedBoard.value.code : 'ALL'
    await fetchStocks(boardCode)
    ElMessage.success('数据已刷新')
  } else {
    await fetchBoards()
    ElMessage.success('板块列表已刷新')
  }
}

// WebSocket连接
const connectWebSocket = () => {
  try {
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'update') {
        ElMessage.success('数据已更新')
        refreshData()
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket连接已关闭')
      // 尝试重连
      setTimeout(connectWebSocket, 5000)
    }
  } catch (error) {
    console.error('WebSocket连接失败:', error)
  }
}

// 在selectedStock变化时更新图表
watch(selectedStock, (newVal) => {
  if (newVal && chartContainer.value) {
    initChart()
  }
})

// 添加对chartIndicators变化的监听
watch(chartIndicators, () => {
  if (selectedStock.value && chart.value) {
    updateChart(selectedStock.value);
  }
}, { deep: true });

// 生命周期钩子
onMounted(() => {
  if (mode.value === 'board') {
    fetchBoards()
  } else {
    fetchStocks('ALL')
  }
  
  // 连接WebSocket
  connectWebSocket()
})
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 0;
  background-color: #f5f7fa;
  max-width: 1440px;  /* 添加最大宽度限制 */
  margin: 0 auto;     /* 居中显示 */
}

/* 顶部区域样式 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;  /* 增加内边距 */
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.08);
  border-radius: 0 0 8px 8px;  /* 添加圆角 */
  margin-bottom: 20px;  /* 增加与下方内容的间距 */
}

.app-title {
  margin: 0;
  font-size: 24px;  /* 增大字体 */
  font-weight: 600;  /* 增加字重 */
  color: #303133;
}

.search-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-input {
  width: 250px;
}

.mode-toggle {
  margin-left: 8px;
}

.refresh-button {
  margin-left: 8px;
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  padding: 20px 24px;  /* 增加水平内边距 */
  overflow: auto;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.selected-board {
  font-size: 16px;
  color: #606266;
  margin-left: 8px;
}

.table-container {
  background-color: #fff;
  border-radius: 8px;  /* 增加圆角 */
  box-shadow: 0 2px 16px 0 rgba(0, 0, 0, 0.06);  /* 柔化阴影 */
  padding: 24px;  /* 增加内边距 */
  margin-bottom: 24px;  /* 增加底部间距 */
}

.data-table {
  margin-bottom: 24px;
}

.data-table :deep(.el-table__header) th {
  background-color: #f7fafc;  /* 表头背景色 */
  font-weight: 600;
  padding: 12px 8px;  /* 调整单元格内边距 */
}

.data-table :deep(.el-table__row) td {
  padding: 14px 8px;  /* 增加单元格内边距 */
  border-bottom: 1px solid #eef2f7;  /* 细化边框 */
}

.back-link {
  margin-top: 16px;
  text-align: left;
}

.back-button {
  font-size: 14px;
}

/* 股票详情区样式 */
.stock-detail {
  margin-top: 24px;
  padding: 24px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 16px 0 rgba(0, 0, 0, 0.06);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  border-bottom: 1px solid #eef2f7;  /* 添加底部边框 */
  padding-bottom: 16px;  /* 增加底部内边距 */
}

.stock-title {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}

.stock-price {
  margin-left: 16px;
  font-size: 24px;
  font-weight: 700;
  color: #f56c6c;
}

.detail-content {
  display: flex;
  gap: 24px;
}

.info-card {
  width: 300px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
  overflow: hidden;  /* 确保圆角生效 */
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
}

.label {
  color: #909399;
  margin-right: 8px;
}

.value {
  font-weight: 500;
  color: #303133;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f7fafc;  /* 添加背景色 */
  padding: 14px 20px;  /* 增加内边距 */
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.chart-card {
  flex: 1;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
  overflow: hidden;  /* 确保圆角生效 */
}

.chart-container {
  height: 500px;  /* 增加图表高度 */
  width: 100%;
  padding: 20px;  /* 添加内边距 */
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.data-table :deep(.el-table__cell) {
  text-align: center;
}

.data-table :deep(.el-button) {
  padding: 8px 16px;
}

@media (max-width: 768px) {
  .detail-content {
    flex-direction: column;
  }
  
  .info-card {
    width: 100%;
  }
}
</style> 