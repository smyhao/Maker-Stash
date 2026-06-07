<script setup lang="ts">
import { useRouter } from 'vue-router'
import { AlertTriangle, Boxes, ChevronRight, ScrollText, Settings, Wrench } from 'lucide-vue-next'

const router = useRouter()
const destinations = [
  { name: 'categories', title: '分类管理', copy: '维护分类树与编号前缀规则', icon: Boxes, action: '进入分类管理' },
  { name: 'backups', title: '备份中心', copy: '创建、下载和恢复数据备份', icon: ScrollText, action: '进入备份中心' },
  { name: 'settings', title: 'Token 管理', copy: '配置 API 连接并管理访问令牌', icon: Settings, action: '进入 Token 管理' },
  { name: 'extension-settings', title: '扩展管理', copy: '启用、禁用和配置已安装扩展', icon: Wrench, action: '进入扩展管理' },
]
</script>

<template>
  <section class="p-5 2xl:p-7">
    <h2 class="text-[26px] font-semibold tracking-tight">管理</h2>
    <p class="mt-1 text-[14px] text-muted">管理分类结构、数据安全与连接设置。</p>
    <div class="mt-7 grid gap-4 xl:grid-cols-4">
      <button v-for="item in destinations" :key="item.name" class="rounded-2xl border border-line bg-white p-5 text-left shadow-sm transition hover:border-green/35 hover:shadow-soft" @click="router.push({ name: item.name })">
        <component :is="item.icon" :size="23" class="text-green" />
        <h3 class="mt-5 text-[18px] font-semibold">{{ item.title }}</h3>
        <p class="mt-2 min-h-[42px] text-[14px] leading-6 text-muted">{{ item.copy }}</p>
        <span class="mt-5 inline-flex items-center gap-2 text-[14px] font-medium text-green">{{ item.action }} <ChevronRight :size="16" /></span>
      </button>
    </div>
    <div class="mt-6 max-w-[760px] rounded-2xl border border-clay/20 bg-clay/5 p-5">
      <h3 class="inline-flex items-center gap-2 text-[16px] font-semibold"><AlertTriangle :size="18" class="text-clay" />安全提醒</h3>
      <div class="mt-4 grid gap-3 text-[14px] text-ink/75 sm:grid-cols-2">
        <p class="rounded-xl bg-white/80 p-3">恢复备份前会自动创建当前快照，但恢复仍会覆盖当前状态。</p>
        <p class="rounded-xl bg-white/80 p-3">新建 Token 仅显示一次，请在创建后妥善保存。</p>
      </div>
    </div>
  </section>
</template>
