"""OS & Arch detection and automated xray-core binary management."""
from __future__ import annotations

import io
import os
import platform
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Optional
import httpx

from src.events import EventBus


class BinaryManager:
    """Detects, downloads, and locates the platform-appropriate xray-core binary."""

    def __init__(self, bin_dir: Path | str = "bin", event_bus: Optional[EventBus] = None) -> None:
        self.bin_dir = Path(bin_dir)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus
        self.system = platform.system()
        self.machine = platform.machine().lower()

    @property
    def binary_name(self) -> str:
        """Name of the xray executable file for current OS."""
        return "xray.exe" if self.system == "Windows" else "xray"

    def get_binary_path(self) -> Optional[Path]:
        """Check if binary already exists in bin_dir or system PATH."""
        local_bin = self.bin_dir / self.binary_name
        if local_bin.is_file():
            return local_bin

        # Check system PATH
        path_binary = shutil.which(self.binary_name) or shutil.which("xray")
        if path_binary:
            return Path(path_binary)

        return None

    def get_asset_name(self) -> str:
        """Map system and machine architecture to official Xray release asset name."""
        sys_name = self.system.lower()
        mach = self.machine

        # Architecture mapping
        if "arm64" in mach or "aarch64" in mach or "armv8" in mach:
            arch = "arm64-v8a"
        elif "armv7" in mach or "arm" in mach:
            arch = "arm32-v7a"
        elif "64" in mach or "amd64" in mach or "x86_64" in mach:
            arch = "64"
        elif "86" in mach or "32" in mach:
            arch = "32"
        else:
            arch = "64"

        if sys_name == "windows":
            return f"Xray-windows-{arch}.zip"
        elif sys_name == "linux":
            return f"Xray-linux-{arch}.zip"
        elif sys_name == "darwin":
            return f"Xray-macos-{arch}.zip"
        else:
            return f"Xray-linux-{arch}.zip"

    def ensure_binary(self) -> Path:
        """
        Ensure xray binary is present, downloading it if necessary.
        Returns the resolved Path to the executable binary.
        """
        existing = self.get_binary_path()
        if existing and existing.is_file():
            return existing

        asset_name = self.get_asset_name()
        download_url = f"https://github.com/XTLS/Xray-core/releases/latest/download/{asset_name}"

        msg = f"Downloading xray-core binary ({asset_name}) from GitHub..."
        if self.event_bus:
            self.event_bus.log(msg, level="INFO")

        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                resp = client.get(download_url)
                resp.raise_for_status()
                zip_bytes = resp.content

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(self.bin_dir)

            dest_binary = self.bin_dir / self.binary_name
            if not dest_binary.is_file():
                # In case zip contained subfolder or differently named file
                for f in self.bin_dir.rglob(self.binary_name):
                    shutil.move(str(f), str(dest_binary))
                    break

            if not dest_binary.is_file():
                raise FileNotFoundError(
                    f"Extracted zip from {download_url} but {self.binary_name} was not found."
                )

            # Ensure executable permission on Unix/Linux/Termux
            if self.system != "Windows":
                st = os.stat(dest_binary)
                os.chmod(dest_binary, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

            if self.event_bus:
                self.event_bus.log(f"xray-core binary ready at {dest_binary}", level="INFO")
            return dest_binary

        except Exception as e:
            err_msg = f"Failed to download xray binary: {e}"
            if self.event_bus:
                self.event_bus.log(err_msg, level="ERROR")
            raise RuntimeError(err_msg) from e
