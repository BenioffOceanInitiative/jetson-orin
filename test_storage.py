import os

class StorageManager:
    def __init__(self,storage_dir,target_folder):
        self.storage_available = False
        self.drive = None
        self.storage_dir = storage_dir
        self.target_folder = target_folder
        
    def get_storage(self)->bool:
        try:
            drives = os.listdir(self.storage_dir)
            if not len(drives):
                self.storage_available = False
                return False

            for drive in drives:
                print(f"Testing {drive}:\r\n")
                if self.test_storage(drive):
                    self.drive = drive
                    break
                
            self.storage_available = True
            self.drive = drives[0]
            print(f"Storage status: {self.storage_available}")
            if(self.drive):
                print(f"Using drive {self.drive}")
                return True
            
        except Exception as e:
            raise(e)
    
    def test_storage(self,drive):            
            return os.path.exists(f"{self.storage_dir}/{drive}")
                
     
    
          
    
storage = StorageManager("/media/dan","testDir")
storage.get_storage()