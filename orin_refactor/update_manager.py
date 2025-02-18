import asyncio
from logger import logger
import time


class GitRepoWatcher:
    def __init__(self, device_name, working_dir="/home/orin/jetson-orin"):
        self.last_update = 0
        self.update_cooldown = 60
        self.fetch_interval = 300  # 5 minutes
        self.device_name = device_name
        self.working_dir = working_dir
        self.should_pull = False
    
    async def is_remote_updated(self) -> bool:
        try:
            # Use asyncio subprocess for fetch
            fetch_proc = await asyncio.create_subprocess_exec(
                'git', 'fetch',
                cwd=self.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            fetch_out, fetch_err = await fetch_proc.communicate()
            
            if fetch_proc.returncode != 0 or b"Failed to fetch" in fetch_err:
                logger.error(f"Fetch failed: {fetch_err.decode()}")
                return False
            
            # Check status
            status_proc = await asyncio.create_subprocess_exec(
                'git', 'status', '-uno',
                cwd=self.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            status_out, _ = await status_proc.communicate()
            status_text = status_out.decode()
            
            return "Your branch is behind" in status_text

        except Exception as e:
            logger.error(f"Remote check failed: {str(e)}")
            return False

    async def pull_changes(self):
        try:
            pull_proc = await asyncio.create_subprocess_exec(
                'git', 'pull',
                cwd=self.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await pull_proc.communicate()
            
            if pull_proc.returncode == 0:
                logger.info(f"Pull result: {stdout.decode()}")
                return True
            else:
                logger.error(f"Git pull failed: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Git pull failed: {str(e)}")
            return False

    async def restart_service(self):
        proc = await asyncio.create_subprocess_exec(
            'sudo', 'systemctl', 'restart', f'{self.device_name}.service',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    async def watch(self):
        logger.info(f"Starting to watch repository: {self.working_dir}")
        
        try:
            while True:
                if await self.is_remote_updated():
                    current_time = time.time()
                    if current_time - self.last_update >= self.update_cooldown:
                        logger.info("Remote updates detected")
                        self.last_update = current_time
                        self.should_pull = True
                else:
                    self.should_pull = False
                    
                await asyncio.sleep(self.fetch_interval)
                            
        except KeyboardInterrupt:
            logger.info("Stopping repository watch")