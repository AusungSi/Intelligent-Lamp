# StudyPilot 数据采集、处理与控制规则说明

本文档说明当前系统中设备端数据采集频率、后端接收频率、摄像头图像数据频率，以及后端在什么条件下触发台灯控制、提醒事件和学习摘要。

涉及的主要代码文件：

- `device/sensor_collector.py`
- `device/camera_streamer.py`
- `device/config_loader.py`
- `vision/run_vision_worker.py`
- `backend/routes/device_api.py`
- `backend/routes/pose_api.py`
- `backend/services/telemetry_service.py`
- `backend/services/state_engine.py`
- `backend/services/policy_engine.py`
- `backend/services/lamp_service.py`
- `backend/services/summary_service.py`

## 1. 数据采集与上传频率

### 1.1 设备端传感器采集频率

开发板端在 `device/sensor_collector.py` 中按不同传感器设置独立采样周期：

| 数据类型 | 传感器/来源 | 默认采集周期 | 说明 |
|---|---:|---:|---|
| 温度 | AHT20 | 30 秒 | `INTERVAL_TEMP_HUMID = 30` |
| 湿度 | AHT20 | 30 秒 | 与温度一起读取 |
| 光照 | BH1750 | 10 秒 | `INTERVAL_LIGHT = 10` |
| 距离 | VL53L0X | 1 秒 | `INTERVAL_DISTANCE = 1` |
| 状态机更新 | 开发板本地计算 | 约 0.1 秒检查一次 | 主循环每轮 `sleep_ms(100)`，但传感器按各自周期读取 |

设备端会根据最新传感器值计算：

- `presence_state`：`present`、`away`、`unknown`
- `distance_level`：`too_close`、`normal`、`far`、`unknown`
- `env_label`：`normal`、`too_dark`、`too_hot`、`too_humid`
- `study_state`：`idle`、`studying`、`warning`

### 1.2 设备端向后端上传频率

开发板端上传频率来自 `device/config_loader.py` 默认配置，也可在开发板 `secrets.json` 中覆盖。

| 上传类型 | 接口 | 默认频率 | 配置字段 |
|---|---|---:|---|
| 传感器 telemetry | `POST /api/device/telemetry` | 1 秒一次 | `telemetry_interval_seconds = 1` |
| 心跳 heartbeat | `POST /api/device/heartbeat` | 5 秒一次 | `heartbeat_interval_seconds = 5` |
| 拉取运行配置 | `GET /api/device/config` | 60 秒一次 | `config_refresh_seconds = 60` |
| 状态变化事件 | `POST /api/device/events` | 不固定 | 仅在状态变化时触发 |
| 事件快照 | `POST /api/device/events/<event_id>/snapshot` | 不固定 | 仅指定事件触发且有图像时上传 |

后端本身没有主动轮询开发板，也没有固定接收节拍。后端的“接收频率”由设备端上传频率决定：默认情况下，后端大约每 1 秒接收一次 telemetry，每 5 秒接收一次 heartbeat。

### 1.3 摄像头图像采集和上传频率

系统当前有两种摄像头来源，需要区分。

#### 开发板摄像头模式

开发板摄像头逻辑在 `device/camera_streamer.py` 中。

| 图像用途 | 默认频率 | 配置字段 | 说明 |
|---|---:|---|---|
| 上传到后端 `/api/device/camera/frame` | 300 ms 一帧，约 3.3 FPS | `camera_frame_interval_ms = 300` | 由开发板摄像头采集并上传 |
| 开发板本地网页视频流 `/stream` | 120 ms 一帧，约 8.3 FPS | `local_camera_frame_interval_ms = 120` | 只用于访问开发板本地视频流 |

如果当前使用电脑摄像头进行视觉测试，建议在开发板 `secrets.json` 中设置：

```json
{
  "camera_enabled": false
}
```

这样开发板只上传传感器数据，不再上传摄像头帧，避免占用 ESP32 内存、网络带宽和后端摄像头接口。

#### 电脑摄像头 vision 模式

电脑摄像头视觉模块在 `vision/run_vision_worker.py` 中。

| 数据类型 | 默认频率 | 参数 | 说明 |
|---|---:|---|---|
| 姿态识别结果上传 | 0.5 秒一次，约 2 次/秒 | `--post-interval 0.5` | 上传到 `POST /api/pose/result` |
| 画面帧上传到后端 | 0.2 秒一次，约 5 FPS | `--frame-interval 0.2` | 上传到 `POST /api/device/camera/frame`，供前端显示 |
| 摄像头读取/模型处理 | 尽可能连续执行 | 受摄像头、模型和机器性能影响 | 每轮读取一帧并进行姿态处理 |

