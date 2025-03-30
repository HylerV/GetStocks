<template>
  <div class="home">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>股票分析系统</h1>
          <div class="header-buttons">
            <el-button type="primary" @click="loadAvailableBoards" :loading="loadingAvailable">
              获取有效板块
            </el-button>
            <el-button type="success" @click="refreshAllData" :loading="loading">
              刷新数据
            </el-button>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card class="board-card">
              <template #header>
                <div class="card-header">
                  <span>板块列表</span>
                  <el-input
                    v-model="searchQuery"
                    placeholder="搜索板块"
                    clearable
                    @clear="handleSearch"
                    @input="handleSearch"
                  >
                    <template #prefix>
                      <el-icon><Search /></el-icon>
                    </template>
                  </el-input>
                </div>
              </template>
              
              <el-tabs v-model="activeTab">
                <el-tab-pane label="全部板块" name="all">
                  <el-table
                    :data="filteredBoards"
                    style="width: 100%"
                    height="calc(100vh - 300px)"
                    @row-click="handleBoardClick"
                  >
                    <el-table-column prop="板块名称" label="板块名称" />
                    <el-table-column prop="板块代码" label="板块代码" width="120" />
                  </el-table>
                </el-tab-pane>
                
                <el-tab-pane label="有效板块" name="available">
                  <el-table
                    :data="availableBoards"
                    style="width: 100%"
                    height="calc(100vh - 300px)"
                    @row-click="handleAvailableBoardClick"
                  >
                    <el-table-column prop="name" label="板块名称">
                      <template #default="scope">
                        <span>{{ scope.row.name || '未分类股票' }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="code" label="板块代码" width="120">
                      <template #default="scope">
                        <span>{{ scope.row.code || 'OTHER' }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="符合条件的股票" min-width="200">
                      <template #default="scope">
                        <el-popover
                          placement="right"
                          :width="600"
                          trigger="hover"
                        >
                          <template #reference>
                            <el-tag type="success">
                              {{ (scope.row.matching_stocks || []).length }} 只
                            </el-tag>
                          </template>
                          <div class="stock-popover">
                            <el-table :data="scope.row.matching_stocks || []" size="small">
                              <el-table-column prop="code" label="代码" width="100" />
                              <el-table-column prop="name" label="名称" />
                              <el-table-column prop="current_price" label="当前价" width="100" />
                              <el-table-column label="斐波那契位" width="120">
                                <template #default="{ row }">
                                  {{ row.fib_qfq }}
                                </template>
                              </el-table-column>
                              <el-table-column label="突破状态" width="100">
                                <template #default="{ row }">
                                  <el-tag :type="row.current_price > row.fib_qfq ? 'success' : 'info'">
                                    {{ row.current_price > row.fib_qfq ? '已突破' : '未突破' }}
                                  </el-tag>
                                </template>
                              </el-table-column>
                              <el-table-column label="操作" width="100">
                                <template #default="{ row }">
                                  <el-button type="primary" link @click.stop="showStockDetail(row)">
                                    详情
                                  </el-button>
                                </template>
                              </el-table-column>
                            </el-table>
                          </div>
                        </el-popover>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
              </el-tabs>
            </el-card>
          </el-col>
          
          <el-col :span="16">
            <el-card v-if="selectedStock" class="stock-detail-card">
              <template #header>
                <div class="card-header">
                  <span>{{ selectedStock.name }} ({{ selectedStock.code }}) - 分析详情</span>
                  <el-button type="primary" @click="refreshStockData" :loading="loading">
                    刷新数据
                  </el-button>
                </div>
              </template>
              
              <div class="stock-info">
                <el-descriptions :column="3" border>
                  <el-descriptions-item label="当前价格">{{ selectedStock.current_price }}</el-descriptions-item>
                  <el-descriptions-item label="斐波那契位">{{ selectedStock.fib_qfq }}</el-descriptions-item>
                  <el-descriptions-item label="突破状态">
                    <el-tag :type="selectedStock.current_price > selectedStock.fib_qfq ? 'success' : 'info'">
                      {{ selectedStock.current_price > selectedStock.fib_qfq ? '已突破' : '未突破' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="后复权前低">{{ selectedStock.prev_low_hfq }}</el-descriptions-item>
                  <el-descriptions-item label="后复权前高">{{ selectedStock.prev_high_hfq }}</el-descriptions-item>
                  <el-descriptions-item label="后复权0.618位">{{ selectedStock.fib_hfq }}</el-descriptions-item>
                  <el-descriptions-item label="除权前低">{{ selectedStock.prev_low_qfq }}</el-descriptions-item>
                  <el-descriptions-item label="除权前高">{{ selectedStock.prev_high_qfq }}</el-descriptions-item>
                  <el-descriptions-item label="除权0.618位">{{ selectedStock.fib_qfq }}</el-descriptions-item>
                </el-descriptions>
              </div>
              
              <div class="stock-chart">
                <div ref="chartRef" style="height: 400px;"></div>
              </div>
            </el-card>
            
            <el-empty v-else description="请选择一只股票查看详情" />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Search, Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const router = useRouter()
const boards = ref([])
const availableBoards = ref([])
const searchQuery = ref('')
const selectedStock = ref(null)
const loading = ref(false)
const loadingAvailable = ref(false)
const activeTab = ref('all')
const chartRef = ref(null)
let chart = null

const filteredBoards = computed(() => {
  if (!searchQuery.value) return boards.value
  const query = searchQuery.value.toLowerCase()
  return boards.value.filter(board => 
    board.板块名称.toLowerCase().includes(query) ||
    board.板块代码.toLowerCase().includes(query)
  )
})

const fetchBoards = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/boards')
    boards.value = response.data
  } catch (error) {
    console.error('获取板块列表失败:', error)
    ElMessage.error('获取板块列表失败，请刷新页面重试')
  }
}

const loadAvailableBoards = async () => {
  if (loadingAvailable.value) return
  
  loadingAvailable.value = true
  try {
    const response = await axios.get('http://localhost:8000/api/boards/available')
    availableBoards.value = response.data.boards
    activeTab.value = 'available'
    
    if (availableBoards.value.length === 0) {
      ElMessage.warning('没有找到符合条件的板块')
    } else {
      ElMessage.success(`找到 ${availableBoards.value.length} 个有效板块`)
    }
  } catch (error) {
    console.error('获取有效板块失败:', error)
    ElMessage.error('获取有效板块失败，请重试')
  } finally {
    loadingAvailable.value = false
  }
}

const handleSearch = () => {
  // 搜索逻辑已通过计算属性实现
}

const handleBoardClick = async (row) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/board/${row.板块代码}/stocks`)
    if (response.data.stocks && response.data.stocks.length > 0) {
      showStockDetail(response.data.stocks[0])
    }
  } catch (error) {
    console.error('获取板块股票失败:', error)
    ElMessage.error('获取板块股票失败')
  }
}

const handleAvailableBoardClick = async (row) => {
  try {
    // 如果是未分类股票，直接显示第一只股票的详情
    if (row.code === 'OTHER' && row.matching_stocks && row.matching_stocks.length > 0) {
      showStockDetail(row.matching_stocks[0])
      return
    }
    
    const response = await axios.get(`http://localhost:8000/api/board/${row.code}/stocks`)
    if (response.data.stocks && response.data.stocks.length > 0) {
      showStockDetail(response.data.stocks[0])
    }
  } catch (error) {
    console.error('获取板块股票失败:', error)
    ElMessage.error('获取板块股票失败')
  }
}

