<template>
  <div class="stock-detail">
    <el-container>
      <el-header>
        <el-button @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>{{ stockInfo.name }} ({{ stockInfo.code }})</h2>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <el-col :span="16">
            <el-card class="chart-card">
              <div ref="chartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          
          <el-col :span="8">
            <el-card class="info-card">
              <template #header>
                <div class="card-header">
                  <span>技术分析数据</span>
                </div>
              </template>
              
              <el-descriptions :column="1" border>
                <el-descriptions-item label="当前价格">
                  {{ stockInfo.current_price }}
                </el-descriptions-item>
                <el-descriptions-item label="流通市值(亿)">
                  {{ stockInfo.market_cap }}
                </el-descriptions-item>
                <el-descriptions-item label="前复权前低价">
                  {{ stockInfo.prev_low_qfq }}
                </el-descriptions-item>
                <el-descriptions-item label="前复权前高价">
                  {{ stockInfo.prev_high_qfq }}
                </el-descriptions-item>
                <el-descriptions-item label="前复权0.618位">
                  {{ stockInfo.fib_qfq }}
                </el-descriptions-item>
                <el-descriptions-item label="突破状态">
                  <el-tag :type="stockInfo.breakthrough_status === '是' ? 'success' : 'info'">
                    {{ stockInfo.breakthrough_status }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import * as echarts from 'echarts'

const route = useRoute()
const chartRef = ref(null)
let chart = null

const stockInfo = ref({
  code: '',
  name: '',
  current_price: 0,
  market_cap: 0,
  prev_low_qfq: 0,
  prev_high_qfq: 0,
  fib_qfq: 0,
  breakthrough_status: '否'
})

const fetchStockData = async () => {
  try {
    const code = route.params.code
    const [analysisRes, historyRes] = await Promise.all([
      axios.get(`http://localhost:8000/api/stock/${code}/analysis`),
      axios.get(`http://localhost:8000/api/stock/${code}/history`)
    ])
    
    stockInfo.value = analysisRes.data
    initChart(historyRes.data)
  } catch (error) {
    console.error('获取股票数据失败:', error)
  }
}

const initChart = (data) => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  const dates = data.map(item => item.日期)
  const prices = data.map(item => item.收盘)
  
  const option = {
    title: {
      text: '历史走势图'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: dates
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: prices,
        smooth: true,
        lineStyle: {
          width: 2
        }
      }
    ],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    }
  }
  
  chart.setOption(option)
}

const handleResize = () => {
  chart?.resize()
}

onMounted(() => {
  fetchStockData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.stock-detail {
  padding: 20px;
}

.el-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  height: 600px;
}

.chart-container {
  height: 500px;
}

.info-card {
  height: 600px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.el-descriptions {
  margin-top: 20px;
}
</style> 