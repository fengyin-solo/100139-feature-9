<template>
  <section class="page" data-module="lift-level">
    <header class="page-head">
      <div>
        <h2>提升泵站液位记录</h2>
        <p class="page-desc">按泵站编号登记液位高度与格栅状态，集水池容积由台账自动带出；每条记录只追加保存，历史记录不会被新记录覆盖。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记液位记录</button>
        <button class="btn" type="button" @click="exportRows">导出液位记录</button>
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
        <input v-model="filters.station_code" placeholder="按泵站编号检索" />
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
            <button class="link" type="button" @click="openEdit(row)">修正此条</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无液位记录，可先按泵站编号登记一条</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条历史液位记录（按监测时间倒序，旧记录保留不覆盖）</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      <span v-else-if="successMessage" class="success-text">{{ successMessage }}</span>
    </footer>

    <div v-if="dialogOpen" class="modal-mask" @click.self="closeDialog">
      <div class="modal-card">
        <h3 class="modal-title">{{ editingId === null ? '登记液位记录' : '修正液位记录' }}</h3>
        <p class="modal-sub">液位高度与格栅状态只挂在填写的泵站编号上；集水池容积按编号从台账带出。</p>
        <form @submit.prevent="submitDialog">
          <div class="form-grid">
            <label class="form-field">
              <span>泵站编号</span>
              <input
                v-model="form['泵站编号']"
                :readonly="editingId !== null"
                placeholder="如 LIFT-0001"
                @blur="prefillStation"
              />
            </label>
            <label class="form-field">
              <span>监测时间</span>
              <input v-model="form['监测时间']" placeholder="留空取当前时间" />
            </label>
            <label class="form-field">
              <span>泵站名称</span>
              <input v-model="form['泵站名称']" readonly />
            </label>
            <label class="form-field">
              <span>集水池容积（m³，台账带出）</span>
              <input v-model="form['集水池容积']" readonly />
            </label>
            <label class="form-field">
              <span>液位高度（m）</span>
              <input v-model="form['液位高度']" placeholder="如 3.2" />
            </label>
            <label class="form-field">
              <span>格栅状态</span>
              <select v-model="form['格栅状态']">
                <option value="" disabled>请选择</option>
                <option value="通畅">通畅</option>
                <option value="堵塞">堵塞</option>
              </select>
            </label>
            <label class="form-field full">
              <span>备注</span>
              <input v-model="form['备注']" placeholder="可选" />
            </label>
          </div>
          <div class="modal-actions">
            <button class="btn ghost" type="button" @click="closeDialog">取消</button>
            <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存记录' }}</button>
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

const ENDPOINT = '/api/lift-level'
const columns = ["泵站编号", "泵站名称", "集水池容积", "监测时间", "格栅状态", "液位高度", "泵站状态"]
const statuses = ["正常运行", "高液位", "格栅堵塞", "停机"]
const formFields = ["泵站编号", "监测时间", "泵站名称", "集水池容积", "液位高度", "格栅状态", "备注"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
const filters = reactive<{ station_code: string; status: string }>({ station_code: '', status: '' })

const dialogOpen = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<Record<string, string>>({})

const stats = computed(() => {
  const count = (state: string) => rows.value.filter((row) => row['泵站状态'] === state).length
  return [
    { label: '正常运行', value: count('正常运行') },
    { label: '高液位', value: count('高液位') },
    { label: '格栅堵塞', value: count('格栅堵塞') },
    { label: '历史记录总数', value: total.value },
  ]
})

function resetFilters() {
  filters.station_code = ''
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

async function prefillStation() {
  const code = form['泵站编号']?.trim()
  if (!code || editingId.value !== null) {
    return
  }
  try {
    const response = await request(`${ENDPOINT}/stations/${encodeURIComponent(code)}`)
    if (!response.ok) {
      form['泵站名称'] = ''
      form['集水池容积'] = ''
      return
    }
    const station = await response.json()
    form['泵站名称'] = station['泵站名称'] ?? ''
    form['集水池容积'] = station['集水池容积'] ?? ''
  } catch {
    // 编号没找到时保存动作会给出明确提示，这里不打断填写。
  }
}

async function submitDialog() {
  errorMessage.value = ''
  successMessage.value = ''
  saving.value = true
  try {
    const values: Record<string, string> = { ...form }
    const url = editingId.value === null ? ENDPOINT : `${ENDPOINT}/${editingId.value}`
    const method = editingId.value === null ? 'POST' : 'PUT'
    const response = await request(url, { method, body: JSON.stringify({ values }) })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '保存未生效，请稍后重试')
    }
    successMessage.value = payload.message || '液位记录已保存'
    dialogOpen.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '液位记录保存失败'
  } finally {
    saving.value = false
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (filters.station_code) params.set('station_code', filters.station_code)
  if (filters.status) params.set('status', filters.status)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('液位记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '液位记录列表读取失败'
  }
}

onMounted(reload)
</script>