const showStockDetail = async (stock) => {
  if (!stock) return
  
  selectedStock.value = stock
  await nextTick()
  initChart()
  loadStockHistory(stock.code)
}

const initChart = () => {
  if (!chartRef.value) return
  
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  
  const option = {
    title: {
      text: '股票K线图'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', '成交量', '斐波那契位']
    },
    grid: [{
      left: '10%',
      right: '8%',
      height: '60%'
    }, {
      left: '10%',
      right: '8%',
      top: '75%',
      height: '20%'
    }],
    xAxis: [{
      type: 'category',
      data: [],
      scale: true,
      boundaryGap: true,
      axisLine: { onZero: false },
      splitLine: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    }, {
      type: 'category',
      gridIndex: 1,
      data: [],
      scale: true,
      boundaryGap: true,
      axisLine: { onZero: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    }],
    yAxis: [{
      scale: true,
      splitArea: {
        show: true
      }
    }, {
      gridIndex: 1,
      splitNumber: 2,
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false }
    }],
    dataZoom: [{
      type: 'inside',
      xAxisIndex: [0, 1],
      start: 0,
      end: 100
    }, {
      show: true,
      xAxisIndex: [0, 1],
      type: 'slider',
      bottom: '0%',
      start: 0,
      end: 100
    }],
    series: [{
      name: 'K线',
      type: 'candlestick',
      data: [],
      itemStyle: {
        color: '#ef232a',
        color0: '#14b143',
        borderColor: '#ef232a',
        borderColor0: '#14b143'
      }
    }, {
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: []
    }, {
      name: '斐波那契位',
      type: 'line',
      data: [],
      symbol: 'none',
      lineStyle: {
        color: '#ffd700',
        width: 2,
        type: 'dashed'
      }
    }]
  }
  
  chart.setOption(option)
}