前端实时监控页面每 300 ms 刷新一次 `GET /api/camera/latest.jpg`，用于显示最新画面；传感器状态面板每 2 秒请求一次 `GET /api/status/current`。

## 2. 后端接收后的处理流程

### 2.1 telemetry 处理流程

设备上传 telemetry 后，后端执行以下步骤：

1. `backend/routes/device_api.py` 校验 `X-Device-Token`。
2. 检查请求体中是否包含 `device_id`。
3. `telemetry_service.save_telemetry()` 将原始数据写入 `sensor_records`。
4. 根据 telemetry 同步学习会话 `study_sessions`。
5. 读取最近一次姿态识别结果 `pose_records`。
6. `state_engine.derive_state()` 生成后端派生状态。
7. `policy_engine.maybe_execute()` 判断是否需要自动控制台灯。
8. 将派生状态和建议动作写入 `derived_states`。
9. 前端通过 `GET /api/status/current` 读取最新状态。

### 2.2 姿态结果处理流程

电脑视觉模块会把姿态结果上传到：

```http
POST /api/pose/result
```

后端将结果写入 `pose_records`。下一次 telemetry 到达时，后端会读取最近的姿态记录，把传感器数据和视觉结果融合为派生状态。

当前姿态状态主要包括：

| 姿态状态 | 含义 |
|---|---|
| `calibration_normal` | 校准/正常坐姿 |
| `computer_normal` | 正常使用电脑 |
| `computer_abnormal` | 使用电脑姿态异常 |
| `reading_normal` | 正常阅读/写字 |
| `reading_abnormal` | 阅读/写字姿态异常 |
| `absent` | 未检测到人 |
| `ignore` | 忽略或过渡状态 |
| `unknown` | 未知 |
| `low_confidence` | 低置信度 |

## 3. 状态判断规则

### 3.1 距离与在位判断

距离阈值来自后端 `GET /api/device/config` 返回值，也与 `state_engine.py` 默认值一致。

| 条件 | `presence_state` | `distance_level` | 含义 |
|---|---|---|---|
| `distance_mm` 缺失 | `unknown` | `unknown` | 无有效距离 |
| `distance_mm <= 350` | `present` | `too_close` | 用户在位，但距离过近 |
| `350 < distance_mm <= 1200` | `present` | `normal` | 用户在位，距离正常 |
| `distance_mm > 1200` | `away` | `far` | 用户离开或距离过远 |

### 3.2 环境状态判断

| 条件 | 环境标签 |
|---|---|
| `lux < 150` | `too_dark` |
| `temperature > 30` | `too_hot` |
| `humidity > 75` | `too_humid` |
| 没有异常条件 | `normal` |

同一条 telemetry 可以同时具有多个环境标签，例如：

```json
["too_dark", "too_hot"]
```

### 3.3 学习状态判断

设备端和后端都会计算学习状态。当前实现中，如果 telemetry 已经带有 `presence_state`、`distance_level`、`env_label`、`study_state`，后端会优先保留设备端上传值。

后端派生状态的基本规则如下：

| 条件 | `study_state` |
|---|---|
| 用户不在位 | `idle` |
| 用户在位，距离正常，环境正常，姿态正常 | `studying` |
| 用户在位，距离过近 | `warning` |
| 用户在位，环境异常 | `warning` |
| 用户在位，姿态状态异常 | `warning` |

姿态状态只在用户在位时参与 warning 判断。`unknown`、`normal`、`low_confidence` 不会单独触发姿态 warning；其他非正常姿态会触发 warning。

### 3.4 学习会话开始/结束规则

当前学习会话不再由距离传感器判断开始和结束，而是由电脑端 vision 模块输出的 7 类姿态状态判断是否有人。

视觉在位规则如下：

| `pose_state` | 在位判断 |
|---|---|
| `absent` | 无人 |
| `ignore` | 无人 |
| `calibration_normal` | 有人 |
| `computer_normal` | 有人 |
| `computer_abnormal` | 有人 |
| `reading_normal` | 有人 |
| `reading_abnormal` | 有人 |

如果最近一次 pose 结果超过 5 秒未更新，或状态为 `unknown`、`low_confidence`，后端将本次在位状态视为 `unknown`，既不开始学习，也不结束学习，避免因为短暂丢帧或低置信度误判。

学习开始条件：

```text
最近有效 pose_state 判定为有人
且当前没有 active 学习会话
=> 后端创建新的 study_sessions 记录
```

学习结束条件：

```text
最近有效 pose_state 判定为无人
且当前存在 active 学习会话
且距离最近一次“有人”状态已经超过 15 秒
=> 后端关闭学习会话并生成摘要
```

