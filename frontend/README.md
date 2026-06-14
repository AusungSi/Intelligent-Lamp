# 米家台灯传感器中控台

基于 Vue 3、TypeScript、Vite 搭建的网页端后台展示界面，通过 Flask 后端 API 展示光照、湿度、温度、距离等传感器指标。

## 启动

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

## 后端 JSON 结构

页面通过 `src/api/sensorService.ts` → `dataService.ts` → `client.ts` 轮询后端接口。开发时 `VITE_API_BASE` 留空，走 Vite proxy 到 `http://127.0.0.1:5000`。

```ts
interface SensorDashboardPayload {
  lamp: {
    name: string
    room: string
    online: boolean
    mode: string
    updatedAt: string
  }
  readings: Array<{
    key: 'illumination' | 'humidity' | 'temperature' | 'distance'
    label: string
    value: number
    unit: string
    status: 'low' | 'normal' | 'high'
    trend: string
    description: string
  }>
}
```
