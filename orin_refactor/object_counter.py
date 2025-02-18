from typing import List, Dict, Tuple, Any
from config_manager import ConfigManager
from socket_types import PayloadKeys

class ObjectCounter:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.counting_region_bottom: int = 0
        self.counting_region_top: int = 0
        self.names: List[str] = []
        self.total_counts: Dict[str, int] = {}
        self.counting_list: set = set()
        self.last_seen: int = 0
        self.upload: bool = False
        self.target_object: Dict[str, Any] = {}
        self.frame_counter: int = 0
        self.miss_counter: int = 0
        self.miss_threshold: int = 0
        self.counter_miss_condition: int = 0
        self.upload_threshold: int = 0
        self.collected_total: int = 0
        self.resolution: Tuple[int, int] = (640, 480)

    async def init_config(self):
        self.resolution = self.config_manager.get(PayloadKeys.RESOLUTION, (640, 480))
        self.counting_region_bottom = int(self.resolution[1] * (self.config_manager.get("counting_region_bottom", 25) / 100))
        self.counting_region_top = int(self.resolution[1] * (self.config_manager.get("counting_region_top", 75) / 100))
        self.miss_threshold = self.config_manager.get("miss_threshold", 40)
        self.counter_miss_condition = self.config_manager.get("counter_miss_condition", 5)
        self.upload_threshold = self.config_manager.get("upload_threshold", 20)
        self.total_counts = {name: 0 for name in self.names}

    async def start_counting(self, boxes: List[List[float]], ids: List[int], classes: List[int]):
        if len(boxes) == 0:
            self.target_object = {}
            return
        await self.process_output(boxes, ids, classes)

    async def process_output(self, boxes: List[List[float]], track_ids: List[int], classes: List[int]):
        self.frame_counter += 1
        try:
            if "id" not in self.target_object or self.target_object["id"] is None:
                self.target_object = await self.find_lowest_object(boxes, track_ids)

            for box, track_id, cls in zip(boxes, track_ids, classes):
                center_x, center_y = await self.calculate_box_center(box)

                if self.counting_region_top < center_y < self.counting_region_bottom:
                    await self.update_counting_list(track_id, cls)

                if track_id == self.target_object["id"]:
                    self.last_seen = self.frame_counter
                    self.target_object["box"] = [center_x, center_y]

                if center_y < self.upload_threshold:
                    self.counting_list.discard(track_id)
        except Exception as e:
            raise Exception(f"Error processing output: {e}") from e
        
        await self.manage_target_object(boxes, track_ids)

    @staticmethod
    async def calculate_box_center(box: List[float]) -> Tuple[int, int]:
        center_x = int((box[0] + box[2]) / 2)
        center_y = int((box[1] + box[3]) / 2)
        return center_x, center_y

    async def update_counting_list(self, track_id: int, cls: int):
        if track_id not in self.counting_list:
            self.counting_list.add(track_id)
            class_name = self.names[cls]
            self.total_counts[class_name] = self.total_counts.get(class_name, 0) + 1
            self.collected_total += 1
        
    async def manage_target_object(self, boxes: List[List[float]], track_ids: List[int]):
        if self.frame_counter - self.last_seen > self.counter_miss_condition:
            self.miss_counter += 1
            if self.miss_counter > self.miss_threshold:
                self.target_object = await self.find_lowest_object(boxes, track_ids)
                self.miss_counter = 0
                self.frame_counter = 0
        elif self.target_object["id"] is None:
            self.target_object = await self.find_lowest_object(boxes, track_ids)
        elif self.target_object["box"][1] <= self.upload_threshold:
            self.target_object = await self.find_lowest_object(boxes, track_ids)
            self.upload = True
            self.miss_counter = 0

    async def find_lowest_object(self, boxes: List[List[float]], track_ids: List[int]) -> Dict[str, Any]:
        lowest_object = {"id": None, "box": [0, 0]}
        for box, track_id in zip(boxes, track_ids):
            x, y = await self.calculate_box_center(box)
            if y > lowest_object["box"][1]:
                lowest_object = {"id": track_id, "box": [x, y]}
        return lowest_object

    #TODO
    async def process_total_counts(self)->Dict:
        # loop through counting list and determine max counted class for each ID
        # return dict of classes and counts
        return {}
            
    async def clear(self):
        self.total_counts = {name: 0 for name in self.names}
        self.collected_total = 0

    async def start_counting(self, boxes: List[List[float]], ids: List[int], clss: List[int]):
        if len(boxes) == 0:
            self.target_object = {}
            return
        await self.process_output(boxes, ids, clss)

    def get_counts(self) -> Dict[str, int]:
        return self.total_counts

    def should_upload(self) -> bool:
        return self.upload

    def reset_upload_flag(self):
        self.upload = False