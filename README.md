# 视频轮播系统

## 项目简介
视频轮播系统是一个集视频流传输、设备管理、视频上传等功能于一体的监控系统。支持RTSP视频流模拟，可用于监控系统开发测试。

## 功能模块

### 模块1：监控流选择与预览
- 监控设备列表展示（列表/树形结构）
- 设备流地址转换（RTSP → FLV/HLS/WebRTC）
- 设备增删改查管理
- 设备状态监控（在线/离线）

### 模块2：多设备监控预览
- 多路视频流同时预览
- 分屏布局配置（1x1, 2x2, 3x3, 4x4, 1+5, 1+7）
- 预览会话管理
- 大屏联动切换
- RTSP模拟流测试
- 流转发管理

### 模块3：视频导出
- 历史视频存储/回放
- 视频导出功能

### 模块4：视频上传/设备状态
- 监控设备状态（Ping检测）
- 本地视频上传
- 设备分布地域图
- 进入当前视频(全屏)

---

## 快速开始

### 环境要求
- Python 3.10+
- Conda（推荐）
- FFMPEG（视频流推送）
- MediaMTX（RTSP服务器）

（可选）算法能力：
- Florence-2（grounded phrase）本地模型目录（默认 `../Florence-2-large-no-flash-attn`）
- Grounded-SAM-2（grounded tracking）仓库与SAM2 checkpoint（默认从 `../Grounded-SAM-2` 解析）

### 1. 创建并激活环境

```bash
# 创建conda环境
conda create -n video-stream python=3.10 -y

# 激活环境
conda activate video-stream

# 安装依赖
pip install -r requirements.txt

# 如果要启用 grounded tracking（SAM2 + GroundingDINO），需要安装 Grounded-SAM-2 的 python 包
# 假设当前工作目录在 Video-Stream-System，且同级目录存在 ../Grounded-SAM-2
pip install -e ../Grounded-SAM-2

# 如果要启用 grounded phrase（Florence-2），请确保 transformers/torch 可用
# 并准备好 Florence-2 模型目录或设置环境变量 FLORENCE2_MODEL_ID
```

### 2. 启动后端服务

```bash
cd Video-Stream-System
pip install -r requirements.txt

# 入口兼容：backend.main:app -> backend.api.main:app
python -m uvicorn backend.main:app --reload
```

服务启动后访问：
- API文档: http://127.0.0.1:8000/docs
- 健康检查: http://127.0.0.1:8000/

### 3. 运行测试

```powershell
python -m backend.test_api_http
```

（可选）算法健康检查：
- grounded phrase: `GET http://127.0.0.1:8000/api/grounded-phrase/health`
- grounded tracking: `GET http://127.0.0.1:8000/api/grounded-tracking/health`

---

## 视频流模拟（RTSP）

### 准备工作

#### 1. 安装FFMPEG
下载地址: https://ffmpeg.org/download.html

Windows用户推荐下载 `ffmpeg-release-essentials.zip`，解压后将 `bin` 目录添加到系统 PATH。

#### 2. 下载MediaMTX
下载地址: https://github.com/bluenviron/mediamtx/releases

选择 `mediamtx_vX.X.X_windows_amd64.zip`，解压后运行 `mediamtx.exe`（默认监听8554端口）。

### 使用方法

#### 方法1：通过API启动推流

```bash
# 启动视频流推送
POST http://127.0.0.1:8000/api/stream/start
{
    "video_path": "C:/path/to/video.mp4",
    "stream_name": "camera1"
}

# 返回RTSP地址: rtsp://127.0.0.1:8554/live/camera1
```

#### 方法2：手动使用FFMPEG

```powershell
ffmpeg -re -stream_loop -1 -i "video_path.mp4" -c copy -f rtsp rtsp://127.0.0.1:8554/live/camera1
```

### 验证视频流

使用VLC播放器打开: `rtsp://127.0.0.1:8554/live/camera1`

或调用API捕获帧:
```bash
POST http://127.0.0.1:8000/api/stream/capture
{
    "rtsp_url": "rtsp://127.0.0.1:8554/live/camera1"
}
```

---

## API 接口文档

### 监控流选择与预览 `/api/stream`（模块1）

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/devices` | 获取监控设备列表 | - |
| GET | `/devices/tree` | 获取设备树形结构 | - |
| GET | `/devices/{device_id}` | 获取单个设备详情 | `device_id` (path) |
| GET | `/url/{device_id}` | 获取设备流地址 | `device_id` (path), `format?` (query: flv/hls/webrtc) |
| POST | `/devices` | 添加监控设备 | `id`, `name`, `group`, `rtsp_url`, `description?` |
| DELETE | `/devices/{device_id}` | 删除监控设备 | `device_id` (path) |
| PUT | `/devices/{device_id}/status` | 更新设备状态 | `device_id` (path), `status` (online/offline) |
| POST | `/start` | 启动推流 | `video_path`, `stream_name`, `host?`, `port?` |
| POST | `/stop` | 停止推流 | `stream_name` |
| GET | `/list` | 获取活跃流列表 | - |
| POST | `/capture` | 捕获视频帧 | `rtsp_url` |

### 多设备监控预览 `/api/multi-preview`（模块2）

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/layouts` | 获取分屏布局模板 | - |
| POST | `/batch-streams` | 批量获取多路流地址 | `layout_type`, `device_ids` |
| POST | `/session` | 创建预览会话 | `layout_type`, `device_ids` |
| GET | `/session/{session_id}` | 获取预览会话 | `session_id` (path) |
| PUT | `/session/{session_id}/main` | 切换主屏设备 | `session_id` (path), `device_id` |
| DELETE | `/session/{session_id}` | 删除预览会话 | `session_id` (path) |
| GET | `/rtsp/simulate` | 获取模拟RTSP流 | - |
| POST | `/rtsp/forward` | 启动RTSP流转发 | `device_ids` |

