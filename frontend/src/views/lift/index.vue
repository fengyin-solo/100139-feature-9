<template>
  <section class="page" data-module="lift">
    <header class="page-head">
      <div>
        <h2>提升泵站管理</h2>
        <p class="page-desc">泵站台账与历史液位记录分开保存：液位高度、格栅状态只挂在泵站编号上；泵站状态由最新液位记录统一推导，台账、记录与管网画面保持同步。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openStationCreate">登记提升泵站</button>
        <button class="btn primary" type="button" @click="openRecordCreate()">填报液位记录</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in summary" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}泵站</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'stations' }" type="button" @click="switchTab('stations')">泵站台账</button>
      <button class="tab" :class="{ active: tab === 'records' }" type="button" @click="switchTab('records')">历史液位记录</button>
    </div>

    <!-- 泵站台账 -->
    <template v-if="tab === 'stations'">
      <form class="filter-bar" @submit.prevent="reloadStations">
        <label class="filter-item">
          <span>泵站编号</span>
          <input v-model="stationFilters.keyword" placeholder="按泵站编号检索" />
        </label>
        <label class="filter-item">
          <span>泵站状态</span>
          <select v-model="stationFilters.status">
            <option value="">全部状态</option>
            <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetStationFilters">重置条件</button>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in stationColumns" :key="column">{{ column }}</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in stations" :key="String(row.id)">
            <td v-for="column in stationColumns" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button class="link" type="button" @click="openStationEdit(row)">编辑台账</button>
              <button class="link" type="button" @click="openRecordCreate(row)">填报液位</button>
              <button class="link" type="button" @click="runAction('启动清渣', row)">启动清渣</button>
              <button class="link" type="button" @click="runAction('排水处置', row)">排水处置</button>
              <button class="link" type="button" @click="runAction('停机', row)">停机</button>
            </td>
          </tr>
          <tr v-if="!stations.length">
            <td :colspan="stationColumns.length + 1" class="empty-state">暂无符合条件的提升泵站，可先登记提升泵站</td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot">
        <span>共 {{ stationTotal }} 条泵站台账</span>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </footer>
    </template>

    <!-- 历史液位记录 -->
    <template v-else>
      <form class="filter-bar" @submit.prevent="reloadRecords">
        <label class="filter-item">
          <span>泵站编号</span>
          <input v-model="recordFilters.station" placeholder="按泵站编号检索" list="station-code-list" />
        </label>
        <label class="filter-item">
          <span>泵站状态</span>
          <select v-model="recordFilters.status">
            <option value="">全部状态</option>
            <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetRecordFilters">重置条件</button>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in recordColumns" :key="column">{{ column }}</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in records" :key="String(row.id)">
            <td v-for="column in recordColumns" :key="column">{{ row[column] ?? '—' }}</td>
            <td class="row-actions">
              <button class="link" type="button" @click="openRecordEdit(row)">编辑</button>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td :colspan="recordColumns.length + 1" class="empty-state">暂无历史液位记录，可在台账行点击「填报液位」</td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot">
        <span>共 {{ recordTotal }} 条历史液位记录（只追加、不改写）</span>
        <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
      </footer>
    </template>

    <datalist id="station-code-list">
      <option v-for="option in stationOptions" :key="String(option['泵站编号'])" :value="String(option['泵站编号'])" />
    </datalist>

    <!-- 台账新增/编辑弹窗 -->
    <div v-if="stationModal.open" class="modal-mask" @click.self="closeModals">
      <div class="modal">
        <h3>{{ stationModal.mode === 'create' ? '登记提升泵站' : '编辑泵站台账' }}</h3>
        <label v-for="field in stationFormFields" :key="field" class="modal-field">
          <span>{{ field }}</span>
          <input
            v-model="stationModal.form[field]"
            :disabled="stationModal.mode === 'edit' && field === '泵站编号'"
            :placeholder="`请输入${field}`"
          />
        </label>
        <div class="modal-actions">
          <button class="btn" type="button" @click="closeModals">取消</button>
          <button class="btn primary" type="button" @click="submitStation">保存</button>
        </div>
      </div>
    </div>

    <!-- 液位记录填报/编辑弹窗 -->
    <div v-if="recordModal.open" class="modal-mask" @click.self="closeModals">
      <div class="modal">
        <h3>{{ recordModal.mode === 'create' ? '填报液位记录' : '编辑液位记录' }}</h3>
        <label class="modal-field">
          <span>泵站编号</span>
          <select
            v-model="recordModal.form['泵站编号']"
            :disabled="recordModal.mode === 'edit'"
            @change="onRecordStationChange"
          >
            <option value="" disabled>请选择泵站编号</option>
            <option v-for="option in stationOptions" :key="String(option['泵站编号'])" :value="String(option['泵站编号'])">
              {{ option['泵站编号'] }}（{{ option['泵站名称'] }}）
            </option>
          </select>
        </label>
        <label class="modal-field">
          <span>集水池容积（按泵站编号带出）</span>
          <input :value="recordVolume ?? '—'" disabled />
        </label>
        <label class="modal-field">
          <span>液位高度（米）</span>
          <input v-model="recordModal.form['液位高度']" type="number" step="0.01" min="0" placeholder="请输入液位高度" />
        </label>
        <label class="modal-field">
          <span>格栅状态</span>
          <select v-model="recordModal.form['格栅状态']">
            <option value="" disabled>请选择格栅状态</option>
            <option v-for="g in gridStates" :key="g" :value="g">{{ g }}</option>
          </select>
        </label>
        <label class="modal-field">
          <span>记录时间</span>
          <input v-model="recordModal.form['记录时间']" type="datetime-local" />
        </label>
        <div class="modal-actions">
          <button class="btn" type="button" @click="closeModals">取消</button>
          <button class="btn primary" type="button" @click="submitRecord">保存</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type Form = Record<string, string>

