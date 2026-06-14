# StudyPilot 智能学习台灯

这是一个面向家庭学习场景的智能台灯项目，包含三部分：

- `device/`：ESP32-S3 端 MicroPython 代码，负责传感器采集、摄像头上传和基础控制
- `backend/`：Flask 后端，负责数据接收、状态处理、米家台灯绑定与自动灯控
- `frontend/`：Vue 3 + TypeScript 前端，负责监控面板、台灯绑定和手动控制

## 1. 环境要求

### 后端环境

- Python 3.14
- 依赖：`Flask`、`mijiaAPI==3.2.0`

### 前端环境

- Node.js 18 或更高
- npm

### ESP32 环境

- MicroPython 固件
- ESP32-S3 开发板
- 已连接的 AHT20、BH1750、VL53L0X、摄像头模块
- 与后端处于同一局域网

## 2. 后端安装

先创建并进入 Conda 环境：

```powershell
conda env create -f backend/environment.yml
conda activate studypilot
```

如果环境已存在，可直接安装依赖：

```powershell
conda activate studypilot
python -m pip install -r backend/requirements.txt
```

后端启动：

```powershell
conda activate studypilot
python -m backend.app
```

后端默认运行在：

```text
http://127.0.0.1:5000
```

## 3. 前端安装

进入前端目录安装依赖：

```powershell
cd frontend
npm install
```

开发模式启动：

```powershell
npm run dev
```

生产构建：

```powershell
npm run build
```

构建后可用：

```powershell
npm run preview
```

## 4. ESP32 端配置

1. 复制 `device/secrets.example.json` 为 `device/secrets.json`
2. 填写 Wi-Fi 名称和密码
3. 设置后端 IP 地址
4. 把 `device/` 下需要的脚本上传到 ESP32 文件系统

示例配置：

```json
{
  "device_id": "esp32-study-lamp-01",
  "wifi_ssid": "YOUR_WIFI_NAME",
  "wifi_password": "YOUR_WIFI_PASSWORD",
  "backend_host": "192.168.1.100",
  "backend_port": 5000,
  "device_token": "change-me"
}
```

传感器上报频率默认值：

- 温湿度：30 秒
- 光照：10 秒
- 距离：1 秒
- telemetry 上报：1 秒
- 心跳：5 秒

## 5. 米家台灯绑定

后端使用 `mijiaAPI==3.2.0` 控制米家台灯。

前端进入“台灯绑定”页面后：

1. 点击扫码登录
2. 使用米家 App 扫码
3. 登录成功后获取设备列表
4. 选择台灯并绑定
5. 绑定后即可在前端手动控制亮度和色温

绑定和控制都通过后端完成，前端不直接访问米家云端。

## 6. 后端运行数据

后端会在 `backend/data/` 下保存运行数据，包括：

- SQLite 数据库
- 米家认证文件
- 摄像头快照
- 设备规格缓存


## 7. 常用接口

- `POST /api/device/telemetry`：接收传感器数据
- `POST /api/device/events`：接收设备事件
- `POST /api/device/heartbeat`：接收设备心跳
- `GET /api/device/config`：下发设备运行配置
- `POST /api/lamp/mijia/login/qr`：启动米家扫码登录
- `GET /api/lamp/mijia/devices`：获取米家设备列表
- `POST /api/lamp/binding`：绑定台灯
- `POST /api/lamp/control`：手动控制台灯
- `POST /api/pose/analyze/latest-frame`：后端分析最新摄像头帧

## 8. 本地开发建议

推荐启动顺序：

1. 启动后端
2. 启动前端
3. 配置 ESP32 的 `secrets.json`
4. 让 ESP32 连接 Wi-Fi 并对准后端地址
5. 进入前端完成米家绑定


