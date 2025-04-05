<template>
  <div class="container">
    <div class="left-panel">
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索板块"
          clearable
          @input="handleSearch"
        />
        <el-radio-group v-model="mode" @change="handleModeChange">
          <el-radio label="board">板块模式</el-radio>
          <el-radio label="all">全市场模式</el-radio>
        </el-radio-group>
      </div>
      
      <el-table
        v-loading="loading"
        :data="filteredBoards"
        style="width: 100%"
        @row-click="handleBoardClick"
      >
        <el-table-column prop="name" label="板块名称" />
        <el-table-column prop="code" label="板块代码" width="100" />
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalBoards"
        @current-change="handlePageChange"
      />
    </div>
    
    <div class="right-panel">
      <div v-if="selectedBoard" class="board-info">
        <h2>{{ selectedBoard.name }}</h2>
        <el-button type="primary" @click="refreshData">刷新数据</el-button>
      </div>
      
      <el-table
        v-loading="stocksLoading"
        :data="currentStocks"
        style="width: 100%"
        @row-click="handleStockClick"
      >
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="current_price" label="当前价" width="100" />
        <el-table-column prop="market_cap" label="市值(亿)" width="100" />
        <el-table-column label="突破状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.breakthrough_status ? 'success' : 'info'">
              {{ row.breakthrough_status ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      
      <div v-if="selectedStock" class="stock-chart">
        <div ref="chartContainer" style="width: 100%; height: 400px;"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
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
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value,
        search: searchKeyword.value
      }
    })
    boards.value = response.data
    totalBoards.value = response.headers['x-total-count'] || boards.value.length
  } catch (error) {
    ElMessage.error('获取板块列表失败')
  } finally {
    loading.value = false
  }
}

const fetchStocks = async (boardCode) => {
  try {
    stocksLoading.value = true
    const response = await axios.get(`/api/boards/${boardCode}/stocks`)
    currentStocks.value = response.data
  } catch (error) {
    ElMessage.error('获取股票列表失败')
  } finally {
    stocksLoading.value = false
  }
}

const fetchStockHistory = async (stockCode) => {
  try {
    const response = await axios.get(`/api/stocks/${stockCode}/history`)
    return response.data
  } catch (error) {
    ElMessage.error('获取历史数据失败')
    return []
  }
}

const initChart = () => {
  if (chartContainer.value) {
    chart.value = echarts.init(chartContainer.value)
  }
}

const updateChart = async (stockCode) => {
  if (!chart.value) return
  
  const history = await fetchStockHistory(stockCode)
  const dates = history.map(item => item.date)
  const data = history.map(item => [
    item.open,
    item.close,
    item.low,
    item.high
  ])
  
  const option = {
    title: {
      text: `${selectedStock.value.name} K线图`
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    xAxis: {
      data: dates
    },
    yAxis: {},
    series: [{
      type: 'candlestick',
      data: data
    }]
  }
  
  chart.value.setOption(option)
}

const handleSearch = () => {
  currentPage.value = 1
  fetchBoards()
}

const handleModeChange = () => {
  currentPage.value = 1
  fetchBoards()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchBoards()
}

const handleBoardClick = async (row) => {
  selectedBoard.value = row
  await fetchStocks(row.code)
}

const handleStockClick = async (row) => {
  selectedStock.value = row
  await updateChart(row.code)
}

const refreshData = async () => {
  if (selectedBoard.value) {
    await fetchStocks(selectedBoard.value.code)
  }
}

// WebSocket连接
const connectWebSocket = () => {
  const ws = new WebSocket('ws://localhost:8000/ws')
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'update') {
      ElMessage.success('数据已更新')
      if (selectedBoard.value) {
        fetchStocks(selectedBoard.value.code)
      }
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }
}

// 生命周期钩子
onMounted(() => {
  fetchBoards()
  initChart()
  connectWebSocket()
})
</script>

<style scoped>
.container {
  display: flex;
  height: 100vh;
  padding: 20px;
  gap: 20px;
}

.left-panel {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.search-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.board-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-chart {
  margin-top: 20px;
}
</style> 