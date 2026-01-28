# camera_operation FastAPI 接口功能说明

对应代码：`backend/api/device_management/camera_operation.py`

- Router 前缀：`/api/device`
- Tag：`camera_operation`

## 1) 添加摄像头

- 路由：`POST /api/device/cameras/add`
- 函数：`add_camera`
- 功能：
  - 将请求体中的摄像头信息加入内存注册表。
  - 当 `protocol_in` 为空时，会基于本地 `video_path` 调用推流模块启动 RTSP 推流，并将返回的 RTSP 地址写入该摄像头的输入协议字段。
  - 当 `protocol_out` 为空时，会生成/转换输出协议地址（当前实现倾向 WebRTC）。
  - 添加成功后会将内存中的摄像头列表保存到数据库。

## 2) 移除摄像头

- 路由：`DELETE /api/device/cameras/remove/{camera_id}`
- 函数：`remove_camera`
- 功能：
  - 从内存注册表中移除指定 `camera_id` 的摄像头。

## 3) 查询摄像头输出协议地址

- 路由：`GET /api/device/cameras/protocol_out/{camera_id}`
- 函数：`get_camera_protocol_out`
- 功能：
  - 根据 `camera_id` 获取该摄像头的 `protocol_out`（用于前端拉流/播放 WebRTC）。

## 4) 启动指定摄像头推流

- 路由：`POST /api/device/cameras/stream/start/{camera_id}`
- 函数：`start_camera_stream`
- 功能：
  - 根据 `camera_id` 找到摄像头实例。
  - 使用其 `camera_name / camera_id / video_path / camera_ip` 调用推流模块启动 RTSP 推流。
  - 将返回的 RTSP 地址更新到该摄像头的输入协议字段（`protocol_in`）。这里模拟打开摄像头的操作

## 5) 停止指定摄像头推流

- 路由：`POST /api/device/cameras/stream/stop/{camera_id}`
- 函数：`stop_camera_stream`
- 功能：
  - 根据 `camera_id` 找到摄像头实例。
  - 计算流名称（通常为 `{camera_name}_{camera_id}`），并调用推流模块停止对应 RTSP 推流。这里模拟关闭摄像头的操作

## 6) 查询单个摄像头状态

- 路由：`GET /api/device/cameras/one_status/{camera_id}`
- 函数：`get_camera_status`
- 功能：
  - 对指定摄像头执行一次健康探测（例如 ping），并返回该摄像头在内存中的基础信息与在线状态。

## 7) 查询全部摄像头状态

- 路由：`GET /api/device/cameras/status`
- 函数：`get_all_cameras_status`
- 功能：
  - 对全部摄像头执行一次批量健康探测（例如批量 ping）。
  - 返回所有摄像头的状态列表（包含基础信息与在线状态）。

## 8) 查询摄像头列表（不做探测）

- 路由：`GET /api/device/cameras/list`
- 函数：`list_all_cameras`
- 功能：
  - 仅返回当前内存中所有摄像头的基础信息，不执行 ping/健康探测。

## 9) 查询摄像头统计信息

- 路由：`GET /api/device/cameras/stats`
- 函数：`get_camera_stats`
- 功能：
  - 返回摄像头注册表的统计信息（例如总数、在线数、离线数等统计）。

## 10) 查询后台健康检查运行状态

- 路由：`GET /api/device/cameras/healthcheck/status`
- 函数：`get_cameras_healthcheck_status`
- 功能：
  - 查询后台周期性健康检查任务当前是否在运行。


## 11) 切换摄像头信息并重启推流

- 路由：`POST /api/device/cameras/set_camera_data`
- 函数：`set_camera_data`
- 功能：
  - 根据 `camera_id` 在内存中定位摄像头实例并更新camera基本信息。
  - 停止该摄像头当前推流。
  - 重新启动推流。
  - 成功后将内存中的摄像头信息保存到数据库。
