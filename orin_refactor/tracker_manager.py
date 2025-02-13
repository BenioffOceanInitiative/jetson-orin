import asyncio
import cv2
import logging
from typing import Dict, Any, Optional,AsyncIterator,Tuple,List
from ultralytics import YOLO
from config_manager import ConfigManager
from capture_manager import CaptureManager
from object_counter import ObjectCounter
from stream_manager import StreamManager
import numpy as np
from scipy import stats
from socket_types import *
import time
import os

class TrackerManager:
    def __init__(self, config_manager: ConfigManager,mode):
        self.config_manager = config_manager
        self.capture_manager = CaptureManager(self.config_manager)
        self.stream_manager = None
        self.object_counter = ObjectCounter(config_manager)
        self.logger = logging.getLogger("app")
        self.model = None
        self.mode: Mode = mode
        self.motion_detected: bool = False
        self.tracking: bool = False
        self.motion_hits = 0
        self.no_motion_frames = 0
        self.stop_signal = asyncio.Event()
        self.stream = False
        self.prev_frames: list[np.ndarray] = []
        self.device_id = os.getenv("DEVICE_ID")

    async def initialize(self):
        await self.object_counter.init_config()
        if self.mode != Mode.STREAM_ONLY:
            self.model = YOLO(f"weights/{self.config_manager.get(ConfigKeys.weights, 'best.pt')}")
            self.names = self.model.names
            await self.config_manager.update({ConfigKeys.names:self.names})
        self.logger.info(f"Tracker Mode is {self.mode}")
        self.motion_iou = float(self.config_manager.get(ConfigKeys.motion_iou,.3))
        self.motion_interval = self.config_manager.get(ConfigKeys.motion_interval,.8)
        self.calibration_length = self.config_manager.get(ConfigKeys.calibration_length,100)
        self.motion_hit_count = int(self.config_manager.get(ConfigKeys.motion_hit_count,5))
        self.conf_threshold = self.config_manager.get(ConfigKeys.conf_threshold,.25)
        self.max_no_motion_frames = self.config_manager.get(ConfigKeys.max_no_motion_frames, 20)
        self.show_bboxes = self.config_manager.get(ConfigKeys.show_bboxes,False)
        self.upload_interval = int(self.config_manager.get(ConfigKeys.upload_interval,200))
        
        if self.mode == Mode.STREAM_ONLY:
            self.stream_manager = StreamManager(self.config_manager)
            await self.initialiaze_stream()
        
        await self.capture_manager.initialize()
        self.logger.info(f"Initialized TrackerManager with mode: {self.mode}")

    async def update_config(self): 
        await self.object_counter.init_config()
        if self.stream_manager:
            await self.stream_manager.update_config()
        self.logger.info(f"Updated TrackerManager configuration")

    async def stop_stream(self):
        try:
            if not self.stream_manager:
                return
            await self.stream_manager.stop_stream()
            self.stream = False
            self.stream_manager = None       
            self.logger.info("succesfully stopped stream manager")
            
        except Exception as e:
            self.logger.error(f"error stopping stream {e}")
      
    async def initialiaze_stream(self):
        try:
            self.stream_manager = None
            self.stream_manager = StreamManager(self.config_manager)
            await self.stream_manager.initialize()
            await self.stream_manager.start_stream()
            self.stream = True
            self.logger.info("succesfully started stream manager")
        except Exception as e:
            self.logger.error(f"error starting stream {e}")
            self.stream = False
            self.stream_manager = None
            
    async def run(self) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        self.logger.info(f"Starting tracking in mode: {self.mode}")
        
        while not self.stop_signal.is_set():
            if self.mode == Mode.STREAM_ONLY:
                if not self.stream or self.stream_manager is None or not self.stream_manager.stream_active:
                    break
                async for item in self._stream_only_loop():
                    yield item
            elif self.mode == Mode.COLLECT_DATA:
                async for item in self._collect_data():
                    yield item
            elif self.mode == Mode.COLLECT_DATA_MOTION:
                async for item in self._motion_data_collection():
                    yield item
            elif self.mode == Mode.MOTION_TRACK:
                async for item in self._motion_tracking_loop():
                    yield item
            elif self.mode == Mode.TRACK:
                async for item in self._manual_tracking_loop():
                    yield item
            else:
                self.logger.warning(f"Unsupported mode: {self.mode}")
                break
         
        await self.cleanup()

        self.logger.info("Tracking stopped")

    async def _stream_only_loop(self) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        async for frame in self.capture_manager.get_frame_generator():
            if self.stop_signal.is_set():
                break
            await self.stream_manager.send_frame(frame)
            yield None, None  

    async def _motion_data_collection(self):
        last_motion_check = 0
        self.motion_hits = 0
        self.tracking = False
        prev_upload = time.time()
        async for frame in self.capture_manager.get_frame_generator():
            if self.stop_signal.is_set():
                break
            current_time = time.time()
            if current_time - last_motion_check >= self.motion_interval:
                motion_detected = await self._check_motion(frame)
                last_motion_check = current_time

                if motion_detected:
                    self.motion_hits += 1
                    if self.motion_hits >= self.motion_hit_count:
                        self.motion_detected = True
                        self.tracking = True
                        self.motion_hits = 0
                else:
                    self.motion_hits = 0
                    if self.tracking:
                        self.no_motion_frames += 1
                        if self.no_motion_frames >= self.max_no_motion_frames:
                            self.motion_detected = False
                            self.tracking = False
                            self.no_motion_frames = 0
                    
            if self.tracking:
                if time.time() - prev_upload > self.upload_interval:
                    prev_upload = time.time()
                    yield {"plastic_bottle": 0}, frame
            else:
                self.motion_detected = False
                
            if self.stream and self.stream_manager.stream_active:
                 await self.stream_manager.send_frame(frame)
                    
    async def _collect_data(self) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        prev = time.time()
        async for frame in self.capture_manager.get_frame_generator():
            if self.stop_signal.is_set():
                break
            curr = time.time()
            if curr - prev > self.upload_interval:
                self.logger.info("Sending data from tracking loop")
                prev = curr
                yield {"plastic_bottle": 0}, frame
                
            if self.stream and self.stream_manager and self.stream_manager.stream_active:
                await self.stream_manager.send_frame(frame)

    async def _motion_tracking_loop(self) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        last_motion_check = 0
        self.motion_hits = 0
        self.tracking = False

        async for frame in self.capture_manager.get_frame_generator():
            if self.stop_signal.is_set():
                break

            current_time = time.time()
            if current_time - last_motion_check >= self.motion_interval:
                motion_detected = await self._check_motion(frame)
                last_motion_check = current_time

                if motion_detected:
                    self.motion_hits += 1
                    if self.motion_hits >= self.motion_hit_count:
                        self.motion_detected = True
                        self.tracking = True
                        self.motion_hits = 0
                else:
                    self.motion_hits = 0
                    if self.tracking:
                        self.no_motion_frames += 1
                        if self.no_motion_frames >= self.max_no_motion_frames:
                            self.motion_detected = False
                            self.tracking = False
                            self.no_motion_frames = 0
                    
            if self.tracking:
                async for tracking_data, tracked_frame in self._track_objects(frame):
                    self.motion_detected = True
                    yield tracking_data, tracked_frame
            else:
                self.motion_detected = False
                if self.stream and self.stream_manager.stream_active:
                    await self.stream_manager.send_frame(frame)

    async def _handle_streaming(self, frame: np.ndarray, results: Any) -> None:
        if self.stream and self.stream_manager.stream_active:
            if self.show_bboxes and results:
                frame = self.draw_bboxes(frame, results[0])
            try:
                await self.stream_manager.send_frame(frame)
            except Exception as e:
                self.logger.error(e)
                self.stream = False
                self.stream_manager = None
                
    async def _manual_tracking_loop(self) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        self.tracking = True
        async for frame in self.capture_manager.get_frame_generator():
            if self.stop_signal.is_set():
                break
            async for tracking_data, tracked_frame in self._track_objects(frame):
                yield tracking_data, tracked_frame

    async def _track_objects(self, frame) -> AsyncIterator[Tuple[Dict[str, Any], np.ndarray]]:
        results = await self.process_frame(frame)
        if results and len(results) > 0:
            tracking_data = await self.process_results(results[0], frame)
            if tracking_data:
                yield tracking_data, frame
        
        await self._handle_streaming(frame, results)
               
    async def process_frame(self, frame):
        try:
            results = self.model.track(frame, conf=self.conf_threshold, show=False, persist=True, save=False, verbose=False, device=0)
            return results 
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return None
        
    async def process_results(self, results, frame) -> Optional[Dict[str, Any]]:
        try:
            if results.boxes.id is not None:
                boxes = results.boxes.xyxy.cpu().numpy()
                track_ids = results.boxes.id.int().cpu().numpy().tolist()
                classes = results.boxes.cls.cpu().numpy().tolist()
                
                await self.object_counter.start_counting(boxes, track_ids, classes)
                
                if self.object_counter.should_upload():
                    counts = self.object_counter.get_counts()
                    self.object_counter.reset_upload_flag()
                    
                    return {
                        PayloadKeys.COUNT_DATA: counts,
                        PayloadKeys.DATA: {
                            "total_collected": self.object_counter.collected_total
                        }
                    }
            
            return None
        except Exception as e:
            self.logger.error(f"Error processing results: {e}")
            return None
        
    async def _check_motion(self, frame: np.ndarray) -> bool:
        motion_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_frame = cv2.GaussianBlur(motion_frame, (21, 21), 0)
                
        self.prev_frames.append(motion_frame)
        if len(self.prev_frames) > 3:
            self.prev_frames.pop(0)

        if len(self.prev_frames) == 3:
            diff = cv2.countNonZero(self.diff_img(*self.prev_frames))
            return (diff / motion_frame.size) > self.motion_iou

        return False
    
    def draw_bboxes(self, frame, results):
        if results and results.boxes.id is not None:
            annotated_frame = results.plot()
            cv2.line(annotated_frame, 
                     (0, self.object_counter.counting_region_top), 
                     (frame.shape[1], self.object_counter.counting_region_top), 
                     (0, 255, 0), 2)
            cv2.line(annotated_frame, 
                     (0, self.object_counter.counting_region_bottom),
                     (frame.shape[1], self.object_counter.counting_region_bottom), 
                     (0, 255, 0), 2)
            return annotated_frame
        return frame
    
    def diff_img(self, t0: np.ndarray, t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
        d1 = cv2.absdiff(t2, t1)
        d2 = cv2.absdiff(t1, t0)
        return cv2.bitwise_and(d1, d2)
    

    def get_state(self) -> Dict[str, Any]:
        return {
            PayloadKeys.TRACKING: self.tracking,
            PayloadKeys.MODE: self.mode,
            PayloadKeys.MOTION_DETECTED: self.motion_detected,
            PayloadKeys.COUNT_DATA: self.object_counter.get_counts(),
            PayloadKeys.TRACKER_ALIVE:  not self.stop_signal.is_set(),
            PayloadKeys.STREAM: self.stream_manager and self.stream_manager.stream_active
        }
        
    async def calibrate(self) -> float:
        '''
        Perform calibration to determine a suitable motion threshold.
        '''
        diffs = []

        try:
            if self.capture_manager:
                self.capture_manager = CaptureManager(self.config_manager)
                await self.capture_manager.initialize()
            
            self.calibration_length = int(self.config_manager.get("calibration_length", 100))
            self.motion_interval = float(self.config_manager.get("motion_interval", 2))

            self.prev_frames = []
            for _ in range(3):
                async for frame in self.capture_manager.get_frame_generator():
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
                    self.prev_frames.append(blurred)
                    break

            frame_count = 0
            async for frame in self.capture_manager.get_frame_generator():
                motion_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                motion_frame = cv2.GaussianBlur(motion_frame, (21, 21), 0)

                diff = cv2.countNonZero(self.diff_img(*self.prev_frames))
                diffs.append(diff / motion_frame.size) 

                self.prev_frames = self.prev_frames[1:] + [motion_frame]

                frame_count += 1
                if frame_count >= self.calibration_length:
                    break

                await asyncio.sleep(self.motion_interval)

            threshold = self.calculate_threshold(diffs)
            self.logger.info(f"CALIBRATION COMPLETE, Motion Threshold is {threshold}")
            return threshold

        except Exception as e:
            self.logger.error(f"Error calibrating motion: {e}")
            return 0.1  

    def calculate_threshold(self, diffs: List[float]) -> float:
        '''
        Calculate the motion threshold based on the collected differences.
        '''
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)
        threshold = mean_diff + 2 * std_diff 
        return min(max(threshold, 0.01), 0.99) 

    async def create_status_message(self) -> Message:
        device_id = self.device_id
        payload = Payload(data=self.get_state())
        return Message(device_id, Topic.DEVICE_STATUS, Action.SET_VALUE, payload)

    async def stop(self):
        self.stop_signal.set()
        if self.stream_manager:
            try:
                await self.stream_manager.stop_stream()
            except:
                pass
        await self.capture_manager.stop_capture()
        self.logger.info("Stopped TrackerManager")

    async def cleanup(self):
        await self.stop()
        self.logger.info("Cleaned up TrackerManager resources")