const loadStockHistory = async (code) => {
  try {
    const response = await axios.get(`http://localhost:8000/api/stock/${code}/history`)
    if (response.data.history) {
      const history = response.data.history
      const dates = history.map(item => item.date)
      const kLineData = history.map(item => [
        item.open,
        item.close,
        item.low,
        item.high
      ])
      const volumes = history.map(item => item.volume)
      const fibLevels = history.map(() => selectedStock.value.fib_qfq)
      
      chart.setOption({
        xAxis: [{
          data: dates
        }, {
          data: dates
        }],
        series: [{
          data: kLineData
        }, {
          data: volumes
        }, {
          data: fibLevels
        }]
      })
    }
  } catch (error) {
    console.error('获取股票历史数据失败:', error)
    ElMessage.error('获取股票历史数据失败')
  }
}

const refreshStockData = async () => {
  if (!selectedStock.value) return
  
  loading.value = true
  try {
    const response = await axios.get(`http://localhost:8000/api/stock/${selectedStock.value.code}/refresh`)
    selectedStock.value = response.data
    ElMessage.success('数据刷新成功')
  } catch (error) {
    console.error('刷新股票数据失败:', error)
    ElMessage.error('刷新股票数据失败')
  } finally {
    loading.value = false
  }
}

const refreshAllData = async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchBoards(),
      loadAvailableBoards()
    ])
    ElMessage.success('数据刷新成功')
  } catch (error) {
    console.error('刷新数据失败:', error)
    ElMessage.error('刷新数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBoards()
  
  window.addEventListener('resize', () => {
    if (chart) {
      chart.resize()
    }
  })
})
</script>

<style scoped>
.home {
  height: 100vh;
  background-color: #f5f7fa;
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #dcdfe6;
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.el-main {
  padding: 20px;
}

.board-card {
  height: calc(100vh - 120px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.stock-detail-card {
  height: calc(100vh - 120px);
}

.stock-info {
  margin-bottom: 20px;
}

.stock-chart {
  margin-top: 20px;
}

.stock-popover {
  max-height: 400px;
  overflow-y: auto;
}

h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.el-input {
  width: 200px;
}

.el-descriptions {
  margin-bottom: 20px;
}

.el-tag {
  margin-right: 5px;
}
</style> 