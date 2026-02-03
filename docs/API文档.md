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


## 算法能力 API

### 1. Phrase Grounding（Florence-2）

- **GET** `/api/grounded-phrase/health`
	- 功能：健康检查（不加载模型权重），返回当前 `FLORENCE2_MODEL_ID` 及路径是否存在
- **POST** `/api/grounded-phrase/annotate`
	- 功能：对上传的单张图片做phrase grounding并返回标注后的JPEG
	- Body(JSON)：`image_b64`（base64 JPEG/PNG）、`prompt`
- **POST** `/api/grounded-phrase/annotate_rtsp`
	- 功能：从RTSP读取一帧并做phrase grounding，返回标注后的JPEG
	- Body(JSON)：`rtsp_url`、`prompt`、`timeout_sec?`

### 2. Grounded Tracking（GroundingDINO + SAM2）

- **GET** `/api/grounded-tracking/health`
	- 功能：健康检查（不加载权重），验证 `SAM2_CHECKPOINT/SAM2_CONFIG` 等路径
- **POST** `/api/grounded-tracking/annotate_rtsp`
	- 功能：从RTSP读取一帧并做GroundingDINO+SAM2标注，返回标注后的JPEG
	- Body(JSON)：`rtsp_url`、`text`（建议小写且以`.`结尾，例如`car.`）、`detection_threshold?`、`text_threshold?`、`timeout_sec?`
- **GET** `/api/grounded-tracking/mjpeg`
	- 功能：输出MJPEG（multipart）实时标注流，便于浏览器直接预览
	- Query：`rtsp_url`、`text`、`step?`、`max_fps?`、`duration_sec?`

### 3. 设备注册→推流→算法（已打通）

当摄像头已被注册并且 `protocol_in` 为可读的RTSP地址时，可以使用以下接口直接按 `camera_id` 调用算法：

- **GET** `/api/device/cameras/{camera_id}/grounded_phrase`
	- 功能：读取该 camera 的 `protocol_in` 单帧并做phrase grounding
	- Query：`prompt`、`timeout_sec?`
- **GET** `/api/device/cameras/{camera_id}/grounded_tracking`
	- 功能：读取该 camera 的 `protocol_in` 单帧并做Grounded tracking
	- Query：`text`、`timeout_sec?`、`detection_threshold?`、`text_threshold?`