const ENDPOINT = '/api/lift'
const stationColumns = ['泵站编号', '泵站名称', '集水池容积', '扬程', '服务管网', '格栅状态', '液位高度', '泵站状态']
const recordColumns = ['泵站编号', '泵站名称', '记录时间', '液位高度', '格栅状态', '泵站状态']
const stationFormFields = ['泵站编号', '泵站名称', '集水池容积', '扬程', '服务管网']
const statuses = ['正常运行', '高液位', '格栅堵塞', '停机']
const gridStates = ['正常', '堵塞']

const tab = ref<'stations' | 'records'>('stations')
const stations = ref<Row[]>([])
const records = ref<Row[]>([])
const stationTotal = ref(0)
const recordTotal = ref(0)
const summary = ref<{ label: string; value: number }[]>(
  statuses.map((label) => ({ label, value: 0 })),
)
const errorMessage = ref('')
const stationFilters = ref<Record<string, string>>({ keyword: '', status: '' })
const recordFilters = ref<Record<string, string>>({ station: '', status: '' })
const stationOptions = ref<Row[]>([])

const stationModal = reactive<{ open: boolean; mode: 'create' | 'edit'; id: number | null; form: Form }>({
  open: false,
  mode: 'create',
  id: null,
  form: {},
})
const recordModal = reactive<{ open: boolean; mode: 'create' | 'edit'; id: number | null; form: Form }>({
  open: false,
  mode: 'create',
  id: null,
  form: {},
})

const recordVolume = computed(() => {
  const option = stationOptions.value.find((item) => item['泵站编号'] === recordModal.form['泵站编号'])
  return option ? option['集水池容积'] : null
})

function nowLocalInput(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

function switchTab(next: 'stations' | 'records') {
  tab.value = next
  errorMessage.value = ''
  void (next === 'stations' ? reloadStations() : reloadRecords())
}

async function loadOptions() {
  try {
    const response = await request(`${ENDPOINT}/stations/options`)
    if (response.ok) {
      stationOptions.value = await response.json()
    }
  } catch {
    // 下拉拉不到时保留空选项，提交时后端会再校验泵站编号。
  }
}

async function loadSummary() {
  try {
    const response = await request(`${ENDPOINT}/status-summary`)
    if (response.ok) {
      summary.value = await response.json()
    }
  } catch {
    // 统计不阻塞主列表。
  }
}

function resetStationFilters() {
  stationFilters.value = { keyword: '', status: '' }
  void reloadStations()
}

function resetRecordFilters() {
  recordFilters.value = { station: '', status: '' }
  void reloadRecords()
}

async function reloadStations() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (stationFilters.value.keyword) params.set('keyword', stationFilters.value.keyword)
  if (stationFilters.value.status) params.set('status', stationFilters.value.status)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('提升泵站列表读取失败')
    }
    const payload = await response.json()
    stations.value = payload.items ?? []
    stationTotal.value = payload.total ?? stations.value.length
    await loadSummary()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提升泵站列表读取失败'
  }
}

