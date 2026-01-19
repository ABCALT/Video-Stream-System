# 视频轮播系统

## 项目简介
视频轮播系统是一个集视频流传输、设备管理、视频上传等功能于一体的监控系统。

## 功能模块

### 视频流传输
- 监控流选择与预览
- 多设备监控预览
- 视频导出
- 历史视频存储/回放

### 视频上传/监控设备状态
- 监控设备状态
- 本地视频上传
- 设备分布地域图
- 进入当前视频(全屏)

## 项目结构

```
VideoStream/
├── backend/              # 后端代码
│   ├── api/             # API 接口
│   │   ├── video_stream/      # 视频流相关接口
│   │   ├── device_management/ # 设备管理接口
│   │   └── video_upload/      # 视频上传接口
│   ├── models/          # 数据模型
│   ├── utils/           # 工具函数
│   └── config/          # 配置文件
├── frontend/            # 前端代码
│   └── src/
│       ├── components/
│       │   ├── VideoStream/        # 视频流组件
│       │   ├── DeviceManagement/   # 设备管理组件
│       │   └── VideoUpload/        # 视频上传组件
│       ├── utils/       # 前端工具函数
│       └── assets/      # 静态资源
├── database/            # 数据库相关
│   ├── migrations/      # 数据库迁移文件
│   └── models/          # 数据库模型
├── static/              # 静态文件存储
│   ├── uploads/         # 上传的视频文件
│   ├── exports/         # 导出的视频文件
│   └── history/         # 历史视频文件
├── config/              # 项目配置文件
├── docs/                # 项目文档
└── tests/               # 测试文件
```

## 技术栈
- 后端: Python (FastAPI/Flask)
- 前端: React/Vue
- 数据库: MySQL/PostgreSQL
- 视频处理: FFmpeg

## 安装与运行
（待完善）

## 开发说明
（待完善）

