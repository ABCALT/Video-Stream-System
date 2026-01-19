# API 文档

## 视频流传输 API

### 1. 监控流选择与预览
- **GET** `/api/video_stream/preview/{device_id}`
- 功能：获取指定设备的视频流预览

### 2. 多设备监控预览
- **GET** `/api/video_stream/multi_preview`
- 功能：获取多个设备的视频流预览

### 3. 视频导出
- **POST** `/api/video_stream/export`
- 功能：导出指定时间段的视频

### 4. 历史视频存储/回放
- **GET** `/api/video_stream/history`
- 功能：获取历史视频列表
- **GET** `/api/video_stream/history/{video_id}/playback`
- 功能：回放历史视频

## 设备管理 API

### 1. 监控设备状态
- **GET** `/api/device/status`
- 功能：获取所有设备状态
- **GET** `/api/device/status/{device_id}`
- 功能：获取指定设备状态

### 2. 设备分布地域图
- **GET** `/api/device/location_map`
- 功能：获取设备地理位置分布数据

## 视频上传 API

### 1. 本地视频上传
- **POST** `/api/video/upload`
- 功能：上传本地视频文件

### 2. 进入当前视频(全屏)
- **GET** `/api/video/{video_id}/fullscreen`
- 功能：获取视频全屏播放信息

