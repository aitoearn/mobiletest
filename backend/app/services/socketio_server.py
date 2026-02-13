"""Socket.IO server for Scrcpy video streaming."""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Dict, Optional

import socketio

from app.services.scrcpy_protocol import ScrcpyMediaStreamPacket
from app.services.scrcpy_stream import ScrcpyStreamer

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)

_socket_streamers: Dict[str, ScrcpyStreamer] = {}
_stream_tasks: Dict[str, asyncio.Task] = {}
_device_locks: Dict[str, asyncio.Lock] = {}


async def _stop_stream_for_sid(sid: str) -> None:
    task = _stream_tasks.pop(sid, None)
    if task:
        task.cancel()

    streamer = _socket_streamers.pop(sid, None)
    if streamer:
        streamer.stop()


def _classify_error(exc: Exception) -> dict:
    """Classify error and return user-friendly message."""
    error_str = str(exc)

    if "Address already in use" in error_str:
        return {
            "message": "端口冲突，视频流端口仍被占用。请稍后重试。",
            "type": "port_conflict",
        }
    elif "not found" in error_str.lower():
        return {
            "message": "scrcpy-server 未找到，请确保已安装。",
            "type": "server_not_found",
        }
    elif "timeout" in error_str.lower():
        return {
            "message": "连接超时，请检查设备连接后重试。",
            "type": "timeout",
        }
    elif "Failed to connect" in error_str:
        return {
            "message": "无法连接到 scrcpy 服务器，请检查设备连接。",
            "type": "connection_failed",
        }
    else:
        return {
            "message": error_str,
            "type": "unknown",
        }


def stop_streamers(device_id: Optional[str] = None) -> None:
    """Stop active scrcpy streamers (all or by device)."""
    sids = list(_socket_streamers.keys())
    for sid in sids:
        streamer = _socket_streamers.get(sid)
        if not streamer:
            continue
        if device_id and streamer.device_id != device_id:
            continue
        task = _stream_tasks.pop(sid, None)
        if task:
            task.cancel()
        streamer.stop()
        _socket_streamers.pop(sid, None)


async def _stream_packets(sid: str, streamer: ScrcpyStreamer) -> None:
    try:
        async for packet in streamer.iter_packets():
            payload = _packet_to_payload(packet)
            await sio.emit("video-data", payload, to=sid)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("Video streaming failed: %s", exc)
        try:
            await sio.emit("error", {"message": str(exc)}, to=sid)
        except Exception:
            pass
    finally:
        await _stop_stream_for_sid(sid)


def _packet_to_payload(packet: ScrcpyMediaStreamPacket) -> dict:
    payload = {
        "type": packet.type,
        "data": packet.data,
        "timestamp": int(time.time() * 1000),
    }
    if packet.type == "data":
        payload["keyframe"] = packet.keyframe
        payload["pts"] = packet.pts
    return payload


@sio.event
async def connect(sid: str, environ: dict) -> None:
    logger.info(f"Socket.IO client connected: {sid}")
    await sio.emit('connected', {'status': 'ok'}, to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    logger.info("Socket.IO client disconnected: %s", sid)
    await _stop_stream_for_sid(sid)


@sio.on("connect-device")
async def connect_device(sid: str, data: dict) -> None:
    payload = data or {}
    device_id = payload.get("device_id") or payload.get("deviceId")
    if not device_id:
        await sio.emit(
            "error",
            {"message": "Device ID is required", "type": "invalid_request"},
            to=sid,
        )
        return

    max_size = int(payload.get("maxSize") or 1280)
    bit_rate = int(payload.get("bitRate") or 4_000_000)

    # Stop any existing stream for this sid
    await _stop_stream_for_sid(sid)

    # Get or create a lock for this device
    if device_id not in _device_locks:
        _device_locks[device_id] = asyncio.Lock()

    device_lock = _device_locks[device_id]

    async with device_lock:
        # Stop existing streams for the same device (from other sids)
        sids_to_stop = [
            s
            for s, streamer in _socket_streamers.items()
            if s != sid and streamer.device_id == device_id
        ]
        for s in sids_to_stop:
            logger.info(f"Stopping existing stream for device {device_id} from sid {s}")
            await _stop_stream_for_sid(s)

        streamer = ScrcpyStreamer(
            device_id=device_id,
            max_size=max_size,
            bit_rate=bit_rate,
        )

        try:
            await streamer.start()
            metadata = await streamer.read_video_metadata()
            await sio.emit(
                "video-metadata",
                {
                    "deviceName": metadata.device_name,
                    "width": metadata.width,
                    "height": metadata.height,
                    "codec": metadata.codec,
                },
                to=sid,
            )

            _socket_streamers[sid] = streamer
            _stream_tasks[sid] = asyncio.create_task(_stream_packets(sid, streamer))

        except Exception as exc:
            streamer.stop()
            logger.exception("Failed to start scrcpy stream: %s", exc)
            error_info = _classify_error(exc)
            await sio.emit("error", error_info, to=sid)
