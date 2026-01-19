"""
配置文件示例
复制此文件为 config.py 并修改相应配置
"""

# 数据库配置
DATABASE_URL = "sqlite:///./video_stream.db"
# 生产环境使用：
# DATABASE_URL = "postgresql://user:password@localhost/videostream"

# 应用配置
APP_NAME = "视频轮播系统"
APP_VERSION = "1.0.0"
DEBUG = True

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000

# 文件上传配置
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".flv"]

# 视频存储路径
UPLOAD_DIR = "static/uploads"
EXPORT_DIR = "static/exports"
HISTORY_DIR = "static/history"

# 视频流配置
STREAM_TIMEOUT = 30  # 秒
MAX_CONCURRENT_STREAMS = 10

# 设备管理配置
DEVICE_STATUS_CHECK_INTERVAL = 60  # 秒

