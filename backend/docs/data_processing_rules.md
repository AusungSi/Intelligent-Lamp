# 后端数据处理逻辑规则说明

本文档说明当前后端在接收到 ESP32 采集数据后的处理流程，覆盖传感器数据入库、派生状态计算、学习会话同步、后端姿态检测、自动灯控策略、手动灯控覆盖以及前端读取接口。

涉及的主要代码文件：

- `backend/routes/device_api.py`
- `backend/routes/lamp_api.py`
- `backend/routes/pose_api.py`
- `backend/services/telemetry_service.py`
- `backend/services/state_engine.py`
- `backend/services/policy_engine.py`
- `backend/services/lamp_service.py`
- `backend/services/pose_service.py`

## 1. 数据入口

### 1.1 传感器数据上报

接口：

```http
POST /api/device/telemetry
```

必需请求头：

```http
X-Device-Token: <后端配置的设备令牌>
```

主要请求体字段：

```json
{
  "device_id": "esp32-study-lamp-01",
  "timestamp": 1710000000,
  "temperature": 26.5,
  "humidity": 58.0,
  "lux": 120,
  "distance_mm": 500,
  "presence_state": "present",
  "distance_level": "normal",
  "env_label": ["too_dark"],
  "study_state": "studying",
  "study_duration": 300,
  "session_started_at": 1710000000
}
```

处理顺序：

1. 校验 `device_id` 是否存在。
2. 将原始传感器数据写入 `sensor_records`。
3. 根据 telemetry 同步学习会话状态。
4. 读取最近一次后端姿态检测结果。
5. 将传感器数据和姿态结果融合为后端派生状态。
6. 根据派生状态评估自动灯控策略。
7. 如果已绑定台灯且允许自动控制，则调用米家接口执行灯控。
8. 将派生状态和建议灯控动作写入 `derived_states`。
9. 将派生状态和灯控执行结果返回给设备端。

### 1.2 设备事件上报

接口：

```http
POST /api/device/events
```

设备事件会写入 `events` 表，同时可能影响当前学习会话。

当前事件处理规则：

| 事件类型 | 后端处理 |
|---|---|
| `study_started` | 如果没有活跃会话，则创建新的学习会话 |
| `study_finished` | 关闭当前活跃学习会话并生成摘要 |
| `distance_too_close` | 当前学习会话的 `warning_count` 加 1 |
| `environment_changed` | 当前学习会话的 `warning_count` 加 1 |
| `presence_away` | 当前学习会话的 `leave_count` 加 1 |

### 1.3 设备心跳

接口：

```http
POST /api/device/heartbeat
```

心跳数据写入 `heartbeats` 表。前端会根据最近心跳时间判断设备是否在线。

### 1.4 设备运行配置

接口：

```http
GET /api/device/config
```

该接口向 ESP32 返回当前传感器阈值和后端能力开关。

返回示例：

```json
{
  "settings": {
    "distance_warning_mm": 350,
    "distance_presence_mm": 1200,
    "light_low_lux": 150,
    "temperature_high_c": 30,
    "humidity_high_percent": 75,
    "leave_grace_seconds": 15,
    "snapshot_enabled": true,
    "snapshot_event_types": ["distance_too_close", "presence_away"]
  },
  "features": {
    "backend_lamp_control": true,
    "backend_pose_detection": true
  }
}
```

说明：

- ESP32 仍负责采集和上报数据。
- 台灯控制由后端通过米家账号和 `mijiaAPI` 执行。
- 姿态检测只在后端处理，不由 ESP32 上传姿态结果。

## 2. 原始数据存储规则

每次收到 telemetry 后，后端都会先将原始数据写入 `sensor_records`。

保存字段包括：

- `device_id`
- `timestamp`
- `temperature`
- `humidity`
- `lux`
- `distance_mm`
- 各传感器独立采样时间戳
- `presence_state`
- `distance_level`
- `env_label`
- `study_state`
- `study_duration`
- `session_started_at`