### 设备监控 `/api/device`

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/ping/{ip}` | 检测设备在线 | `ip` (path) |
| GET | `/status` | 获取所有设备状态 | - |
| GET | `/list` | 获取设备列表 | - |
| POST | `/register` | 注册设备 | `ip`, `name`, `rtsp_url?`, `description?` |
| DELETE | `/unregister/{id}` | 注销设备 | `id` (path) |
| GET | `/info/{id}` | 获取设备详情 | `id` (path) |
| GET | `/hello` | Hello World测试 | - |

### 算法：Phrase Grounding（Florence-2） `/api/grounded-phrase`

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/health` | 算法配置健康检查（不加载权重） | - |
| POST | `/annotate` | base64输入，输出标注JPEG | `image_b64`, `prompt` |
| POST | `/annotate_rtsp` | RTSP读取单帧，输出标注JPEG | `rtsp_url`, `prompt`, `timeout_sec?` |

### 算法：Grounded Tracking（GroundingDINO + SAM2） `/api/grounded-tracking`

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/health` | 配置/权重路径健康检查（不加载权重） | - |
| POST | `/annotate_rtsp` | RTSP读取单帧，输出标注JPEG | `rtsp_url`, `text`, `thresholds?` |
| GET | `/mjpeg` | 输出MJPEG流（RTSP输入） | `rtsp_url`, `text`, `step?`, `max_fps?` |

### 设备流→算法（已打通） `/api/device/cameras/{camera_id}`

| 方法 | 接口 | 功能 | 参数 |
|-----|------|-----|------|
| GET | `/grounded_phrase` | 用 camera 的 `protocol_in`(RTSP) 单帧做phrase grounding | `prompt`, `timeout_sec?` |
| GET | `/grounded_tracking` | 用 camera 的 `protocol_in`(RTSP) 单帧做Grounded-SAM2标注 | `text`, `timeout_sec?` |

#### 常用环境变量

```bash
# grounded phrase
export FLORENCE2_MODEL_ID=../Florence-2-large-no-flash-attn
export FLORENCE2_DEVICE=cuda:0
export FLORENCE2_FP16=1

# grounded tracking
export SAM2_CHECKPOINT=../Grounded-SAM-2/checkpoints/sam2.1_hiera_large.pt
export SAM2_CONFIG=../Grounded-SAM-2/sam2/configs/sam2.1/sam2.1_hiera_l.yaml
export GROUNDED_TRACKING_DEVICE=cuda
export GROUNDED_DINO_MODEL_ID=IDEA-Research/grounding-dino-tiny
```

---

## 项目结构

```
Video-Stream-System/
├── backend/                    # 后端代码
│   ├── api/                   # API 接口
│   │   ├── video_stream/      # 视频流相关接口
│   │   │   ├── rtsp_manager.py   # RTSP推流管理
│   │   │   ├── monitor_stream.py # 监控流选择与预览（模块1）
│   │   │   ├── multi_preview.py  # 多设备监控预览（模块2）
│   │   │   └── data/             # 设备数据持久化
│   │   │       └── devices.json  # 监控设备配置
│   │   ├── device_management/ # 设备管理接口
│   │   │   ├── device_monitor.py  # 设备状态监控
│   │   │   └── hello_world.py     # 示例接口
│   │   └── video_upload/      # 视频上传接口
│   ├── data/                  # 数据持久化目录
│   │   ├── streams.json       # 视频流配置
│   │   └── devices.json       # 设备信息
│   ├── main.py               # FastAPI入口
│   ├── test_api_http.py      # API测试脚本
│   └── test_full_demo.py     # 完整功能验证
├── video_monitor/             # 视频监控资源
│   └── test_video/           # 测试视频文件
├── config/                    # 项目配置文件
├── docs/                      # 项目文档
├── static/                    # 静态文件存储
├── requirements.txt           # Python依赖
└── README.md                  # 项目说明
```

---

## 技术栈
- **后端**: Python + FastAPI
- **视频处理**: FFMPEG + OpenCV
- **RTSP服务**: MediaMTX
- **数据持久化**: JSON文件
- **流媒体格式**: FLV / HLS / WebRTC

---

## 开发说明

### 添加新接口

1. 在对应模块下创建 `.py` 文件
2. 使用 `APIRouter` 创建路由
3. 在 `main.py` 中注册路由

示例：
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/your-module", tags=["your_module"])

@router.get("/your-endpoint")
async def your_function() -> dict:
    return {"message": "Hello"}
```

### 测试接口

```powershell
# 启动服务
python -m uvicorn backend.main:app --reload

# 运行测试
python -m backend.test_api_http
```

---

## 常见问题

### Q: FFMPEG未找到？
确保FFMPEG的 `bin` 目录已添加到系统PATH环境变量。

### Q: 无法连接RTSP流？
确保MediaMTX正在运行（端口8554）。

### Q: Ping设备超时？
设备监控的ping功能只能检测同一网络下的设备。

---

## License
MIT