距离传感器数据仍然保留，用于显示距离、判断 `distance_level` 和触发 `distance_too_close` 等提醒，但不再参与学习会话开始/结束判断。

## 4. 台灯自动控制触发条件

自动控制逻辑位于 `backend/services/policy_engine.py`，实际执行台灯控制位于 `backend/services/lamp_service.py`。

### 4.1 自动控制执行前提

后端只有在满足以下条件时，才会真正调用米家 API 控制台灯：

1. 自动策略启用，`lamp_policies.enabled = true`。
2. 已登录米家账号。
3. 已绑定台灯设备。
4. 当前台灯模式允许自动控制，即不是 `manual`、`manual_override` 未过期、`off`。
5. 计算出的目标状态与当前缓存状态不同。
6. 没有被防抖规则拦截。
7. 已识别出台灯支持的可写属性，例如 `power`、`brightness`、`color_temperature`。

### 4.2 默认策略参数

默认策略来自 `lamp_service.DEFAULT_POLICY`：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `manual_override_minutes` | 30 | 手动控制后暂停自动控制 30 分钟 |
| `presence_on` | `true` | 用户在位时允许开灯 |
| `away_dim_seconds` | 60 | 离开 60 秒后调暗 |
| `away_off_seconds` | 180 | 离开 180 秒后关灯 |
| `light_on_lux` | 200 | 低于或等于 200 lux 时按最大自动亮度开灯 |
| `light_off_lux` | 1000 | 高于 1000 lux 时关灯 |
| `too_dark_lux` | 150 | 低于 150 lux 认为偏暗 |
| `normal_lux` | 350 | 正常光照参考值 |
| `min_auto_brightness` | 20 | 自动曲线最低亮度 |
| `max_auto_brightness` | 80 | 自动曲线最高亮度 |
| `too_dark_brightness` | 80 | 偏暗时亮度 |
| `normal_brightness` | 55 | 正常学习亮度 |
| `dim_brightness` | 20 | 离开后的低亮度 |
| `day_study_color_temperature` | 4300 | 学习状态色温 |
| `evening_study_color_temperature` | 3700 | 预留的傍晚学习色温 |
| `rest_color_temperature` | 3000 | 休息/离开色温 |
| `debounce_seconds` | 10 | 相同原因自动命令防抖时间 |

### 4.3 自动控制决策

| 条件 | 后端建议动作 | 原因 |
|---|---|---|
| 用户离开时间 `< 60 秒` | 不控制 | `away_waiting_grace` |
| 用户离开时间 `>= 60 秒` 且 `< 180 秒` | 开灯但调暗，亮度 20，色温 3000 | `away_timeout_dim` |
| 用户离开时间 `>= 180 秒` | 关灯 | `away_timeout_off` |
| 用户在位且 `lux <= 200` | 开灯，亮度 80，色温 4300 | `ambient_dark_full` |
| 用户在位且 `200 < lux <= 1000` | 开灯，亮度随 lux 从 80 线性下降到 20，色温 4300 | `ambient_lux_curve` |
| 用户在位且 `lux > 1000` | 关灯 | `ambient_bright_off` |
| 用户在位但没有有效 lux | 按旧默认策略，正常亮度 55 或偏暗亮度 80 | `present_study_lighting` |
| 在位状态未知 | 不控制 | `presence_unknown` |
| 自动策略关闭 | 不控制 | `policy_disabled` |

说明：

- 当前自动策略主要根据在位状态和光照强度调节台灯；光照越强，自动亮度越低。
- 姿态异常和距离过近会进入 `warning` 状态并记录事件，但当前策略没有直接因为姿态异常或距离过近改变亮度/色温。
- 如果当前台灯状态已经与建议动作一致，后端不会重复发送控制命令。
- 相同原因的自动控制命令在 `debounce_seconds` 内不会重复执行，默认防抖 10 秒。

### 4.4 手动控制优先级

前端手动控制接口：

```http
POST /api/lamp/control
```

手动控制会：

1. 调用米家 API 设置 `power`、`brightness`、`color_temperature`。
2. 写入 `lamp_commands`。
3. 更新 `lamp_states`。
4. 将模式设置为 `manual_override`。
5. 在默认 30 分钟内暂停自动控制。

台灯模式含义如下：

| 模式 | 含义 |
|---|---|
| `auto` | 后端自动策略可以控制台灯 |
| `manual_override` | 手动覆盖期内，自动策略暂停 |
| `manual` | 长期手动模式，自动策略不控制 |
| `off` | 后端不控制台灯 |

## 5. 提醒事件触发条件

提醒事件主要由开发板端状态机触发，并上传到：

```http
POST /api/device/events
```