该表是历史曲线、状态回放和原始数据排查的基础。

## 3. 派生状态计算规则

派生状态由 `state_engine.derive_state()` 生成。

派生状态的目的，是把传感器原始值转换成后端统一理解的状态，例如：

- 是否有人在桌前
- 人体距离是否过近
- 环境是否异常
- 当前是否处于学习状态
- 是否存在姿态风险

### 3.1 距离状态规则

输入字段：`distance_mm`

| 条件 | `presence_state` | `distance_level` |
|---|---|---|
| `distance_mm` 缺失 | `unknown` | `unknown` |
| `distance_mm <= 350` | `present` | `too_close` |
| `distance_mm <= 1200` | `present` | `normal` |
| `distance_mm > 1200` | `away` | `far` |

含义：

- `present`：检测到用户在桌前。
- `away`：用户离开或距离过远。
- `too_close`：距离过近，需要提醒。
- `normal`：距离处于正常范围。
- `far`：距离较远或离桌。

### 3.2 环境状态规则

输入字段：`lux`、`temperature`、`humidity`

| 条件 | 环境标签 |
|---|---|
| `lux < 150` | `too_dark` |
| `temperature > 30` | `too_hot` |
| `humidity > 75` | `too_humid` |
| 没有异常条件 | `normal` |

同一条数据可以同时具有多个环境标签，例如：

```json
["too_dark", "too_hot"]
```

### 3.3 学习状态规则

后端会综合在位状态、距离状态、环境标签和姿态状态计算学习状态。

规则：

| 条件 | `study_state` |
|---|---|
| 用户不在位 | `idle` |
| 用户在位，且无异常 | `studying` |
| 用户在位，且距离过近 | `warning` |
| 用户在位，且环境异常 | `warning` |
| 用户在位，且姿态异常 | `warning` |

说明：

- 如果 telemetry 中已经包含 `presence_state`、`distance_level`、`env_label` 或 `study_state`，当前实现会优先保留设备端上传的值。
- 后端派生状态仍会写入 `derived_states`，用于后续分析和灯控策略判断。

## 4. 学习会话同步规则

学习会话由 `study_sessions` 表记录。

### 4.1 根据 telemetry 同步

规则：

1. 如果 telemetry 中存在 `session_started_at`，且当前设备没有活跃会话，则创建新的学习会话。
2. 如果当前存在活跃会话，并且 telemetry 同时满足以下条件：
   - `study_state == idle`
   - `study_duration == 0`
   - `presence_state == away`

   则关闭当前活跃学习会话。

### 4.2 根据事件同步

规则：

| 事件类型 | 会话处理 |
|---|---|
| `study_started` | 如果没有活跃会话，则创建会话 |
| `study_finished` | 关闭当前活跃会话 |
| `distance_too_close` | 当前会话 warning 次数加 1 |
| `environment_changed` | 当前会话 warning 次数加 1 |
| `presence_away` | 当前会话 leave 次数加 1 |

会话关闭时，后端会生成学习摘要并写入 `summary_text`。

## 5. 后端姿态检测规则

当前设计中，姿态检测只在后端执行。

接口：

```http
POST /api/pose/analyze/latest-frame
```

当前行为：

1. 从 `camera_store` 读取最近一帧摄像头画面。
2. 如果没有摄像头帧，则保存一条姿态记录：

```json
{
  "pose_state": "unknown",
  "confidence": 0,
  "risk_labels": ["no_frame"]
}
```

3. 如果有摄像头帧，但尚未接入真实姿态算法，则保存：

```json
{
  "pose_state": "low_confidence",
  "confidence": 0,
  "risk_labels": ["pose_detector_not_configured"]
}
```

真实姿态算法的接入点：

```text
backend/services/pose_service.py
analyze_latest_frame()
```

后续接入模型时，应将算法输出规范化为：

