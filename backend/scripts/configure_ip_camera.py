"""Securely configure a local Imou/Dahua RTSP camera in backend/.env."""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / "backend" / ".env"


def update_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    output: list[str] = []

    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in remaining and not line.lstrip().startswith("#"):
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)

    if remaining:
        if output and output[-1]:
            output.append("")
        output.append("# Household IP camera (local configuration; do not commit)")
        output.extend(f"{key}={value}" for key, value in remaining.items())

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--port", type=int, default=554)
    parser.add_argument("--subtype", choices=("0", "1"), default="1")
    args = parser.parse_args()

    password = getpass("Nhập mật khẩu thiết bị/ONVIF Imou (sẽ không hiển thị): ")
    if not password:
        raise SystemExit("Mật khẩu không được để trống; cấu hình chưa thay đổi.")

    user = quote(args.username, safe="")
    secret = quote(password, safe="")
    rtsp_url = (
        f"rtsp://{user}:{secret}@{args.host}:{args.port}"
        f"/cam/realmonitor?channel=1&subtype={args.subtype}"
    )
    update_env(
        ENV_PATH,
        {
            "HOME_CAMERA_RTSP_URL": rtsp_url,
            "CAMERA_CAPTURE_INTERVAL_SECONDS": "0.5",
            "CAMERA_REQUEST_TIMEOUT_SECONDS": "3",
            "CAMERA_RECONNECT_INTERVAL_SECONDS": "2",
            "CAMERA_MAX_FRAME_BYTES": "1048576",
        },
    )
    print("Đã lưu cấu hình camera vào backend/.env (không in URL hoặc mật khẩu).")


if __name__ == "__main__":
    main()
