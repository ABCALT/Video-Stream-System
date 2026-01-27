import subprocess
from backend.api.device_management.camera_registry import CameraRegistry

# 获取 CameraRegistry 单例实例
_Camera_DB_PATH = "../../DataBase/cameras_db_test.pkl"
_registry = CameraRegistry.get_instance(_Camera_DB_PATH) # 全局Cameras实例
_active_processes: dict[str, subprocess.Popen] = {} # rtsp url: ffmpeg进程