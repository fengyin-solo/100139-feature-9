<template>
  <section class="page" data-module="lift">
    <header class="page-head">
      <div>
        <h2>提升泵站管理</h2>
        <p class="page-desc">维护提升泵站台账：液位高度、格栅状态只挂在泵站编号上，保存后立即落盘，再次打开仍是改过的内容。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记提升泵站</button>
        <button class="btn" type="button" @click="exportRows">导出提升泵站清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>泵站编号</span>
        <input v-model="filters.keyword" placeholder="按泵站编号检索" />
      </label>
      <label class="filter-item">
        <span>泵站状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">
            <span v-if="column === '泵站状态'" class="status-tag" :class="`status-${row[column]}`">{{ row[column] ?? '—' }}</span>
            <span v-else>{{ row[column] ?? '—' }}</span>
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="openEdit(row)">编辑保存</button>
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
          <td :colspan="columns.length + 1" class="empty-state">暂无提升泵站数据，可先登记提升泵站</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条提升泵站记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      <span v-else-if="successMessage" class="success-text">{{ successMessage }}</span>
    </footer>

    <!-- 登记 / 编辑共用弹窗 -->
    <div v-if="dialogOpen" class="modal-mask" @click.self="closeDialog">
      <div class="modal-card">
        <h3 class="modal-title">{{ editingId === null ? '登记提升泵站' : '编辑提升泵站' }}</h3>
        <p class="modal-sub">泵站编号是液位记录与管网画面的关联键；保存后状态按格栅、液位自动推导。</p>
        <form @submit.prevent="submitDialog">
          <div class="form-grid">
            <label v-for="field in formFields" :key="field" class="form-field" :class="{ full: field === '服务管网' }">
              <span>{{ field }}</span>
              <input
                v-model="form[field]"
                :readonly="editingId !== null && field === '泵站编号'"
                :placeholder="`请输入${field}`"
              />
            </label>
          </div>
          <div class="modal-actions">
            <button class="btn ghost" type="button" @click="closeDialog">取消</button>
            <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/lift'
const columns = ["泵站编号", "泵站名称", "集水池容积", "扬程", "服务管网", "格栅状态", "液位高度", "泵站状态"]
const actions = ["启动清渣", "排水处置", "停机"]
const statuses = ["正常运行", "高液位", "格栅堵塞", "停机"]
const formFields = ["泵站编号", "泵站名称", "集水池容积", "扬程", "服务管网", "格栅状态", "液位高度"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const filters = reactive<{ keyword: string; status: string }>({ keyword: '', status: '' })

const dialogOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Record<string, string>>({})

const stats = computed(() => {
  const count = (state: string) => rows.value.filter((row) => row['泵站状态'] === state).length
  return [
    { label: '正常运行泵站', value: count('正常运行') },
    { label: '高液位泵站', value: count('高液位') },
    { label: '格栅堵塞泵站', value: count('格栅堵塞') },
    { label: '停机泵站', value: count('停机') },
  ]
})

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  editingId.value = null
  formFields.forEach((field) => { form[field] = '' })
  dialogOpen.value = true
  errorMessage.value = ''
}

function openEdit(row: Row) {
  editingId.value = Number(row.id)
  formFields.forEach((field) => {
    form[field] = row[field] === null || row[field] === undefined ? '' : String(row[field])
  })
  dialogOpen.value = true
  errorMessage.value = ''
}

function closeDialog() {
  dialogOpen.value = false
}

async function submitDialog() {
  errorMessage.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    const url = editingId.value === null ? ENDPOINT : `${ENDPOINT}/${editingId.value}`
    const method = editingId.value === null ? 'POST' : 'PUT'
    const response = await request(url, { method, body: JSON.stringify({ values: { ...form } }) })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '保存未生效，请稍后重试')
    }
    successMessage.value = payload.message || '已保存'
    dialogOpen.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提升泵站保存失败'
  } finally {
    saving.value = false
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '提升泵站动作未生效，请稍后重试')
    }
    successMessage.value = payload.message
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提升泵站操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.status) params.set('status', filters.status)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('提升泵站列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提升泵站列表读取失败'
  }
}

onMounted(reload)
</script>
