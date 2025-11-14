<template>
  <div class="min-h-screen bg-gray-100">
    <div class="container mx-auto p-4">
      <!-- 头部 -->
      <header class="bg-white rounded-lg shadow-lg p-6 mb-4">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">FinAI MT5 A股交易平台</h1>
        <p class="text-gray-600">实时行情 · 智能交易 · 投资组合管理</p>
      </header>

      <!-- 账户信息 -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-gray-500 text-sm">总资产</div>
          <div class="text-2xl font-bold text-blue-600">¥{{ formatNumber(account.totalAssets) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-gray-500 text-sm">可用资金</div>
          <div class="text-2xl font-bold text-green-600">¥{{ formatNumber(account.cash) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-gray-500 text-sm">持仓市值</div>
          <div class="text-2xl font-bold text-purple-600">¥{{ formatNumber(account.marketValue) }}</div>
        </div>
        <div class="bg-white rounded-lg shadow p-4">
          <div class="text-gray-500 text-sm">盈亏</div>
          <div class="text-2xl font-bold" :class="account.profit >= 0 ? 'text-green-600' : 'text-red-600'">
            {{ account.profit >= 0 ? '+' : '' }}¥{{ formatNumber(account.profit) }}
          </div>
        </div>
      </div>

      <!-- 主要内容区 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- 左侧 -->
        <div class="lg:col-span-2 space-y-4">
          <!-- 股票搜索 -->
          <div class="bg-white rounded-lg shadow p-4">
            <h2 class="text-xl font-bold mb-4">股票搜索</h2>
            <div class="flex gap-2 mb-4">
              <input 
                v-model="searchKeyword" 
                @keyup.enter="searchStock"
                type="text" 
                placeholder="输入股票代码或名称" 
                class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
              <button @click="searchStock" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                搜索
              </button>
            </div>
            <div v-if="searchResults.length > 0" class="space-y-2">
              <div 
                v-for="stock in searchResults" 
                :key="stock.symbol"
                @click="selectStock(stock)"
                class="border rounded p-2 hover:bg-gray-50 cursor-pointer"
              >
                <div class="font-bold">{{ stock.symbol }}</div>
                <div class="text-sm text-gray-600">{{ stock.description }}</div>
              </div>
            </div>
          </div>

          <!-- 热门股票 -->
          <div class="bg-white rounded-lg shadow p-4">
            <h2 class="text-xl font-bold mb-4">热门股票</h2>
            <div class="space-y-2">
              <div 
                v-for="stock in hotStocks" 
                :key="stock.symbol"
                @click="selectStock(stock)"
                class="border rounded p-3 hover:bg-gray-50 cursor-pointer transition"
              >
                <div class="flex justify-between items-center">
                  <div>
                    <div class="font-bold">{{ stock.symbol }}</div>
                    <div class="text-sm text-gray-600">{{ stock.name }}</div>
                  </div>
                  <div class="text-blue-600 font-bold">
                    {{ stock.price ? '¥' + stock.price.toFixed(2) : '--' }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 交易面板 -->
          <div v-if="selectedStock" class="bg-white rounded-lg shadow p-4">
            <h2 class="text-xl font-bold mb-4">
              交易 - {{ selectedStock.symbol }} {{ selectedStock.name }}
            </h2>
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block text-sm text-gray-600 mb-2">当前价格</label>
                <div class="text-2xl font-bold text-blue-600">
                  ¥{{ selectedStock.price ? selectedStock.price.toFixed(2) : '--' }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-600 mb-2">数量（手）</label>
                <input 
                  v-model.number="tradeQuantity" 
                  type="number" 
                  min="1" 
                  step="1"
                  class="w-full px-4 py-2 border rounded-lg"
                >
              </div>
            </div>
            <div class="flex gap-2">
              <button 
                @click="placeOrder('BUY')" 
                class="flex-1 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-bold"
              >
                买入
              </button>
              <button 
                @click="placeOrder('SELL')" 
                class="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-bold"
              >
                卖出
              </button>
            </div>
          </div>
        </div>

        <!-- 右侧 -->
        <div class="space-y-4">
          <!-- 持仓 -->
          <div class="bg-white rounded-lg shadow p-4">
            <h2 class="text-xl font-bold mb-4">我的持仓</h2>
            <div v-if="positions.length > 0" class="space-y-2">
              <div 
                v-for="pos in positions" 
                :key="pos.symbol"
                @click="selectStockBySymbol(pos.symbol)"
                class="border rounded p-2 hover:bg-gray-50 cursor-pointer"
              >
                <div class="flex justify-between items-center">
                  <div>
                    <div class="font-bold">{{ pos.symbol }}</div>
                    <div class="text-sm text-gray-600">{{ pos.volume }}手</div>
                  </div>
                  <div class="text-right">
                    <div class="font-bold text-blue-600">¥{{ pos.price_open.toFixed(2) }}</div>
                    <div class="text-sm" :class="pos.profit >= 0 ? 'text-green-600' : 'text-red-600'">
                      {{ pos.profit >= 0 ? '+' : '' }}¥{{ pos.profit.toFixed(2) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-gray-400 text-center py-4">暂无持仓</div>
          </div>

          <!-- AI交易 -->
          <div class="bg-white rounded-lg shadow p-4">
            <h2 class="text-xl font-bold mb-4">AI自动交易</h2>
            <button 
              @click="triggerAI" 
              :disabled="aiLoading"
              class="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-bold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🤖 {{ aiLoading ? '执行中...' : '触发AI交易' }}
            </button>
            <div v-if="aiStatus" class="mt-2 text-sm text-center" :class="aiStatusClass">
              {{ aiStatus }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'

const API_BASE = '/api'

// 数据
const account = ref({
  totalAssets: 0,
  cash: 0,
  marketValue: 0,
  profit: 0
})

const hotStocks = ref([
  { symbol: '600000', name: '浦发银行', price: null },
  { symbol: '000001', name: '平安银行', price: null },
  { symbol: '600036', name: '招商银行', price: null },
  { symbol: '600519', name: '贵州茅台', price: null },
  { symbol: '601318', name: '中国平安', price: null },
  { symbol: '000002', name: '万科A', price: null }
])

const positions = ref([])
const searchKeyword = ref('')
const searchResults = ref([])
const selectedStock = ref(null)
const tradeQuantity = ref(1)
const aiLoading = ref(false)
const aiStatus = ref('')

let refreshTimer = null

// 计算属性
const aiStatusClass = computed(() => {
  if (aiStatus.value.includes('✅')) return 'text-green-600'
  if (aiStatus.value.includes('❌')) return 'text-red-600'
  return 'text-gray-600'
})

// 方法
const formatNumber = (num) => {
  return num.toFixed(2)
}

const loadAccount = async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/mt5/account`)
    if (data.success) {
      account.value.totalAssets = data.data.total_assets
      account.value.cash = data.data.cash
      account.value.marketValue = data.data.market_val
      account.value.profit = data.data.total_assets - 1000000
    }
  } catch (e) {
    console.error('加载账户失败:', e)
  }
}

const loadPositions = async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/mt5/positions`)
    if (data.success) {
      positions.value = data.data
    }
  } catch (e) {
    console.error('加载持仓失败:', e)
  }
}

const updateHotStockPrices = async () => {
  for (const stock of hotStocks.value) {
    try {
      const { data } = await axios.get(`${API_BASE}/mt5/price/${stock.symbol}`)
      if (data.success) {
        stock.price = data.data.price
      }
    } catch (e) {
      console.error('更新价格失败:', e)
    }
  }
}

const searchStock = async () => {
  if (!searchKeyword.value) return
  try {
    const { data } = await axios.get(`${API_BASE}/mt5/search/${searchKeyword.value}`)
    if (data.success) {
      searchResults.value = data.data
    }
  } catch (e) {
    console.error('搜索失败:', e)
  }
}

const selectStock = async (stock) => {
  selectedStock.value = {
    symbol: stock.symbol,
    name: stock.name || stock.description,
    price: null
  }
  await updateSelectedStockPrice()
}

const selectStockBySymbol = async (symbol) => {
  const stock = hotStocks.value.find(s => s.symbol === symbol)
  if (stock) {
    await selectStock(stock)
  }
}

const updateSelectedStockPrice = async () => {
  if (!selectedStock.value) return
  try {
    const { data } = await axios.get(`${API_BASE}/mt5/price/${selectedStock.value.symbol}`)
    if (data.success) {
      selectedStock.value.price = data.data.price
    }
  } catch (e) {
    console.error('更新价格失败:', e)
  }
}

const placeOrder = async (side) => {
  if (!selectedStock.value) return
  
  const quantity = tradeQuantity.value * 100
  if (quantity < 100) {
    alert('最小交易单位为100股（1手）')
    return
  }
  
  if (!confirm(`确认${side === 'BUY' ? '买入' : '卖出'} ${selectedStock.value.symbol} ${quantity}股？`)) {
    return
  }
  
  try {
    const { data } = await axios.post(`${API_BASE}/mt5/order`, {
      symbol: selectedStock.value.symbol,
      name: selectedStock.value.name,
      side: side,
      order_type: 'MARKET',
      quantity: quantity,
      price: selectedStock.value.price,
      use_mt5_platform: false
    })
    
    if (data.success) {
      alert('下单成功！')
      await loadAccount()
      await loadPositions()
    } else {
      alert('下单失败: ' + (data.detail || '未知错误'))
    }
  } catch (e) {
    alert('下单失败: ' + e.message)
  }
}

const triggerAI = async () => {
  aiLoading.value = true
  aiStatus.value = '🤖 AI正在分析市场...'
  
  try {
    const { data } = await axios.post(`${API_BASE}/mt5/ai/trade`)
    
    if (data.success) {
      aiStatus.value = '✅ AI交易执行完成'
      setTimeout(async () => {
        await loadAccount()
        await loadPositions()
      }, 1000)
    } else {
      aiStatus.value = '❌ AI交易失败'
    }
  } catch (e) {
    aiStatus.value = '❌ 连接失败'
  }
  
  aiLoading.value = false
  setTimeout(() => aiStatus.value = '', 3000)
}

const startRefresh = () => {
  refreshTimer = setInterval(async () => {
    await loadAccount()
    await loadPositions()
    await updateHotStockPrices()
    if (selectedStock.value) {
      await updateSelectedStockPrice()
    }
  }, 5000)
}

const stopRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
}

// 生命周期
onMounted(async () => {
  await loadAccount()
  await loadPositions()
  await updateHotStockPrices()
  startRefresh()
})

onUnmounted(() => {
  stopRefresh()
})
</script>