async function reloadRecords() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (recordFilters.value.station) params.set('station', recordFilters.value.station)
  if (recordFilters.value.status) params.set('status', recordFilters.value.status)
  try {
    const response = await request(`${ENDPOINT}/records?${params.toString()}`)
    if (!response.ok) {
      throw new Error('历史液位记录读取失败')
    }
    const payload = await response.json()
    records.value = payload.items ?? []
    recordTotal.value = payload.total ?? records.value.length
    await loadSummary()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '历史液位记录读取失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '提升泵站动作未生效，请稍后重试')
    }
    await reloadStations()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '提升泵站操作失败'
  }
}

// ---------- 台账弹窗 ----------

function openStationCreate() {
  stationModal.open = true
  stationModal.mode = 'create'
  stationModal.id = null
  stationModal.form = Object.fromEntries(stationFormFields.map((field) => [field, '']))
}

function openStationEdit(row: Row) {
  stationModal.open = true
  stationModal.mode = 'edit'
  stationModal.id = Number(row.id)
  stationModal.form = Object.fromEntries(
    stationFormFields.map((field) => [field, String(row[field] ?? '')]),
  )
}

async function submitStation() {
  errorMessage.value = ''
  const isCreate = stationModal.mode === 'create'
  const url = isCreate ? ENDPOINT : `${ENDPOINT}/${stationModal.id}`
  try {
    const response = await request(url, {
      method: isCreate ? 'POST' : 'PUT',
      body: JSON.stringify({ values: { ...stationModal.form } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '泵站台账保存失败')
    }
    closeModals()
    await loadOptions()
    await reloadStations()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '泵站台账保存失败'
  }
}

// ---------- 液位记录弹窗 ----------

function openRecordCreate(row?: Row) {
  recordModal.open = true
  recordModal.mode = 'create'
  recordModal.id = null
  recordModal.form = {
    '泵站编号': row ? String(row['泵站编号'] ?? '') : '',
    '液位高度': '',
    '格栅状态': '',
    '记录时间': nowLocalInput(),
  }
}

function openRecordEdit(row: Row) {
  recordModal.open = true
  recordModal.mode = 'edit'
  recordModal.id = Number(row.id)
  recordModal.form = {
    '泵站编号': String(row['泵站编号'] ?? ''),
    '液位高度': row['液位高度'] == null ? '' : String(row['液位高度']),
    '格栅状态': String(row['格栅状态'] ?? ''),
    '记录时间': String(row['记录时间'] ?? ''),
  }
}

function onRecordStationChange() {
  // 集水池容积通过 computed 随编号联动带出，这里无需额外赋值。
}

async function submitRecord() {
  errorMessage.value = ''
  const isCreate = recordModal.mode === 'create'
  const url = isCreate ? `${ENDPOINT}/records` : `${ENDPOINT}/records/${recordModal.id}`
  try {
    const response = await request(url, {
      method: isCreate ? 'POST' : 'PUT',
      body: JSON.stringify({ values: { ...recordModal.form } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '液位记录保存失败')
    }
    closeModals()
    // 保存后台账与记录两边都刷新，保证状态立刻同步。
    await Promise.all([reloadStations(), reloadRecords()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '液位记录保存失败'
  }
}

function closeModals() {
  stationModal.open = false
  recordModal.open = false
}

onMounted(() => {
  void loadOptions()
  void loadSummary()
  void reloadStations()
})
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}
.tab {
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 6px 6px 0 0;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
}
.tab.active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  width: 420px;
  max-width: calc(100vw - 32px);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.2);
}
.modal h3 {
  margin: 0 0 16px;
  font-size: 15px;
}
.modal-field {
  display: block;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--muted);
}
.modal-field span {
  display: block;
  margin-bottom: 4px;
}
.modal-field input,
.modal-field select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 13px;
  color: #1f2937;
}
.modal-field input:disabled {
  background: #f1f5f9;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
