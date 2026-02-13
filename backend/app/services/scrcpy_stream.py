"""Scrcpy video streaming implementation."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from asyncio.subprocess import Process as AsyncProcess
from typing import AsyncGenerator, Optional, Union

from app.services.scrcpy_protocol import (
    PTS_CONFIG,
    PTS_KEYFRAME,
    SCRCPY_CODEC_NAME_TO_ID,
    SCRCPY_KNOWN_CODECS,
    ScrcpyMediaStreamPacket,
    ScrcpyVideoStreamMetadata,
    ScrcpyVideoStreamOptions,
)

import logging

logger = logging.getLogger(__name__)


async def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Test if TCP port is available for binding."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        if sock:
            sock.close()


async def wait_for_port_release(
    port: int,
    timeout: float = 5.0,
    poll_interval: float = 0.2,
    host: str = "127.0.0.1",
) -> bool:
    """Wait for TCP port to become available with polling."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await is_port_available(port, host):
            return True
        await asyncio.sleep(poll_interval)
    return False


async def run_cmd_silently(cmd: list) -> None:
    """Run a command silently, ignoring errors."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except Exception:
        pass


@dataclass
class ScrcpyServerOptions:
    max_size: int
    bit_rate: int
    max_fps: int
    tunnel_forward: bool
    audio: bool
    control: bool
    cleanup: bool
    video_codec: str
    send_frame_meta: bool
    send_device_meta: bool
    send_codec_meta: bool
    send_dummy_byte: bool
    video_codec_options: Optional[str]


class ScrcpyStreamer:
    """Manages scrcpy server lifecycle and video stream parsing."""

    def __init__(
        self,
        device_id: Optional[str] = None,
        max_size: int = 1280,
        bit_rate: int = 1_000_000,
        port: int = 27183,
        idr_interval_s: int = 1,
        stream_options: Optional[ScrcpyVideoStreamOptions] = None,
    ):
        self.device_id = device_id
        self.max_size = max_size
        self.bit_rate = bit_rate
        self.port = port
        self.idr_interval_s = idr_interval_s
        self.stream_options = stream_options or ScrcpyVideoStreamOptions()

        self.scrcpy_process: Optional[Union[subprocess.Popen, AsyncProcess]] = None
        self.tcp_socket: Optional[socket.socket] = None
        self.forward_cleanup_needed = False

        self._read_buffer = bytearray()
        self._metadata: Optional[ScrcpyVideoStreamMetadata] = None
        self._dummy_byte_skipped = False

        # Find scrcpy-server location
        self.scrcpy_server_path = self._find_scrcpy_server()

    def _find_scrcpy_server(self) -> str:
        """Find scrcpy-server binary path."""
        # Priority 1: Project root (backend/app/services -> backend/app -> backend -> project_root)
        project_root = Path(__file__).parent.parent.parent.parent
        for name in ["scrcpy-server-v3.3.3", "scrcpy-server"]:
            p = project_root / name
            if p.exists():
                logger.info(f"Using project scrcpy-server: {p}")
                return str(p)

        # Priority 2: Environment variable
        scrcpy_server = os.getenv("SCRCPY_SERVER_PATH")
        if scrcpy_server and os.path.exists(scrcpy_server):
            return scrcpy_server

        # Priority 3: Common system locations
        paths = [
            "/opt/homebrew/Cellar/scrcpy/3.3.3/share/scrcpy/scrcpy-server",
            "/opt/homebrew/share/scrcpy/scrcpy-server",
            "/usr/local/share/scrcpy/scrcpy-server",
            "/usr/share/scrcpy/scrcpy-server",
        ]
        for path in paths:
            if os.path.exists(path):
                logger.info(f"Using system scrcpy-server: {path}")
                return path

        raise FileNotFoundError(
            "scrcpy-server not found. Please put scrcpy-server in project root "
            "or set SCRCPY_SERVER_PATH env var."
        )

    async def start(self) -> None:
        """Start scrcpy server and establish connection."""
        self._read_buffer.clear()
        self._metadata = None
        self._dummy_byte_skipped = False

        try:
            # 1. Kill existing scrcpy server processes on device
            logger.info("Cleaning up existing scrcpy processes...")
            await self._cleanup_existing_server()

            # 2. Push scrcpy-server to device
            logger.info("Pushing server to device...")
            await self._push_server()

            # 3. Setup port forwarding
            logger.info(f"Setting up port forwarding on port {self.port}...")
            await self._setup_port_forward()

            # 4. Start scrcpy server
            logger.info("Starting scrcpy server...")
            await self._start_server()

            # 5. Connect TCP socket
            logger.info("Connecting to TCP socket...")
            await self._connect_socket()
            logger.info("Successfully connected!")

        except Exception as e:
            logger.exception(f"Failed to start: {e}")
            self.stop()
            raise RuntimeError(f"Failed to start scrcpy server: {e}") from e

    async def _cleanup_existing_server(self) -> None:
        """Kill existing scrcpy server processes and wait for port release."""
        cmd_base = ["adb"]
        if self.device_id:
            cmd_base.extend(["-s", self.device_id])

        # Kill scrcpy processes
        await run_cmd_silently(
            cmd_base + ["shell", "pkill", "-9", "-f", "app_process.*scrcpy"]
        )

        # Remove port forward
        await run_cmd_silently(
            cmd_base + ["forward", "--remove", f"tcp:{self.port}"]
        )

        # Wait for port to be available
        await wait_for_port_release(self.port, timeout=5.0, poll_interval=0.2)

    async def _push_server(self) -> None:
        """Push scrcpy-server to device."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["push", self.scrcpy_server_path, "/data/local/tmp/scrcpy-server"])
        await run_cmd_silently(cmd)

    async def _setup_port_forward(self) -> None:
        """Setup ADB port forwarding."""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(["forward", f"tcp:{self.port}", "localabstract:scrcpy"])
        await run_cmd_silently(cmd)
        self.forward_cleanup_needed = True

    def _build_server_options(self) -> ScrcpyServerOptions:
        codec_options = f"i-frame-interval={self.idr_interval_s}"
        return ScrcpyServerOptions(
            max_size=self.max_size,
            bit_rate=self.bit_rate,
            max_fps=20,
            tunnel_forward=True,
            audio=False,
            control=False,
            cleanup=False,
            video_codec=self.stream_options.video_codec,
            send_frame_meta=self.stream_options.send_frame_meta,
            send_device_meta=self.stream_options.send_device_meta,
            send_codec_meta=self.stream_options.send_codec_meta,
            send_dummy_byte=self.stream_options.send_dummy_byte,
            video_codec_options=codec_options,
        )

    async def _start_server(self) -> None:
        """Start scrcpy server on device with retry."""
        max_retries = 3
        retry_delay = 1.0
        options = self._build_server_options()

        for attempt in range(max_retries):
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])

            server_args = [
                "shell",
                "CLASSPATH=/data/local/tmp/scrcpy-server",
                "app_process",
                "/",
                "com.genymobile.scrcpy.Server",
                "3.3.3",
                f"max_size={options.max_size}",
                f"video_bit_rate={options.bit_rate}",
                f"max_fps={options.max_fps}",
                f"tunnel_forward={str(options.tunnel_forward).lower()}",
                f"audio={str(options.audio).lower()}",
                f"control={str(options.control).lower()}",
                f"cleanup={str(options.cleanup).lower()}",
                f"video_codec={options.video_codec}",
                f"send_frame_meta={str(options.send_frame_meta).lower()}",
                f"send_device_meta={str(options.send_device_meta).lower()}",
                f"send_codec_meta={str(options.send_codec_meta).lower()}",
                f"send_dummy_byte={str(options.send_dummy_byte).lower()}",
                f"video_codec_options={options.video_codec_options}",
            ]
            cmd.extend(server_args)

            self.scrcpy_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await asyncio.sleep(2)

            # Check if process is still running
            if self.scrcpy_process.returncode is not None:
                stdout, stderr = await self.scrcpy_process.communicate()
                error_msg = stderr.decode() if stderr else stdout.decode()

                if "Address already in use" in error_msg and attempt < max_retries - 1:
                    logger.warning(f"Port conflict (attempt {attempt + 1}), retrying...")
                    await self._cleanup_existing_server()
                    await asyncio.sleep(retry_delay)
                    continue
                raise RuntimeError(f"Scrcpy server failed: {error_msg}")

            logger.info("Scrcpy server started successfully")
            return

        raise RuntimeError("Failed to start scrcpy server after maximum retries")

    async def _connect_socket(self) -> None:
        """Connect to scrcpy TCP socket."""
        max_attempts = 10
        retry_delay = 0.3

        for attempt in range(max_attempts):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
            except OSError:
                pass

            try:
                sock.connect(("localhost", self.port))
                sock.settimeout(None)
                self.tcp_socket = sock
                logger.debug(f"Connected on attempt {attempt + 1}")
                return
            except (ConnectionRefusedError, OSError) as e:
                try:
                    sock.close()
                except Exception:
                    pass
                if attempt < max_attempts - 1:
                    await asyncio.sleep(retry_delay)
                    if attempt >= 3:
                        retry_delay = 0.5
                else:
                    logger.error(f"Failed after {max_attempts} attempts: {e}")

        raise ConnectionError("Failed to connect to scrcpy server")

    async def _read_exactly(self, size: int) -> bytes:
        if not self.tcp_socket:
            raise ConnectionError("Socket not connected")

        while len(self._read_buffer) < size:
            chunk = await asyncio.to_thread(
                self.tcp_socket.recv, max(4096, size - len(self._read_buffer))
            )
            if not chunk:
                raise ConnectionError("Socket closed by remote")
            self._read_buffer.extend(chunk)

        data = bytes(self._read_buffer[:size])
        del self._read_buffer[:size]
        return data

    async def _read_u16(self) -> int:
        return int.from_bytes(await self._read_exactly(2), "big")

    async def _read_u32(self) -> int:
        return int.from_bytes(await self._read_exactly(4), "big")

    async def _read_u64(self) -> int:
        return int.from_bytes(await self._read_exactly(8), "big")

    async def read_video_metadata(self) -> ScrcpyVideoStreamMetadata:
        """Read video stream metadata from scrcpy."""
        if self._metadata is not None:
            return self._metadata

        if self.stream_options.send_dummy_byte and not self._dummy_byte_skipped:
            await self._read_exactly(1)
            self._dummy_byte_skipped = True

        device_name = None
        width = None
        height = None
        codec = SCRCPY_CODEC_NAME_TO_ID.get(
            self.stream_options.video_codec, SCRCPY_CODEC_NAME_TO_ID["h264"]
        )

        if self.stream_options.send_device_meta:
            raw_name = await self._read_exactly(64)
            device_name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

        if self.stream_options.send_codec_meta:
            codec_value = await self._read_u32()
            if codec_value in SCRCPY_KNOWN_CODECS:
                codec = codec_value
                width = await self._read_u32()
                height = await self._read_u32()
            else:
                width = (codec_value >> 16) & 0xFFFF
                height = codec_value & 0xFFFF
        else:
            if self.stream_options.send_device_meta:
                width = await self._read_u16()
                height = await self._read_u16()

        self._metadata = ScrcpyVideoStreamMetadata(
            device_name=device_name,
            width=width,
            height=height,
            codec=codec,
        )
        return self._metadata

    async def read_media_packet(self) -> ScrcpyMediaStreamPacket:
        """Read one Scrcpy media packet."""
        if not self.stream_options.send_frame_meta:
            raise RuntimeError("send_frame_meta is disabled")

        if self._metadata is None:
            await self.read_video_metadata()

        pts = await self._read_u64()
        data_length = await self._read_u32()
        payload = await self._read_exactly(data_length)

        if pts == PTS_CONFIG:
            return ScrcpyMediaStreamPacket(type="configuration", data=payload)

        if pts & PTS_KEYFRAME:
            return ScrcpyMediaStreamPacket(
                type="data", data=payload, keyframe=True, pts=pts & ~PTS_KEYFRAME,
            )

        return ScrcpyMediaStreamPacket(
            type="data", data=payload, keyframe=False, pts=pts,
        )

    async def iter_packets(self) -> AsyncGenerator[ScrcpyMediaStreamPacket, None]:
        """Yield packets continuously from the scrcpy stream."""
        while True:
            yield await self.read_media_packet()

    def stop(self) -> None:
        """Stop scrcpy server and cleanup."""
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass
            self.tcp_socket = None

        if self.scrcpy_process:
            try:
                self.scrcpy_process.terminate()
                if isinstance(self.scrcpy_process, subprocess.Popen):
                    self.scrcpy_process.wait(timeout=2)
            except Exception:
                try:
                    self.scrcpy_process.kill()
                except Exception:
                    pass
            self.scrcpy_process = None

        if self.forward_cleanup_needed:
            try:
                cmd = ["adb"]
                if self.device_id:
                    cmd.extend(["-s", self.device_id])
                cmd.extend(["forward", "--remove", f"tcp:{self.port}"])
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            except Exception:
                pass
            self.forward_cleanup_needed = False

    def __del__(self):
        self.stop()
