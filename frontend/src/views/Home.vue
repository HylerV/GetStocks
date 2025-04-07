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
    const response = await axios.get(`/api/stocks/${boardCode}`)
    
    // 确保获取到数据
    const stocksData = response.data.data || []
    
    // 处理数据，添加斐波那契相关字段
    currentStocks.value = stocksData.map(stock => {
      return {
        ...stock,
        hfq_low: stock.fibonacci?.hfq?.low || '-',
        hfq_high: stock.fibonacci?.hfq?.high || '-',
        hfq_fib: stock.fibonacci?.hfq?.fib618 || '-',
        qfq_low: stock.fibonacci?.qfq?.low || '-',
        qfq_high: stock.fibonacci?.qfq?.high || '-',
        qfq_fib: stock.fibonacci?.qfq?.fib618 || '-',
        breakthrough: stock.fibonacci?.breakthrough || '否'
      }
    })
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
      const response = await axios.get(`/api/stocks/${stockCode}/detail`);
      
      // 检查返回数据格式
      if (response.data && response.data.success && response.data.data) {
        const stockDetail = response.data.data;
        
        // 转换并返回数据
        return {
          ...stockDetail,
          kdata: stockDetail.kdata || [],
          fibonacci: stockDetail.fibonacci || {
            hfq: { low: '-', high: '-', fib618: '-' },
            qfq: { low: '-', high: '-', fib618: '-' },
            dates: { low_date: '-', high_date: '-' },
            breakthrough: '否'
          },
          hfq_low: stockDetail.fibonacci?.hfq?.low || '-',
          hfq_high: stockDetail.fibonacci?.hfq?.high || '-',
          hfq_fib: stockDetail.fibonacci?.hfq?.fib618 || '-',
          qfq_low: stockDetail.fibonacci?.qfq?.low || '-',
          qfq_high: stockDetail.fibonacci?.qfq?.high || '-',
          qfq_fib: stockDetail.fibonacci?.qfq?.fib618 || '-',
          breakthrough: stockDetail.fibonacci?.breakthrough || '否'
        };
      } else {
        // 尝试替代API路径
        const altResponse = await axios.get(`/api/stocks/${stockCode}`);
        return altResponse.data;
      }
    } catch (error) {
      retries++;
      if (retries >= maxRetries) {
        ElMessage.error(`获取股票详情失败 (${retries}/${maxRetries})`);
        console.error('获取股票详情失败:', error);
        return null;
      }
      // 等待一段时间后重试
      await new Promise(resolve => setTimeout(resolve, 1000));
      ElMessage.warning(`正在重试获取股票详情 (${retries}/${maxRetries})...`);
    } finally {
      stocksLoading.value = false;
    }
  }
}

const initChart = () => {
  if (chartContainer.value && !chart.value) {
    chart.value = echarts.init(chartContainer.value)
    window.addEventListener('resize', () => {
      chart.value.resize()
    })
  }
}

