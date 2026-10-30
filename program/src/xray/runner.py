"""Async context manager managing the xray-core subprocess."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.events import EventBus


class XrayBatchRunner:
    """Runs a batch of nodes in a single Xray process with dedicated local SOCKS ports."""

    def __init__(
        self,
        binary_path: Path | str,
        config_dict: Dict[str, Any],
        port_map: Dict[str, int],
        listen_host: str = "127.0.0.1",
        startup_timeout: float = 5.0,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.binary_path = Path(binary_path)
        self.config_dict = config_dict
        self.port_map = port_map
        self.listen_host = listen_host
        self.startup_timeout = startup_timeout
        self.event_bus = event_bus
        self.process: Optional[asyncio.subprocess.Process] = None
        self._temp_config_path: Optional[Path] = None

    async def __aenter__(self) -> XrayBatchRunner:
        # Write config to a temporary file
        fd, temp_path = tempfile.mkstemp(prefix="xray_batch_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.config_dict, f, indent=2)
            self._temp_config_path = Path(temp_path)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

        if not self.binary_path.is_file():
            raise FileNotFoundError(f"Xray binary not found at: {self.binary_path}")

        # Start the Xray subprocess (DEVNULL prevents pipe buffer exhaustion/hangs on Windows)
        cmd = [str(self.binary_path), "run", "-c", str(self._temp_config_path)]
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as e:
            if self._temp_config_path and self._temp_config_path.exists():
                self._temp_config_path.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to launch Xray process: {e}") from e

        # Wait until ports are listening
        ports_to_check = list(self.port_map.values())
        if ports_to_check:
            first_port = ports_to_check[0]
            start_t = time.time()
            ready = False

            while (time.time() - start_t) < self.startup_timeout:
                if self.process.returncode is not None:
                    # Process died prematurely
                    raise RuntimeError(
                        f"Xray exited prematurely with code {self.process.returncode}"
                    )
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(self.listen_host, first_port),
                        timeout=0.2,
                    )
                    writer.close()
                    await writer.wait_closed()
                    ready = True
                    break
                except (OSError, asyncio.TimeoutError):
                    await asyncio.sleep(0.05)

            if not ready:
                await self._terminate_process()
                raise TimeoutError(
                    f"Timed out waiting for Xray local port {first_port} to start listening."
                )

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._terminate_process()
        if self._temp_config_path and self._temp_config_path.exists():
            try:
                self._temp_config_path.unlink(missing_ok=True)
            except OSError:
                pass

    async def _terminate_process(self) -> None:
        """Safely terminate and reap the Xray subprocess."""
        if self.process is not None:
            if self.process.returncode is None:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except (asyncio.TimeoutError, ProcessLookupError):
                    try:
                        self.process.kill()
                        await self.process.wait()
                    except Exception:
                        pass
            self.process = None

    def get_proxy_url(self, node_id: str) -> Optional[str]:
        """Return the socks5 proxy URL for the given node in this batch."""
        port = self.port_map.get(node_id)
        if port:
            return f"socks5://{self.listen_host}:{port}"
        return None
