import asyncio
from logger import logger
from typing import Tuple
import ffmpeg
from config_manager import ConfigManager
from socket_types import PayloadKeys
import os

class StreamManager:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logger
        self.process = None
        self.stream_active = False
        self.input_resolution: list = [640, 480]
        self.output_resolution: list = [640, 480]
        self.frame_rate: int = 30
        self.rtmp_url: str = ""
        self.stream_key: str = ""
        self.device_id: str = ""

    async def initialize(self):
        self.input_resolution = tuple(self.config_manager.get(PayloadKeys.RESOLUTION, [1920, 1080]))
        self.output_resolution = tuple(self.config_manager.get(PayloadKeys.STREAM_RESOLUTION, [640, 480]))
        self.frame_rate = self.config_manager.get(PayloadKeys.FPS, 30)
        self.rtmp_url = self.config_manager.get("rtmp_url", "")
        self.stream_key = self.config_manager.get("stream_key", "")
        self.device_id = os.getenv("DEVICE_ID")
        self.logger.info(f"Initialized StreamManager with output URL: {self.rtmp_url}{self.device_id}")

    async def start_stream(self):
        if self.stream_active:
            self.logger.warning("Stream is already active")
            return
        self.logger.info("Starting stream")

        try:
            input_args = {
                'format': 'rawvideo',
                'pix_fmt': 'bgr24',
                's': f'{self.input_resolution[0]}x{self.input_resolution[1]}',
                'framerate': f'{self.frame_rate}',
            }

            output_args = {
                'format': 'flv',
                'vcodec': 'libx264',
                'video_bitrate': '800k',
                'maxrate': '1000k',
                'bufsize': '2000k',
                'framerate': self.frame_rate,
                's': f'{self.output_resolution[0]}x{self.output_resolution[1]}',
                'preset': 'veryfast',
                'tune': 'zerolatency',
                'g': '30',
                'pix_fmt': 'yuv420p',
            }

            stream_url = f"{self.rtmp_url}{self.device_id}?key={self.stream_key}"

            process = (
                ffmpeg
                .input('pipe:', **input_args)
                .output(stream_url, **output_args)
                .overwrite_output()
                .global_args('-loglevel', 'error')
                .run_async(pipe_stdin=True)
            )

            self.process = process
            self.stream_active = True
            self.logger.info("Stream started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start stream: {e}")
            self.stream_active = False
            raise

    async def stop_stream(self):
        if not self.stream_active:
            self.logger.warning("No active stream to stop")
            return

        try:
            if self.process:
                self.process.stdin.close()
                self.process.wait
                self.process = None
            self.stream_active = False
            self.logger.info("Stream stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping stream: {e}")
            raise

    async def send_frame(self, frame):
        if not self.stream_active or not self.process:
            self.logger.error("STREAM INACTIVE OR PROCESS IS NONE")
            return

        try:
            self.logger.debug("Writing frame to stdin") 
            self.process.stdin.write(frame.tobytes())
        except Exception as e:
            self.logger.error(f"Error sending frame to stream: {e}")
            await self.stop_stream()
            raise

    async def update_config(self):
        new_output_url = self.config_manager.get("rtmp_url", "")
        new_stream_key = self.config_manager.get("stream_key", "")
        new_resolution = tuple(self.config_manager.get("stream_resolution", (640, 480)))
        new_frame_rate = self.config_manager.get(PayloadKeys.FPS, 30)

        if (new_output_url != self.output_url or 
            new_stream_key != self.stream_key or 
            new_resolution != self.output_resolution or 
            new_frame_rate != self.frame_rate):
            
            self.logger.info("Stream configuration changed. Reinitializing stream.")
            await self.stop_stream()
            self.output_url = new_output_url
            self.stream_key = new_stream_key
            self.output_resolution = new_resolution
            self.frame_rate = new_frame_rate
            await self.start_stream()

    async def cleanup(self):
        await self.stop_stream()