### 5.1 开发板端事件触发规则

| 事件类型 | 触发条件 | 级别 | 说明 |
|---|---|---|---|
| `study_started` | 从非学习状态进入 `present` | `info` | 旧版设备事件，后端仅记录，不再用于创建学习会话 |
| `presence_present` | `presence_state` 从其他状态变为 `present` | `info` | 检测到用户在位 |
| `presence_away` | `presence_state` 从其他状态变为 `away` | `warning` | 旧版设备离开事件，后端仅记录，不再用于结束学习会话 |
| `distance_too_close` | `distance_level` 变为 `too_close` | `warning` | 距离过近 |
| `environment_changed` | `env_label` 从正常变为异常 | `warning` | 光照、温度或湿度异常 |
| `study_finished` | 学习中离开超过 `leave_grace_seconds`，默认 15 秒 | `info` | 旧版设备事件，后端仅记录，不再用于关闭学习会话 |

事件只在状态变化时触发，不是每秒重复触发。例如用户一直距离过近时，只会在进入 `too_close` 的那次触发 `distance_too_close`。

### 5.2 事件快照规则

默认情况下，以下事件允许上传快照：

```json
["distance_too_close", "presence_away"]
```

是否上传由 `snapshot_enabled` 和 `snapshot_event_types` 控制。当前如果使用电脑摄像头测试，并关闭了开发板摄像头，则开发板事件快照可能没有图像，这是正常现象，不影响传感器 telemetry 和事件本身。

### 5.3 后端事件统计规则

后端接收设备事件后都会写入 `events`，但学习会话的开始和结束不再由设备端事件决定，而是由后端融合 vision 结果后的 `derived_state.presence_state` 决定。

| 事件类型 | 后端统计动作 |
|---|---|
| `study_started` | 仅记录事件，不创建学习会话 |
| `study_finished` | 仅记录事件，不关闭学习会话 |
| `distance_too_close` | 当前会话 `warning_count + 1` |
| `environment_changed` | 当前会话 `warning_count + 1` |
| `presence_away` | 仅记录事件，不增加离开次数 |

新版后端会在 `derived_state.presence_state` 从 `present` 变为 `away` 时，将当前会话的 `leave_count + 1`。如果持续无人达到 15 秒，则关闭当前学习会话并生成摘要。

## 6. 学习摘要生成条件

学习摘要由 `backend/services/summary_service.py` 生成，并写入 `study_sessions.summary_text`。

触发条件：

- 最近有效 vision 结果为 `absent` 或 `ignore`，后端将 `derived_state.presence_state` 判定为 `away`。
- 当前存在活跃学习会话。
- 距离最近一次 vision 判定为“有人”已经超过 15 秒。

如果 vision 结果超过 5 秒未更新，或状态为 `unknown`、`low_confidence`，后端会将本次在位状态视为 `unknown`，不会开始学习，也不会结束学习，避免短暂丢帧导致误关会话。

摘要内容包括：

- 本次学习开始时间
- 本次学习结束时间
- 累计学习时长
- 离开次数 `leave_count`
- 异常提醒次数 `warning_count`

## 7. 当前推荐测试配置

如果当前使用电脑摄像头进行视觉识别，推荐让开发板只负责传感器：

```json
{
  "backend_host": "192.168.5.7",
  "backend_port": 5000,
  "device_token": "change-me",
  "telemetry_interval_seconds": 1,
  "heartbeat_interval_seconds": 5,
  "config_refresh_seconds": 60,
  "camera_enabled": false
}
```

此时数据链路为：

```text
开发板传感器
  -> 每 1 秒上传 telemetry
  -> 后端保存 sensor_records
  -> 后端融合最近一次电脑 vision 姿态结果
  -> 后端生成 derived_state
  -> 后端判断是否自动控制台灯
  -> 前端每 2 秒读取状态并显示

电脑摄像头 vision
  -> 每 0.5 秒上传姿态识别结果
  -> 每 0.2 秒上传画面帧
  -> 前端显示最新视频流和姿态判断结果
```

## 8. 简要结论

默认情况下，设备端距离数据每 1 秒采集一次，光照每 10 秒采集一次，温湿度每 30 秒采集一次；设备端 telemetry 每 1 秒上传一次，后端就按这个节奏接收和处理数据。

开发板摄像头默认约每 300 ms 上传一帧；电脑 vision 模式下默认每 0.2 秒上传一帧画面，每 0.5 秒上传一次姿态判断结果。

台灯自动控制主要由 vision 判定的“是否有人”和光照强度触发；提醒事件主要由距离过近、环境异常等状态变化触发；学习摘要在 vision 判定无人持续 15 秒并结束学习会话时生成。