```json
{
  "device_id": "esp32-study-lamp-01",
  "timestamp": 1710000000,
  "provider": "backend_latest_frame",
  "pose_state": "normal",
  "confidence": 0.92,
  "keypoints": [
    { "name": "nose", "x": 0.5, "y": 0.2, "score": 0.9 }
  ],
  "risk_labels": []
}
```

支持的姿态状态：

| 状态 | 含义 |
|---|---|
| `unknown` | 未知 |
| `normal` | 姿态正常 |
| `head_down` | 低头明显 |
| `leaning_left` | 身体左倾 |
| `leaning_right` | 身体右倾 |
| `too_close` | 人体或头部距离过近 |
| `absent` | 未检测到有效人体 |
| `multi_person` | 检测到多人 |
| `low_confidence` | 置信度不足 |

说明：

- 姿态结果写入 `pose_records`。
- 当前后端只保存结构化姿态结果，不长期保存连续视频。
- 最新姿态结果会参与下一次 telemetry 的派生状态计算。

## 6. 自动灯控策略

自动灯控由 `policy_engine.maybe_execute()` 负责。

后端只有在满足以下条件时才会真正调用米家接口控制台灯：

1. 米家账号已登录。
2. 已绑定台灯。
3. 当前台灯模式允许自动控制。
4. 当前不在手动覆盖期内。
5. 计算出的目标灯光状态与缓存状态不同。
6. 没有触发防抖限制。

### 6.1 默认策略参数

默认策略存储在 `lamp_policies` 表中，名称为 `default`。

默认配置：

```json
{
  "manual_override_minutes": 30,
  "presence_on": true,
  "away_dim_seconds": 60,
  "away_off_seconds": 180,
  "too_dark_lux": 150,
  "normal_lux": 350,
  "too_dark_brightness": 80,
  "normal_brightness": 55,
  "dim_brightness": 20,
  "day_study_color_temperature": 4300,
  "evening_study_color_temperature": 3700,
  "rest_color_temperature": 3000,
  "debounce_seconds": 10
}
```

### 6.2 自动控制决策

| 条件 | 后端动作 |
|---|---|
| 未绑定台灯 | 不执行控制，只记录建议动作 |
| 当前模式为 `manual` | 不执行自动控制 |
| 当前模式为 `manual_override` 且未过期 | 不执行自动控制 |
| 当前模式为 `off` | 不执行自动控制 |
| 用户离开超过 `away_off_seconds` | 关灯 |
| 用户离开超过 `away_dim_seconds` | 降低亮度 |
| 用户在位且环境偏暗 | 开灯，亮度设为 `too_dark_brightness` |
| 用户在位且环境正常 | 开灯，亮度设为 `normal_brightness` |
| 在位状态未知 | 不执行控制 |

### 6.3 防抖规则

自动控制命令会写入 `lamp_commands`。

在发送新的自动命令前，后端会检查最近一次同原因的成功自动命令。

如果距离上次成功执行时间小于 `debounce_seconds`，则跳过本次控制，跳过原因记录为：

```text
debounced
```

这样可以避免 ESP32 每秒上传 telemetry 时，后端频繁调用米家云端接口。

## 7. 手动灯控规则

接口：

```http
POST /api/lamp/control
```

请求示例：

```json
{
  "power": true,
  "brightness": 80,
  "color_temperature": 4200,
  "override_minutes": 30
}
```

处理规则：

1. 后端将请求转换为米家设备属性设置。
2. 通过 `mijiaAPI.set_devices_prop()` 控制台灯。
3. 将命令写入 `lamp_commands`，`requested_by = manual`。
4. 更新 `lamp_states`。
5. 将台灯模式设置为 `manual_override`。
6. 在 `override_minutes` 时间内暂停自动灯控策略。

默认手动覆盖时间为 30 分钟。

### 7.1 台灯控制模式

| 模式 | 含义 |
|---|---|
| `auto` | 后端自动策略可以控制台灯 |
| `manual_override` | 手动覆盖中，自动策略暂时不控制 |
| `manual` | 长期手动模式，自动策略不控制 |
| `off` | 后端不控制台灯 |

