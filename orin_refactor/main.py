import asyncio
import logging
from typing import Dict, Any
from config_manager import ConfigManager
from tracker_manager import TrackerManager
from database_manager import DatabaseManager
from auth_manager import AuthManager
import websockets
from websocket_client import WebSocketClient
from upload_manager import UploadManager
from socket_types import *
import json
from logger import logger
import psutil
from datetime import datetime, timezone
import cv2
import time
import os

class TrackingApplication:
    def __init__(self):
        self.config_manager = ConfigManager('configuration/config.json')
        self.upload_manager = UploadManager(self.config_manager)
        self.database_manager = DatabaseManager()
        self.auth_manager = AuthManager()
        self.websocket_client = WebSocketClient(self.config_manager, self.auth_manager)
        self.telemetry = False
        self.tracker_manager = None
        self.tracking_task = None
        self.telemetry_task = None
        self.current_mode = Mode.IDLE
        self.error_queue = []
        self.stream = False
        
        self.logger = logging.getLogger("app")

    async def initialize(self):
        await self.config_manager.load_config()
        await self.database_manager.initialize()
        await self.upload_manager.initialize()
        await self.auth_manager.initialize()
        await self.websocket_client.connect()
        self.telemetry_interval = self.config_manager.get(ConfigKeys.telemetry_interval, 3)
        self.device_id = os.getenv("DEVICE_ID")
        
        initial_mode = Mode(self.config_manager.get(ConfigKeys.mode, Mode.IDLE))
        await self.set_mode(initial_mode)

    async def set_mode(self, new_mode: Mode):
        self.logger.info(f"Setting Mode to {new_mode}")
        if new_mode == self.current_mode:
            self.logger.info("No change in Mode")
            return
        
        if self.tracker_manager is not None:
            await self.tracker_manager.stop()
            if self.tracking_task:
                self.tracking_task.cancel()
                try:
                    await self.tracking_task
                except asyncio.CancelledError:
                    pass
            self.tracker_manager = None
            self.tracking_task = None

        self.current_mode = new_mode
        await self.config_manager.update({PayloadKeys.MODE:new_mode})

        if new_mode != Mode.IDLE:
            self.tracker_manager = TrackerManager(self.config_manager,self.current_mode)
            await self.tracker_manager.initialize()
            self.tracker_manager.mode = new_mode  
            self.tracking_task = asyncio.create_task(self.run_tracking())
        
        self.logger.info(f"Mode set to {new_mode}")

    async def run(self):
        await self.initialize()
        
        try:
            await self.run_websocket_communication()
        except Exception as e:
            self.logger.error(f"An error occurred in the main loop: {e}")
        finally:
            await self.cleanup()

    async def run_tracking(self):
        try:
            async for tracking_data, frame in self.tracker_manager.run():
                if tracking_data:
                    await self.handle_tracking_data(tracking_data, frame)
        except asyncio.CancelledError:
            self.logger.info("Tracking task cancelled")
        except Exception as e:
            await self.append_error(e)
            self.logger.error(f"Error in tracking task: {e}")
        finally:
            await self.tracker_manager.cleanup()

    async def run_websocket_communication(self):
        while True:
            if not self.websocket_client.is_connected():
                await asyncio.sleep(5)  # wait before trying to reconnect
                continue

            try:
                async for message in self.websocket_client.listen():
                    await self.handle_websocket_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed. Attempting to reconnect...")
                continue
            await self.upload_stored_data()
            
    async def run_calibration(self):
        if self.tracker_manager is None:
            self.tracker_manager = TrackerManager(self.config_manager,Mode.CALIBRATE)
        result = await self.tracker_manager.calibrate()
        await self.websocket_client.send_message(Message(self.device_id,topic = Topic.CALIBRATION_RESULT,action=Action.SET_VALUE,payload = Payload(data={PayloadKeys.CALIBRATION_RESULT:result})))
        await self.tracker_manager.cleanup()
        await self.set_mode(Mode.IDLE)
            
    async def handle_tracking_data(self, tracking_data: Dict[str, Any], frame):
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        if self.config_manager.get('enable_uploads', False):
            try:
                await self.upload_manager.upload( frame,tracking_data,timestamp)
            except Exception as e:
                await self.append_error(e)
                self.logger.error(f"error uploading data: {e}")
                #await self.database_manager.store_data(tracking_data)
        else:
            if self.config_manager.get("save_locally",False):
                if self.config_manager.get("save_images",False):
                    filename = str(round(time.time()) * 1000)
                    tracking_data['timestamp'] = timestamp
                    cv2.imwrite(f"output/{filename}.jpg",frame)
                    tracking_data['file_name'] = filename
                await self.database_manager.store_data(tracking_data)

    async def handle_websocket_message(self, message: Dict[str, Any]):
        try:
            if message[MessageKeys.TOPIC] == Topic.DEVICE_CONFIG:
                if message[MessageKeys.ACTION] == Action.GET_VALUE:
                    config = self.config_manager.get_all()
                    await self.websocket_client.send_message(Message(device_id=self.device_id, topic=Topic.DEVICE_CONFIG, action=Action.SET_VALUE, payload=Payload(data={PayloadKeys.CONFIG: config})))
                elif message[MessageKeys.ACTION] == Action.SET_VALUE:
                    await self.handle_config_update(message[MessageKeys.PAYLOAD][PayloadKeys.CONFIG])
                
            elif message[MessageKeys.TOPIC] == Topic.COMMAND_CONTROL:
                await self.handle_control_command(message[MessageKeys.PAYLOAD])
        except Exception as e:
            await self.append_error(e)
            
    async def handle_config_update(self, config: Dict[str, Any]):
        try:
            await self.config_manager.update(config)
            await self.reset()
        except Exception as e:
            await self.append_error(e) 
            
    async def reset(self):
        prev_mode = self.current_mode
        await self.upload_manager.initialize()
        await self.set_mode(Mode.IDLE)
        await asyncio.sleep(.5)
        await self.set_mode(prev_mode)

    async def handle_control_command(self, command: Dict[str, Any]):
        if PayloadKeys.MODE in command:
            new_mode = Mode(command[PayloadKeys.MODE])
            await self.set_mode(new_mode)
        if PayloadKeys.STREAM in command:
            if self.tracker_manager:
                stream = command[PayloadKeys.STREAM]
                if stream:
                    await self.tracker_manager.initialiaze_stream()
                    self.stream = True
                else:
                    await self.tracker_manager.stop_stream()
                    self.stream = False
        if PayloadKeys.TELEMETRY in command:
            await self.toggle_telemetry(command[PayloadKeys.TELEMETRY])
        if PayloadKeys.CALIBRATE in command:
            await self.run_calibration()

    async def toggle_telemetry(self, state: bool):
        if self.telemetry and self.telemetry_task and state:
            return
        if self.telemetry_task is None and state:
            self.telemetry = True
            self.telemetry_task = asyncio.ensure_future(self.run_telemetry())
        if self.telemetry and state is False:
            self.telemetry = False
            if self.telemetry_task:
                self.telemetry_task.cancel()
                self.telemetry_task = None

    async def run_telemetry(self):
        while self.telemetry:
            if self.websocket_client.is_connected():
                telemetry_data = await self.get_telemetry()
                await self.websocket_client.send_telemetry(telemetry_data)
                if len(self.error_queue):
                    await self.websocket_client.send_error_list(self.error_queue)
                    self.error_queue = []

            await asyncio.sleep(self.telemetry_interval)
            
    async def get_telemetry(self) -> Dict[str, Any]:
        try:
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            if self.tracker_manager:
                tracker_state = self.tracker_manager.get_state()
                tracker_state[PayloadKeys.CPU_USAGE] = cpu_usage
                tracker_state[PayloadKeys.MEMORY_USAGE] =  memory_usage
                return tracker_state
            return {
            PayloadKeys.TRACKING: False,
            PayloadKeys.MODE: self.config_manager.get("mode"),
            PayloadKeys.MOTION_DETECTED: False,
            PayloadKeys.COUNT_DATA: {},
            PayloadKeys.TRACKER_ALIVE:  False,
            PayloadKeys.CPU_USAGE : cpu_usage,
            PayloadKeys.MEMORY_USAGE: memory_usage,
            PayloadKeys.STREAM: self.stream
            }
        
        except Exception as e:
            self.logger.error(f"Error collecting telemetry data: {e}")
            await self.append_error(e)
            return {TelemetryKeys.ENABLED: False, TelemetryKeys.DATA: {},TelemetryKeys.ERROR:e}
    
    async def append_error(self,error:str):
        if len(self.error_queue) > 10:
            self.error_queue = self.error_queue[-10:]
        timestamp = datetime.now(timezone.utc).isoformat()
        self.error_queue.append(f"{timestamp}:{error}")
            
    async def cleanup(self):
        self.logger.info("Cleaning up resources...")
        if self.tracker_manager:
            await self.tracker_manager.cleanup()
        await self.websocket_client.disconnect()
        await self.auth_manager.cleanup()

    async def upload_stored_data(self):
        while True:
            stored_data = await self.database_manager.get_unsent_data(limit=100)
            if not stored_data:
                break

            for id, data in stored_data:
                if not self.websocket_client.is_connected():
                    return  # stop if connection is lost again
                try:
                    json_data = json.loads(data)
                    if json_data['file_name']:
                        await self.upload_manager.upload_stored_data(json_data['file_name'],json_data,json_data['timestamp'])
                    await self.upload_manager.upload(None, json_data, json_data['timestamp'])
                    await self.database_manager.delete_sent_data([id])
                except Exception as e:
                    await self.append_error(e)
                    self.logger.error(f"Failed to upload stored data: {e}")


async def main():
    logger.info("Starting the application")
    app = TrackingApplication()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())