export type AppTab = 'monitor' | 'lamp' | 'summary' | 'events' | 'history'

export const APP_TABS: { id: AppTab; label: string; desc: string }[] = [
  { id: 'monitor', label: '实时监测', desc: '状态总览' },
  { id: 'lamp', label: '台灯绑定', desc: '米家控制' },
  { id: 'summary', label: '学习摘要', desc: '会话统计' },
  { id: 'events', label: '事件记录', desc: '过程追踪' },
  { id: 'history', label: '历史数据', desc: '趋势分析' },
]