模式切换接口：

```http
POST /api/lamp/mode
```

请求示例：

```json
{
  "mode": "auto"
}
```

## 8. 米家账号登录与台灯绑定规则

后端使用：

```text
mijiaAPI==3.2.0
```

### 8.1 登录流程

1. 前端调用：

```http
POST /api/lamp/mijia/login/qr
```

2. 后端启动二维码登录线程，并捕获米家登录 URL。
3. 前端展示二维码：

```http
GET /api/lamp/mijia/login/qr/<session_id>/image
```

4. 前端轮询登录状态：

```http
GET /api/lamp/mijia/login/qr/<session_id>/status
```

5. 登录成功后，认证信息保存到后端数据目录。

### 8.2 设备列表

接口：

```http
GET /api/lamp/mijia/devices
```

后端通过米家 API 获取设备列表，并根据设备名称和 model 判断是否像灯具设备。

### 8.3 台灯绑定

接口：

```http
POST /api/lamp/binding
```

请求示例：

```json
{
  "did": "123456789",
  "model": "yeelink.light.lamp4",
  "name": "书桌台灯"
}
```

绑定时，后端会：

1. 停用旧绑定。
2. 保存新的台灯绑定到 `lamp_bindings`。
3. 根据设备 model 查询 MIoT 规格。
4. 尝试识别以下能力：
   - `power`
   - `brightness`
   - `color_temperature`
5. 将能力映射保存为 `capability_json`。

如果某个能力无法识别，对应字段的控制命令会被跳过。

## 9. 关键数据库表

| 表名 | 作用 |
|---|---|
| `sensor_records` | 原始传感器历史数据 |
| `events` | 设备事件和告警事件 |
| `heartbeats` | 设备在线心跳 |
| `study_sessions` | 学习会话、时长和摘要 |
| `derived_states` | 后端融合后的派生状态 |
| `pose_records` | 后端姿态检测结果 |
| `mijia_accounts` | 米家登录账号元信息 |
| `lamp_bindings` | 当前绑定台灯 |
| `lamp_states` | 台灯缓存状态和控制模式 |
| `lamp_commands` | 手动和自动灯控命令日志 |
| `lamp_policies` | 灯控策略和姿态配置 |

## 10. 前端读取接口

前端主要读取以下接口：

| 接口 | 用途 |
|---|---|
| `GET /api/status/current` | 当前 telemetry、heartbeat、最新事件和派生状态 |
| `GET /api/status/history` | 传感器历史数据 |
| `GET /api/status/events` | 事件时间线 |
| `GET /api/lamp/state` | 当前台灯绑定和灯状态 |
| `GET /api/lamp/commands` | 最近灯控命令日志 |
| `GET /api/lamp/policy` | 自动灯控策略 |
| `GET /api/pose/latest` | 最近一次姿态检测结果 |
| `GET /api/pose/history` | 姿态检测历史 |

前端不直接访问米家云端。米家扫码登录、设备列表、设备绑定和灯光控制全部通过后端接口完成。

## 11. 当前处理链路总结

当前后端完整数据处理链路如下：

```text
ESP32 上传 telemetry
  -> 后端校验 token 和 device_id
  -> 写入 sensor_records
  -> 同步 study_sessions
  -> 读取最近 pose_records
  -> 生成 derived_state
  -> 评估 policy_engine
  -> 如允许则调用 mijiaAPI 控制台灯
  -> 写入 lamp_commands / lamp_states
  -> 写入 derived_states
  -> 前端通过 status/lamp/pose 接口展示
```

核心原则：

- 原始数据先入库，保证历史可追溯。
- 状态判断集中在后端，便于统一调整规则。
- 台灯控制只在后端执行，前端和 ESP32 不直接调用米家。
- 手动控制优先级高于自动策略。
- 姿态检测只在后端运行，设备端不上传姿态结构化结果。
- 自动灯控带防抖，避免频繁调用米家云端。
