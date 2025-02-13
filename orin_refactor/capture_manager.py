import asyncio
import cv2
import numpy as np
from typing import Tuple, Optional, AsyncGenerator
from config_manager import ConfigManager
from socket_types import PayloadKeys
import logging

class CaptureManager:
    def __init__(self, config_manager: ConfigManager):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_lock = asyncio.Lock()
        self.resolution: list = [640, 480]
        self.fps: int = 30
        self.source: str = "/dev/video0"
        self.stop_capture_event = asyncio.Event()

    async def initialize(self):
        self.source = self.config_manager.get(PayloadKeys.SOURCE, self.source)
        self.resolution = tuple(self.config_manager.get(PayloadKeys.RESOLUTION, self.resolution))
        self.fps = self.config_manager.get(PayloadKeys.FPS, self.fps)
        await self.get_cap()

    async def get_cap(self):
        if self.cap is not None:
            await self.stop_capture()
        try:
            self.cap = cv2.VideoCapture(self.source)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        except Exception as e:
            raise Exception(f"Could not initialize Video Capture: {e}")

    async def get_frame_generator(self) -> AsyncGenerator[np.ndarray, None]:
        while not self.stop_capture_event.is_set():
            try:
                async with self.frame_lock:
                    ret, frame = await asyncio.get_event_loop().run_in_executor(None, self.cap.read)
                    if not ret:
                        continue
                    yield frame
            except Exception as e:
                self.logger.error(f"Error getting frame: {e}")
                break

    async def stop_capture(self):
        self.stop_capture_event.set()
        if self.cap is not None:
            self.cap.release
            self.cap = None

    async def cleanup(self):
        await self.stop_capture()
        self.stop_capture_event.clear()