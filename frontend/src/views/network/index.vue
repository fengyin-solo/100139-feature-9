<template>
  <section class="page" data-module="network">
    <header class="page-head">
      <div>
        <h2>管网画面</h2>
        <p class="page-desc">按服务管网汇总提升泵站，液位、格栅与泵站状态实时读取泵站台账，与台账、液位记录始终同源同步。</p>
      </div>
    </header>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">在网泵站</span>
        <strong class="stat-value">{{ overview.total ?? 0 }}</strong>
      </article>
      <article v-for="(count, state) in overview.status_count ?? {}" :key="state" class="stat-card">
        <span class="stat-label">{{ state }}</span>
        <strong class="stat-value">{{ count }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>服务管网 / 泵站编号</span>
        <input v-model="keyword" placeholder="按管网或泵站编号检索" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetKeyword">重置条件</button>
      <button class="btn ghost" type="button" @click="reload">刷新画面</button>
    </form>

    <div v-for="net in overview.networks ?? []" :key="net['服务管网']" style="margin-bottom: 16px;">
      <h3 style="font-size: 14px; margin: 8px 0;">
        {{ net['服务管网'] }}
        <span style="color: var(--muted); font-weight: normal; font-size: 12px;">（{{ net['泵站数量'] }} 座泵站）</span>
      </h3>
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="column in stationColumns" :key="column">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="station in net['泵站']" :key="String(station['泵站编号'])">
            <td v-for="column in stationColumns" :key="column">
              <span v-if="column === '泵站状态'" class="status-tag" :class="`status-${station[column]}`">{{ station[column] ?? '—' }}</span>
              <span v-else>{{ station[column] ?? '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!(overview.networks ?? []).length" class="data-table empty-state" style="padding: 24px;">
      暂无可展示的管网泵站
    </div>

    <footer class="page-foot">
      <span>画面数据来自提升泵站台账，台账或液位记录保存后刷新即可看到最新状态</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Station = Record<string, string | number | null>
type NetworkGroup = { 服务管网: string; 泵站数量: number; 泵站: Station[] }
type Overview = {
  total: number
  status_count: Record<string, number>
  networks: NetworkGroup[]
}

const stationColumns = ["泵站编号", "泵站名称", "服务管网", "集水池容积", "液位高度", "格栅状态", "泵站状态"]

const overview = ref<Partial<Overview>>({})
const keyword = ref('')
const errorMessage = ref('')

function resetKeyword() {
  keyword.value = ''
  void reload()
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (keyword.value) params.set('keyword', keyword.value)
  try {
    const response = await request(`/api/network?${params.toString()}`)
    if (!response.ok) {
      throw new Error('管网画面读取失败')
    }
    overview.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '管网画面读取失败'
  }
}

onMounted(reload)
</script>
