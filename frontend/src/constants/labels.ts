export const STUDY_STATE_LABEL: Record<string, string> = {
  studying: '学习中',
  warning: '异常提醒',
  idle: '待机',
}

export const EVENT_TYPE_LABEL: Record<string, string> = {
  study_started: '开始学习',
  study_finished: '结束学习',
  presence_away: '离桌检测',
  distance_too_close: '坐姿异常',
  environment_changed: '环境异常',
}