const updateChart = (stockData) => {
  if (!chart.value || !stockData || !stockData.kdata || stockData.kdata.length === 0) {
    return;
  }
  
  // 每次更新图表时先销毁旧图表，完全重新创建
  chart.value.dispose();
  chart.value = echarts.init(chartContainer.value);
  
  const kdata = stockData.kdata;
  
  // 准备数据
  const dates = kdata.map(item => item.date);
  const data = kdata.map(item => [item.open, item.close, item.low, item.high]);
  
  // 计算MACD指标
  const calculateMACD = (closeData, shortPeriod = 12, longPeriod = 26, signalPeriod = 9) => {
    const dif = [];
    const dea = [];
    const macd = [];
    
    // 计算EMA
    const calculateEMA = (data, period) => {
      const k = 2 / (period + 1);
      const ema = [];
      
      for (let i = 0; i < data.length; i++) {
        if (i === 0) {
          ema.push(data[i]);
        } else {
          ema.push(data[i] * k + ema[i - 1] * (1 - k));
        }
      }
      
      return ema;
    };
    
    const closeValues = kdata.map(item => parseFloat(item.close));
    const shortEMA = calculateEMA(closeValues, shortPeriod);
    const longEMA = calculateEMA(closeValues, longPeriod);
    
    // 计算DIF
    for (let i = 0; i < closeValues.length; i++) {
      dif.push(shortEMA[i] - longEMA[i]);
    }
    
    // 计算DEA
    const deaEMA = calculateEMA(dif, signalPeriod);
    for (let i = 0; i < dif.length; i++) {
      dea.push(deaEMA[i]);
      // 计算MACD柱状值
      macd.push((dif[i] - dea[i]) * 2);
    }
    
    return { dif, dea, macd };
  };
  
  // 计算布林带
  const calculateBOLL = (closeData, period = 20, multiplier = 2) => {
    const upper = [];
    const middle = [];
    const lower = [];
    
    const closeValues = kdata.map(item => parseFloat(item.close));
    
    for (let i = 0; i < closeValues.length; i++) {
      if (i < period - 1) {
        upper.push(null);
        middle.push(null);
        lower.push(null);
        continue;
      }
      
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) {
        sum += closeValues[j];
      }
      
      const ma = sum / period;
      
      let squareSum = 0;
      for (let j = i - period + 1; j <= i; j++) {
        squareSum += Math.pow(closeValues[j] - ma, 2);
      }
      
      const std = Math.sqrt(squareSum / period);
      
      middle.push(ma);
      upper.push(ma + multiplier * std);
      lower.push(ma - multiplier * std);
    }
    
    return { upper, middle, lower };
  };
  
  // 计算成交量
  const volumes = kdata.map(item => parseFloat(item.volume || 0));
  
  // 计算指标
  const macdData = calculateMACD(kdata);
  const bollData = calculateBOLL(kdata);
  
  // 获取斐波那契水平线
  const fibonacci = stockData.fibonacci || {};
  const fibLineValue = parseFloat(fibonacci.qfq?.fib618) || null;
  
  // 构建图表选项
  const grids = [];
  const xAxis = [];
  const yAxis = [];
  
  // 计算指标数量
  const showMACD = chartIndicators.value.includes('MACD');
  const showBOLL = chartIndicators.value.includes('BOLL');
  const showVOL = chartIndicators.value.includes('VOL');
  const indicatorCount = (showMACD ? 1 : 0) + (showVOL ? 1 : 0);
  
  // 主K线图网格
  const mainHeight = indicatorCount > 0 ? '60%' : '85%';
  grids.push({
    left: '10%', 
    right: '8%',
    top: '5%',
    height: mainHeight
  });
  
  xAxis.push({
    type: 'category',
    data: dates,
    gridIndex: 0,
    scale: true,
    boundaryGap: false,
    axisLine: { onZero: false },
    splitLine: { show: false },
    axisLabel: {
      formatter: function (value) {
        return value.substring(5); // 只显示月-日
      }
    },
    min: 'dataMin',
    max: 'dataMax'
  });
  
  yAxis.push({
    scale: true,
    gridIndex: 0,
    splitArea: {
      show: true
    }
  });
  
  // 指标图的位置计算
  let macdIndex = -1;
  let volIndex = -1;
  
  if (indicatorCount > 0) {
    let position = 0;
    
    // MACD指标网格
    if (showMACD) {
      macdIndex = position + 1;
      grids.push({
        left: '10%',
        right: '8%',
        top: '70%',
        height: '15%'
      });
      
      xAxis.push({
        type: 'category',
        gridIndex: macdIndex,
        data: dates,
        axisLabel: { show: false }
      });
      
      yAxis.push({
        gridIndex: macdIndex,
        scale: true,
        splitLine: { show: false }
      });
      
      position++;
    }
    
    // 成交量网格
    if (showVOL) {
      volIndex = position + 1;
      grids.push({
        left: '10%',
        right: '8%',
        top: showMACD ? '85%' : '70%',
        height: '10%'
      });
      
      xAxis.push({
        type: 'category',
        gridIndex: volIndex,
        data: dates,
        axisLabel: { show: true }
      });
      
      yAxis.push({
        gridIndex: volIndex,
        scale: true,
        splitLine: { show: false }
      });
      
      position++;
    }
  }
  
  // 构建图表选项
  const option = {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA30'],
      top: 0
    },
    grid: grids,
    xAxis: xAxis,
    yAxis: yAxis,
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, macdIndex, volIndex].filter(i => i >= 0),
        start: 80,
        end: 100
      },
      {
        show: true,
        type: 'slider',
        xAxisIndex: [0, macdIndex, volIndex].filter(i => i >= 0),
        bottom: 0,
        start: 80,
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: data,
        itemStyle: {
          color: '#06b06d',
          color0: '#e64b65',
          borderColor: '#06b06d',
          borderColor0: '#e64b65'
        },
        markLine: {
          symbol: 'none',
          data: fibLineValue ? [
            {
              name: '斐波那契0.618',
              yAxis: fibLineValue,
              lineStyle: {
                color: '#f39c12',
                type: 'dashed',
                width: 2
              },
              label: {
                formatter: '0.618: ' + fibLineValue
              }
            }
          ] : []
        }
      }
    ]
  };
  
  // 添加MA
  const calculateMA = (values, period) => {
    const result = [];
    for (let i = 0; i < values.length; i++) {
      if (i < period - 1) {
        result.push(null);
        continue;
      }
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) {
        sum += values[j][1];
      }
      result.push(+(sum / period).toFixed(2));
    }
    return result;
  };
  
  const ma5 = calculateMA(data, 5);
  const ma10 = calculateMA(data, 10);
  const ma20 = calculateMA(data, 20);
  const ma30 = calculateMA(data, 30);
  
  option.series.push({
    name: 'MA5',
    type: 'line',
    data: ma5,
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 1,
      opacity: 0.8
    }
  });
  
  option.series.push({
    name: 'MA10',
    type: 'line',
    data: ma10,
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 1,
      opacity: 0.8
    }
  });
  
  option.series.push({
    name: 'MA20',
    type: 'line',
    data: ma20,
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 1,
      opacity: 0.8
    }
  });
  
  option.series.push({
    name: 'MA30',
    type: 'line',
    data: ma30,
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 1,
      opacity: 0.8
    }
  });
  
  // 布林带
  if (showBOLL) {
    option.legend.data.push('BOLL', 'UB', 'LB');
    
    option.series.push({
      name: 'BOLL',
      type: 'line',
      data: bollData.middle,
      smooth: true,
      lineStyle: {
        opacity: 0.8,
        color: '#9b59b6'
      },
      symbol: 'none'
    });
    
    option.series.push({
      name: 'UB',
      type: 'line',
      data: bollData.upper,
      lineStyle: {
        opacity: 0.8,
        color: '#9b59b6'
      },
      symbol: 'none'
    });
    
    option.series.push({
      name: 'LB',
      type: 'line',
      data: bollData.lower,
      lineStyle: {
        opacity: 0.8,
        color: '#9b59b6'
      },
      symbol: 'none'
    });
  }
  
  // MACD 指标
  if (showMACD && macdIndex !== -1) {
    option.legend.data.push('DIF', 'DEA', 'MACD');
    
    option.series.push({
      name: 'DIF',
      type: 'line',
      xAxisIndex: macdIndex,
      yAxisIndex: macdIndex,
      data: macdData.dif,
      symbol: 'none',
      lineStyle: {
        width: 1.5,
        color: '#da6ee8'
      }
    });
    
    option.series.push({
      name: 'DEA',
      type: 'line',
      xAxisIndex: macdIndex,
      yAxisIndex: macdIndex,
      data: macdData.dea,
      symbol: 'none',
      lineStyle: {
        width: 1.5,
        color: '#ffab65'
      }
    });
    
    option.series.push({
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
  
  // 成交量
  if (showVOL && volIndex !== -1) {
    option.legend.data.push('成交量');
    
    option.series.push({
      name: '成交量',
      type: 'bar',
      xAxisIndex: volIndex,
      yAxisIndex: volIndex,
      data: volumes,
      itemStyle: {
        color: function(params, index) {
          const item = kdata[index];
          return parseFloat(item.close) >= parseFloat(item.open) ? '#e64b65' : '#06b06d';
        }
      }
    });
  }
  
  // 应用选项
  chart.value.setOption(option, true);
  
  // 调整图表大小
  chart.value.resize({
    width: 'auto',
    height: 600  // 设置更大的高度
  });
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
      breakthrough: row.breakthrough  // 保持列表页的突破状态一致性
    };
    
    // 清空旧图表
    if (chart.value) {
      chart.value.dispose();
      chart.value = null;
    }
    
    // 获取完整的股票详情
    ElMessage.info(`正在加载 ${row.name}(${row.code}) 的详细数据...`);
    
    const detail = await fetchStockDetail(row.code);
    
    if (detail) {
      // 合并详情数据，但保持突破状态与列表页一致
      selectedStock.value = {
        ...detail,
        breakthrough: row.breakthrough // 确保突破状态一致性
      };
      
      // 重新初始化图表
      nextTick(() => {
        initChart();
        updateChart(selectedStock.value);
      });
    } else {
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