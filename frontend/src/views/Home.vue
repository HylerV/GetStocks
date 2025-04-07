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
          <el-table-column prop="code" label="代码" width="100" />
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="current_price" label="当前价" width="100" sortable />
          <el-table-column prop="market_cap" label="市值(亿)" width="100" sortable />
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
            </div>
          </template>
          <div ref="chartContainer" class="chart-container"></div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
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
    // 确保response.data.items是一个数组
    currentStocks.value = response.data.data || []
  } catch (error) {
    ElMessage.error('获取股票列表失败')
    console.error('获取股票列表失败:', error)
    currentStocks.value = []
  } finally {
    stocksLoading.value = false
  }
}

const fetchStockDetail = async (stockCode) => {
  try {
    stocksLoading.value = true
    const response = await axios.get(`/api/stocks/${stockCode}`)
    return response.data
  } catch (error) {
    ElMessage.error('获取股票详情失败')
    console.error('获取股票详情失败:', error)
    return null
  } finally {
    stocksLoading.value = false
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

const updateChart = async (stockDetail) => {
  if (!chart.value) return
  
  const kdata = stockDetail.kdata || []
  if (!kdata.length) {
    ElMessage.warning('没有可用的历史数据')
    return
  }
  
  const dates = kdata.map(item => item.date)
  const data = kdata.map(item => [
    item.open,
    item.close,
    item.low,
    item.high
  ])
  
  // 计算斐波那契回调水平线
  let fibLines = []
  if (stockDetail.fibonacci) {
    const fib = stockDetail.fibonacci.qfq
    fibLines = [
      {
        name: '高点',
        value: fib.high,
        color: '#ff4949'
      },
      {
        name: '0.618',
        value: fib.fib618,
        color: '#13ce66'
      },
      {
        name: '低点',
        value: fib.low,
        color: '#409eff'
      }
    ]
  }
  
  const option = {
    title: {
      text: `${selectedStock.value.name} K线图`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', ...fibLines.map(line => line.name)],
      top: 30
    },
    grid: {
      left: '3%',
      right: '3%',
      bottom: '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      scale: true,
      axisLine: { lineStyle: { color: '#8392A5' } }
    },
    yAxis: {
      scale: true,
      splitArea: {
        show: true
      }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        show: true,
        type: 'slider',
        bottom: 5,
        start: 0,
        end: 100
      }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: data,
        itemStyle: {
          color: '#ff4949',
          color0: '#13ce66',
          borderColor: '#ff4949',
          borderColor0: '#13ce66'
        }
      },
      ...fibLines.map(line => ({
        name: line.name,
        type: 'line',
        data: dates.map(() => line.value),
        markLine: {
          symbol: 'none',
          lineStyle: {
            color: line.color,
            type: 'dashed'
          },
          label: {
            formatter: `${line.name}: ${line.value}`
          }
        }
      }))
    ]
  }
  
  chart.value.setOption(option, true)
  chart.value.resize()
}

const handleSearch = () => {
  currentPage.value = 1
  fetchBoards()
}

const handleModeChange = () => {
  currentPage.value = 1
  selectedBoard.value = null
  selectedStock.value = null
  
  if (mode.value === 'all') {
    fetchStocks('ALL')
  } else {
    fetchBoards()
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
  selectedStock.value = row
  
  // 获取完整的股票详情
  const detail = await fetchStockDetail(row.code)
  if (detail) {
    selectedStock.value = { ...row, ...detail }
    initChart()
    await updateChart(detail)
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
}

/* 顶部区域样式 */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.app-title {
  margin: 0;
  font-size: 20px;
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
  padding: 20px;
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
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.data-table {
  margin-bottom: 16px;
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
  margin-top: 20px;
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stock-title {
  margin: 0;
  font-size: 18px;
}

.stock-price {
  margin-left: 12px;
  font-size: 20px;
  color: #f56c6c;
}

.detail-content {
  display: flex;
  gap: 20px;
}

.info-card {
  width: 300px;
}

.chart-card {
  flex: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 400px;
  width: 100%;
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

@media (max-width: 768px) {
  .detail-content {
    flex-direction: column;
  }
  
  .info-card {
    width: 100%;
  }
}
</style> 