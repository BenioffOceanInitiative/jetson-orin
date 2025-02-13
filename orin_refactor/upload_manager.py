from config_manager import ConfigManager
from datetime import datetime
import aiohttp
from aiohttp import FormData
import logging
import numpy as np
import json
import cv2
import io
import time
import os
from socket_types import ConfigKeys
from configuration import config
logger = logging.getLogger("app")
class UploadManager:
    def __init__(self,config_manager:ConfigManager):
        self.config_manager = config_manager   
        
    async def initialize(self):
        self.use_cloud_function = self.config_manager.get(ConfigKeys.use_cloud_function,True)
        self.cloud_function_url = self.config_manager.get(ConfigKeys.upload_url,None)
        self.upload_images = self.config_manager.get(ConfigKeys.enable_uploads,False)
        self.device_id = os.getenv("DEVICE_ID")
        self.server_upload_url = self.config_manager.get("server_upload_url",None)

        
    async def upload(self,image,data,timestamp):
        if self.use_cloud_function:
            try:
                await self.cloud_function_upload(image,data,timestamp)
                
            except Exception as e:
                raise e
        else:
            return
           #await self.server_upload(image,data,timestamp)
            
    async def upload_stored_data(self,image_path,data,timestamp):
        if self.use_cloud_function:
            await self.cloud_function_file_upload(image_path,data,timestamp,self.cloud_function_url)
        else:
            await self.server_upload_stored_data(image_path,data,timestamp)
            
    async def cloud_function_file_upload(self,file_name, data, timestamp,url)-> None | Exception:
        try:
            files = {
                "trash_wheel_id":  str(self.device_id),
                "contents_data":  json.dumps(data),
                "image_file": open(f"output/{file_name}", "rb"),
                "timestamp": datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').isoformat()
            }
    
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url,data=files) as resp:
                        if resp.status != 200:
                            logger.error(f"Error uploading data, {resp.status}")
            except Exception as e:
                logger.error(f"error cloud function file upload uploading:{e}")
                raise e
            finally:
                await session.close()
        
        except Exception as e:
            logger.error(f"Error uploading data: {e}")
            return e
       
    async def cloud_function_upload(self, frame: np.ndarray, data, timestamp):
   
        try:
            _, img_encoded = cv2.imencode('.png', frame)
            img_bytes = img_encoded.tobytes()
            
            form_data = FormData()
            form_data.add_field('trash_wheel_id', str(self.device_id))
            form_data.add_field('contents_data', json.dumps(data))
            form_data.add_field('image_file', 
                                io.BytesIO(img_bytes), 
                                filename=f"{str(round(time.time()) * 1000)}.png",
                                content_type='image/png')
            form_data.add_field('timestamp', datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').isoformat())

            try:
                print(self.cloud_function_url)
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.cloud_function_url, data=form_data) as resp:
                        if resp.status != 200:
                            logger.error(f"Error uploading, resp {resp.status}")
                        else:
                            logger.info("Upload successful")
            except Exception as e:
                logger.error(f"Error uploading: {e}")
            
        except Exception as e:
            logger.error(f"Error preparing upload data: {e}")

           
    
    async def server_upload_stored_data(self,image_path,data,timestamp):
        if self.server_upload_url is None:
            raise NotImplementedError
        
    
    async def server_upload(self, image,data,timestamp):
        if self.server_upload_url is None:
            raise NotImplementedError
        
            