import os
import dotenv

dotenv.load_dotenv()

DB_NAME = os.getenv('DB_NAME', 'local')
SECRET_KEY = os.getenv('SECRET_KEY','secret' )
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 8000))
WS_SERVER_URL = os.getenv('WS_SERVER_URL', f"ws://{HOST}:{PORT}/ws")
RTMP_URL = os.getenv('RTMP_URL', "http://localhost/live/stream")
UPLOAD_URL = os.getenv('UPLOAD_URL', "http://localhost:8000/upload")
DEVICE_ID = os.getenv('DEVICE_ID', None)
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
DEVICE_SECRET = os.getenv('DEVICE_SECRET', 'secret')
DEVICE_SECRET = os.getenv('DEV_DEVICE_SECRET', 'secret')
PINNED_CERT_HASH = os.getenv('PINNED_CERT_HASH', 'hash')
AUTH_SERVER_URL = os.getenv('AUTH_SERVER_URL', 'http://localhost:8000/auth')
WS_SERVER_URL = os.getenv('WS_SERVER_URL', 'ws://localhost:8000/sockets')
FILES_URL = os.getenv('FILES_URL', 'http://localhost:8000/files')
WORKING_DIR = os.getenv('WORKING_DIR', '/home/orin/jetson-orin')
SERVER_NAME = os.getenv('SERVER_NAME', 'localhost')