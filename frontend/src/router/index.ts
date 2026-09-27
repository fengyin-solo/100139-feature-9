import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from '@/views/Dashboard.vue'
const Plank = () => import('@/views/plank/index.vue')
const Inflow = () => import('@/views/inflow/index.vue')
const Aeration = () => import('@/views/aeration/index.vue')
const Chemical = () => import('@/views/chemical/index.vue')
const Sediment = () => import('@/views/sediment/index.vue')
const Sludge = () => import('@/views/sludge/index.vue')
const Effluent = () => import('@/views/effluent/index.vue')
const Labtest = () => import('@/views/labtest/index.vue')
const Reagent = () => import('@/views/reagent/index.vue')
const Equip = () => import('@/views/equip/index.vue')
const Pump = () => import('@/views/pump/index.vue')
const Power = () => import('@/views/power/index.vue')
const Pipe = () => import('@/views/pipe/index.vue')
const Lift = () => import('@/views/lift/index.vue')
const LiftLevel = () => import('@/views/lift_level/index.vue')
const Network = () => import('@/views/network/index.vue')
const Meter = () => import('@/views/meter/index.vue')
const Dispatch2 = () => import('@/views/dispatch2/index.vue')
const Storm = () => import('@/views/storm/index.vue')
const Pollutant = () => import('@/views/pollutant/index.vue')
const Material = () => import('@/views/material/index.vue')
const License = () => import('@/views/license/index.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/plank', name: 'plank', component: Plank },
    { path: '/inflow', name: 'inflow', component: Inflow },
    { path: '/aeration', name: 'aeration', component: Aeration },
    { path: '/chemical', name: 'chemical', component: Chemical },
    { path: '/sediment', name: 'sediment', component: Sediment },
    { path: '/sludge', name: 'sludge', component: Sludge },
    { path: '/effluent', name: 'effluent', component: Effluent },
    { path: '/labtest', name: 'labtest', component: Labtest },
    { path: '/reagent', name: 'reagent', component: Reagent },
    { path: '/equip', name: 'equip', component: Equip },
    { path: '/pump', name: 'pump', component: Pump },
    { path: '/power', name: 'power', component: Power },
    { path: '/pipe', name: 'pipe', component: Pipe },
    { path: '/lift', name: 'lift', component: Lift },
    { path: '/lift-level', name: 'lift-level', component: LiftLevel },
    { path: '/network', name: 'network', component: Network },
    { path: '/meter', name: 'meter', component: Meter },
    { path: '/dispatch2', name: 'dispatch2', component: Dispatch2 },
    { path: '/storm', name: 'storm', component: Storm },
    { path: '/pollutant', name: 'pollutant', component: Pollutant },
    { path: '/material', name: 'material', component: Material },
    { path: '/license', name: 'license', component: License },
  ],
})

export default router
