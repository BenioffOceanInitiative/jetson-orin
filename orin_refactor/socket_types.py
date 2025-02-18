from dataclasses import dataclass, field
from typing import Dict
from enum import Enum

class StrEnum(str, Enum):
    '''
    This class makes StrEnum work in python3.8 environments
    '''
    def __new__(cls, value):
        if ' ' in value:
            raise ValueError('Invalid value for StrEnum: ' + value)
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    def __str__(self):
        return self.value

class Topic(StrEnum):
    DEVICE_STATUS = "status"
    COMMAND_CONTROL = "control"
    DEVICE_DATA = "data"
    TELEMETRY='telemetry'
    ERROR_REPORT = "error"
    LOG_FILE="log_file"
    PING_RESPONSE = "ping"
    CLIENT_INFO = "info"
    DEVICE_CONFIG = "config"
    AUTHENTICATION_RESULT = "authentication_result"
    CALIBRATION_RESULT = "calibration_result"
    UPDATE_WEIGHTS= "update_weights"

class AuthenticationResult(StrEnum):
    SUCCESS = "true"
    FAILURE = "false"

class Action(StrEnum):
    """actions for messages"""
    SET_VALUE = "set"
    GET_VALUE = "get"

class DeviceStatus(StrEnum):
    """status of devices"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"

class PayloadKeys(StrEnum):
    """keys for payload data"""
    DEVICE_ID='device_id'
    STATUS = "status"
    ERROR = "error"
    DATA = "data"
    TRACKING = "tracking"
    TRACKER_ALIVE = "tracker_alive"
    RESULT = "result"
    TELEMETRY = "telemetry"
    MOTION_TRIGGERED = "motion_triggered"
    MANUAL_TRACKING = "manual_tracking"
    COUNT_DATA = "count_data"
    CONFIG = "config"
    MOTION_DETECTED = "motion_detected"
    MODE = 'mode'
    STREAM = 'stream'
    CALIBRATE = 'calibrate'
    CPU_USAGE= 'cpu'
    MEMORY_USAGE= 'memory'
    TELEMETRY_INTERVAL = 'telemetry_interval'
    SOURCE= 'source'
    FPS= 'fps'
    RESOLUTION = 'resolution'
    STREAM_RESOLUTION= 'stream_resolution'
    CALIBRATION_RESULT = 'calibration_result'
    WEIGHT_FILE_URL="weight_file_URL"
    
class ConfigKeys(StrEnum):
    upload_url = "upload_url"
    device_name ="device_name"
    motion_iou = "motion_iou"
    upload_resolution = "upload_resolution"
    stream_resolution = "stream_resolution"
    motion_interval = "motion_interval"
    motion_hit_count = "motion_hit_count"
    source = "source"
    enable_uploads = "enable_uploads"
    use_cloud_function = "use_cloud_function"
    mode = "mode"
    upload_interval = "upload_interval"
    calibration_length = "calibration_length"
    counting_region_top = "counting_region_top"
    counting_region_bottom = "counting_region_bottom"
    cloud_function_url = "cloud_function_url"
    upload_threshold = "upload_threshold"
    miss_threshold = "miss_threshold"
    counter_miss_condition ="counter_miss_condition"
    stream = "stream"
    rtmp_url = "rtmp_url"
    resolution = "resolution"
    show_bboxes = "show_bboxes"
    conf_threshold = "conf_threshold"
    save_images = "save_images"
    save_videos = "save_videos"
    video_length = "video_length"
    fps = "fps"
    max_image_storage_limit = "max_media_storage_limit"
    max_video_storage_limit = "max_video_storage_limit"
    weights = "weights"
    max_no_motion_frames = "max_no_motion_frames"
    names = "names"
    telemetry_interval = "telemetry_interval"
    working_dir= "working_dir"
    
    
class Control(StrEnum):
    """control commands"""
    START = "start"
    STOP = "stop"

class MessageKeys(StrEnum):
    DEVICE_ID = "device_id"
    DEVICE_SECRET="device_secret"
    TOPIC = "topic"
    PAYLOAD = "payload"
    ACTION = "action"

class Mode(StrEnum):
    COLLECT_DATA= "collect_data"
    COLLECT_DATA_MOTION= "collect_data_motion"
    TRACK = "track"
    MOTION_TRACK = 'motion_track'
    STREAM_ONLY = 'stream_only'
    IDLE = 'idle'
    CALIBRATE = 'calibrate'
    
class TelemetryKeys(StrEnum):
    """keys for telemetry data"""
    ENABLED = "enabled"
    DATA = "data"
    TEMPERATURES = "temperatures"
    ERROR = 'error'
    
@dataclass
class Telemetry:
    """telemetry data"""
    enabled: bool = False
    data: Dict[str, str] = field(default_factory=dict)
    def to_dict(self):
        return {"telemetry": self.enabled}
    
@dataclass
class Payload:
    data: Dict[str, str] = field(default_factory=dict)
    def to_dict(self):
        return self.data

@dataclass
class Message:
    device_id: str | None
    topic: Topic
    action: Action = None
    payload: Payload = None
    def to_dict(self):
        return {
            "device_id": self.device_id,
            "topic": self.topic.value,
            "payload": self.payload.to_dict(),
            "action": self.action.value if self.action else None
        }