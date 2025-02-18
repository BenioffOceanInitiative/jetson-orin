import os
import aiohttp
import ssl
import logging
from datetime import datetime, timezone
from typing import Optional
from socket_types import MessageKeys
import dotenv
dotenv.load_dotenv()

class AuthManager:
    def __init__(self):
        self.logger = logging.getLogger("app")
        self.device_id: str = str(os.getenv('DEVICE_ID', ''))
        self.device_secret: str = os.getenv('DEVICE_SECRET', '')
        self.auth_server_url: str = os.getenv('AUTH_SERVER_URL', '')
        self.ws_server_url: str = os.getenv('WS_SERVER_URL', '')
        self.files_url: str = os.getenv("FILES_URL","")
        self.environment: str = os.getenv('ENVIRONMENT', 'dev')
        self.jwt_token: Optional[str] = None
        self.jwt_expiry: Optional[datetime] = None
        self.ssl_context: Optional[ssl.SSLContext] = None
        self.stream_key: Optional[str] = None

    async def initialize(self):
        self.ssl_context = self.create_ssl_context()
        self.logger.info(f"Initialized AuthManager for environment: {self.environment}")
        self.logger.info(f"Using urls {self.ws_server_url}, {self.auth_server_url}")

    def create_ssl_context(self) -> ssl.SSLContext:
        if self.environment.lower() in ['prod','production']:
            ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            pinned_cert_hash = os.getenv('PINNED_CERT_HASH')
            if pinned_cert_hash:
                def verify_cert(conn, cert, err_num, depth, return_code):
                    if depth == 0:
                        cert_hash = cert.digest('sha256')
                        return cert_hash.hex() == pinned_cert_hash
                    return return_code == 1
                ssl_context.verify_callback = verify_cert
            
            return ssl_context
        else:
            return None

    async def get_valid_jwt(self) -> str:
        if self.jwt_token and self.jwt_expiry and datetime.now(timezone.utc) < self.jwt_expiry:
            return self.jwt_token

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.auth_server_url,
                    json={MessageKeys.DEVICE_ID: self.device_id, MessageKeys.DEVICE_SECRET: self.device_secret},
                    ssl=self.ssl_context
                ) as response:
                    if response.status == 200:
                        auth_data = await response.json()
                        self.jwt_token = auth_data['token']
                        self.jwt_expiry = datetime.fromtimestamp(auth_data['expiry'], tz=timezone.utc)
                        self.stream_key = auth_data['stream_key']
                        self.logger.info("Successfully obtained new JWT token")
                        return self.jwt_token
                    else:
                        self.logger.error(f"Failed to authenticate device: {response.status}")
                        raise Exception(f"Authentication failed with status {response.status}")
            except Exception as e:
                self.logger.error(f"Error during authentication: {e}")
                raise
            
    async def get_presigned_url(self,file_name):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f'{self.files_url}/{file_name}',
                    json={MessageKeys.DEVICE_ID: self.device_id,MessageKeys.DEVICE_SECRET:self.device_secret},
                    ssl = self.ssl_context
                ) as response:
                    if(response.status == 200):
                        data = await response.json()
                        url = data['url']
                        return url
            except Exception as e:
                self.logger.error("Failed to get presigned url")

    def get_ssl_context(self) -> ssl.SSLContext:
        return self.ssl_context

    def get_stream_key(self) -> Optional[str]:
        return self.stream_key

    async def cleanup(self):
        self.jwt_token = None
        self.jwt_expiry = None
        self.stream_key = None
        self.logger.info("AuthManager cleaned up")