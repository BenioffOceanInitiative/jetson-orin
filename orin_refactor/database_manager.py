import json
import aiosqlite
from pathlib import Path
import logging

logger = logging.getLogger("app")

class DatabaseManager:
    def __init__(self, db_path='tracking_data.db'):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS tracking_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                await db.commit()
            logger.info(f"Database initialized successfully at {self.db_path}")
        except aiosqlite.OperationalError as e:
            logger.error(f"Error initializing database: {e}")
            if "unable to open database file" in str(e):
                logger.error(f"Please check if the application has write permissions to the directory: {Path(self.db_path).parent}")
            raise

    async def store_data(self, data):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('INSERT INTO tracking_data (data) VALUES (?)', (json.dumps(data),))
                await db.commit()
            logger.debug("Data stored successfully")
        except aiosqlite.OperationalError as e:
            logger.error(f"Error storing data: {e}")
            raise

    async def get_unsent_data(self, limit=100):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT id, data FROM tracking_data ORDER BY timestamp ASC LIMIT ?', (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [(row[0], json.loads(row[1])) for row in rows]
        except aiosqlite.OperationalError as e:
            logger.error(f"Error retrieving unsent data: {e}")
            return []

    async def delete_sent_data(self, ids):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM tracking_data WHERE id IN ({})'.format(','.join('?' * len(ids))), ids)
                await db.commit()
            logger.debug(f"Deleted sent data with ids: {ids}")
        except aiosqlite.OperationalError as e:
            logger.error(f"Error deleting sent data: {e}")
            raise

    async def check_db_access(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
            logger.info("Database access check passed")
            return True
        except aiosqlite.OperationalError as e:
            logger.error(f"Database access check failed: {e}")
            return False