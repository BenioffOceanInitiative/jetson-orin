from logger import logger
import os

class StorageManager:
    def __init__(self,storage_dir:str = "/media/orin"):
        self.storage_available = False
        self.drive = None
        self.storage_dir = storage_dir
        self.logger = logger
        
        
    def get_storage(self)->bool:
        try:
            drives = os.listdir(self.storage_dir)
            if not len(drives):
                self.storage_available = False
                return False

            for drive in drives:
                if self.test_storage(drive):
                    self.drive = drive
                    break
                
            self.storage_available = True
            self.drive = drives[0]
            if(self.drive):
                self.logger.info(f"Using drive {self.drive}")
                return True
            
        except Exception as e:
            self.logger.error(f"Storage manager Error: {e}")
            return False
    
    def test_storage(self,drive)->bool:            
            return os.path.exists(f"{self.storage_dir}/{drive}")
                