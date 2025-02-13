import asyncio
import websockets
import json
import logging
from typing import Dict, Any, AsyncGenerator
from configuration.config import DEVICE_ID
from config_manager import ConfigManager
from auth_manager import AuthManager
from socket_types import Topic, Action, DeviceStatus, PayloadKeys, MessageKeys, Message, Payload

class WebSocketClient:
    def __init__(self, config_manager: ConfigManager, auth_manager: AuthManager):
        self.config_manager = config_manager
        self.auth_manager = auth_manager
        self.websocket = None
        self.connected = False
        self.logger = logging.getLogger("app")
        self.reconnect_interval = 5  # seconds
        self.device_id = DEVICE_ID
        self.last_connection_error = ''
        self.connection_error = False

    async def connect(self) -> None:
        self.connection_task = asyncio.create_task(self._connect_loop())
        
    async def _connect_loop(self) -> None:
        while not self.connected:
            try:
                jwt_token = await self.auth_manager.get_valid_jwt()
                ws_server_url = self.auth_manager.ws_server_url
                stream_key = self.auth_manager.stream_key
                self.websocket = await websockets.connect(
                    f"{ws_server_url}/{self.device_id}?token={jwt_token}",
                    ssl=self.auth_manager.get_ssl_context()
                )
                if self.websocket:
                    self.connected = True
                    self.logger.info("Connected to WebSocket server")
                    await self.config_manager.update({'stream_key':stream_key})
                    self.connection_error = False
                    self.last_connection_error = None 
                    await self.send_status_update(DeviceStatus.ONLINE)
            except ConnectionError as e:
                if not self.connection_error:
                    self.connection_error = True
                    self.logger.error(e)
            except Exception as e:
                if e != self.last_connection_error:
                    self.logger.error(self.last_connection_error)
                    self.last_connection_error = e
                await asyncio.sleep(self.reconnect_interval)

    def is_connected(self) -> bool:
        return self.connected
    
    async def disconnect(self) -> None:
        if hasattr(self, 'connection_task'):
            self.connection_task.cancel()
        if self.websocket:
            await self.websocket.close()
        self.connected = False
        self.logger.info("Disconnected from WebSocket server")

    async def send_message(self, message: Message) -> None:
        if not self.connected:
            raise ConnectionError("Not connected to WebSocket server")
        try:
            await self.websocket.send(json.dumps(message.to_dict()))
        except websockets.exceptions.ConnectionClosed:
            self.logger.error("WebSocket connection closed unexpectedly")
            self.connected = False
            await self.connect()
        except Exception as e:
            self.logger.error(f"error sending message {e}")

    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        while True:
            try:
                if not self.connected:
                    await self.connect()
                message = await self.websocket.recv()
                yield json.loads(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.error("WebSocket connection closed. Attempting to reconnect...")
                self.connected = False
                await asyncio.sleep(self.reconnect_interval)
            except json.JSONDecodeError:
                self.logger.error("Received invalid JSON message")
            except Exception as e:
                self.logger.error(f"Error in WebSocket communication: {e}")
                await asyncio.sleep(self.reconnect_interval)

    async def send_status_update(self, status: DeviceStatus) -> None:
        message = Message(
            device_id=self.device_id,
            topic=Topic.DEVICE_STATUS,
            action=Action.SET_VALUE,
            payload=Payload(data={PayloadKeys.STATUS: status})
        )
        await self.send_message(message)

    async def send_telemetry(self, telemetry_data: Dict[str, Any]) -> None:
        message = Message(
            device_id=self.device_id,
            topic=Topic.DEVICE_DATA,
            action=Action.SET_VALUE,
            payload=Payload(data={PayloadKeys.TELEMETRY: telemetry_data,PayloadKeys.STATUS:DeviceStatus.ONLINE})
        )
        await self.send_message(message)

    async def send_tracking_data(self, tracking_data: Dict[str, Any]) -> None:
        message = Message(
            device_id=self.device_id,
            topic=Topic.DEVICE_DATA,
            action=Action.SET_VALUE,
            payload=Payload(data={PayloadKeys.COUNT_DATA: tracking_data})
        )
        await self.send_message(message)

    async def send_error(self, error_message: str) -> None:
        message = Message(
            device_id=self.device_id,
            topic=Topic.ERROR_REPORT,
            action=Action.SET_VALUE,
            payload=Payload(data={PayloadKeys.ERROR: error_message})
        )
        await self.send_message(message)
    
    async def send_error_list(self,errors:list):
        message = Message(
            device_id=self.device_id,
            topic=Topic.ERROR_REPORT,
            action = Action.SET_VALUE,
            payload=Payload(data={PayloadKeys.ERROR:errors})
        )
    