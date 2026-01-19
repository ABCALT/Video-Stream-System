"""
简单 HTTP 测试脚本，用于验证 backend 中 FastAPI 接口是否可正常被调用。

使用方式：
1. 确保你已经在本地启动了 FastAPI 服务，例如：
   uvicorn main:app --reload
   或根据你的项目实际入口修改。
2. 在项目根目录下执行：
   python -m backend.test_api_http
"""

import sys
from typing import Optional

import requests


def test_hello_world(base_url: str) -> None:
    """测试 /api/device/hello 接口是否可用。"""
    url = f"{base_url}/api/device/hello"
    print(f"[*] 测试接口: GET {url}")
    try:
        resp = requests.get(url, timeout=5)
        print("[*] 状态码:", resp.status_code)
        print("[*] 响应内容:", resp.json())
    except Exception as exc:  # noqa: BLE001
        print("[!] 调用 /api/device/hello 失败:", repr(exc))


def main() -> None:
    """
    命令行执行入口。

    可选参数：
        python -m backend.test_api_http [base_url] [rtsp_url]

    例如：
        python -m backend.test_api_http
        python -m backend.test_api_http http://127.0.0.1:8000
        python -m backend.test_api_http http://127.0.0.1:8000 rtsp://your-camera/stream
    """
    base_url = "http://127.0.0.1:8000"

    if len(sys.argv) >= 2:
        base_url = sys.argv[1]

    print(f"[*] 使用 base_url = {base_url}")

    print("\n=== 测试 /api/device/hello ===")
    test_hello_world(base_url)


if __name__ == "__main__":
    main()


