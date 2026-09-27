<template>
  <section class="page" data-module="pipe">
    <header class="page-head">
      <div>
        <h2>管网巡查管理</h2>
        <p class="page-desc">维护管网巡查，围绕巡查编号、巡查路段、巡查人员、巡查日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记管网巡查</button>
        <button class="btn" type="button" @click="exportRows">导出管网巡查清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无管网巡查数据，可先登记管网巡查</td>
        </tr>
      </tbody>
    </table>

    <!-- 管网画面：提升泵站状态由台账统一推导，与泵站台账、液位记录保持同步 -->
    <section class="network-board">
      <h3>管网画面 · 提升泵站状态</h3>
      <div v-for="group in networkGroups" :key="String(group['服务管网'])" class="network-group">
        <header class="network-head">
          <strong>{{ group['服务管网'] }}</strong>
          <span>在网泵站 {{ group['泵站数量'] }} 座</span>
        </header>
        <div class="network-pumps">
          <article v-for="pump in group['泵站']" :key="String(pump.id)" class="pump-card">
            <div class="pump-title">
              <span>{{ pump['泵站编号'] }}</span>
              <em :class="['pump-status', statusClass(pump['泵站状态'])]">{{ pump['泵站状态'] ?? '—' }}</em>
            </div>
            <p class="pump-name">{{ pump['泵站名称'] ?? '—' }}</p>
            <p class="pump-meta">液位高度：{{ pump['液位高度'] ?? '—' }} 米 · 格栅：{{ pump['格栅状态'] ?? '—' }}</p>
            <p class="pump-meta">集水池容积：{{ pump['集水池容积'] ?? '—' }} m³</p>
          </article>
        </div>
      </div>
      <p v-if="!networkGroups.length" class="empty-state">暂无可展示的提升泵站</p>
    </section>

    <footer class="page-foot">
      <span>共 {{ total }} 条管网巡查记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type PumpStation = Row & { id: number }
interface NetworkGroup {
  '服务管网': string
  '泵站数量': number
  '泵站': PumpStation[]
}

const ENDPOINT = '/api/pipe'
const columns = ["巡查编号", "巡查路段", "巡查人员", "巡查日期", "管线状况", "井盖状况", "异常描述", "巡查状态"]
const actions = ["开始巡查", "填写记录", "提交处置"]
const statuses = ["待巡查", "巡查中", "已巡查", "需处置"]
const stats = [{"label": "待巡查路段", "value": 0}, {"label": "已巡查路段", "value": 0}, {"label": "需处置路段", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const networkGroups = ref<NetworkGroup[]>([])

function statusClass(status: string | number | null | undefined): string {
  return {
    '正常运行': 'is-normal',
    '高液位': 'is-high',
    '格栅堵塞': 'is-blocked',
    '停机': 'is-stopped',
  }[String(status ?? '')] ?? 'is-normal'
}

async function loadNetwork() {
  // 管网画面直接读提升泵站的统一状态口径，避免两个入口各算各的。
  try {
    const response = await request('/api/lift/network')
    if (response.ok) {
      const payload = await response.json()
      networkGroups.value = payload.groups ?? []
    }
  } catch {
    // 管网画面加载失败不影响巡查列表。
  }
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '管网巡查登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('管网巡查动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '管网巡查操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('管网巡查列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '管网巡查列表读取失败'
  }
}

onMounted(() => {
  void reload()
  void loadNetwork()
})
</script>

<style scoped>
.network-board {
  margin-top: 20px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
}
.network-board h3 {
  margin: 0 0 12px;
  font-size: 14px;
}
.network-group {
  margin-bottom: 14px;
}
.network-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 8px;
}
.network-pumps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.pump-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: #fbfdff;
}
.pump-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.pump-status {
  font-style: normal;
  font-size: 12px;
  border-radius: 999px;
  padding: 2px 10px;
  color: #fff;
}
.pump-status.is-normal { background: #16a34a; }
.pump-status.is-high { background: #d97706; }
.pump-status.is-blocked { background: #dc2626; }
.pump-status.is-stopped { background: #64748b; }
.pump-name {
  margin: 6px 0 4px;
  font-size: 13px;
}
.pump-meta {
  margin: 2px 0;
  font-size: 12px;
  color: var(--muted);
}
</style>
