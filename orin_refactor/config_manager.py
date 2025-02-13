from typing import Dict, Any
import json
import logging
from socket_types import *
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file: str = 'configuration/config.json'):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger("app")

    async def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            self.logger.info(f"Configuration loaded from {self.config_file}")
            await self.check_weights()
        except FileNotFoundError:
            self.logger.error(f"Config file {self.config_file} not found. Using empty configuration.")
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing the config file: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error loading config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        If the key is not found, return the default value.
        Supports nested keys using dot notation.
        """
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            self.logger.warning(f"Configuration key '{key}' not found. Using default value: {default}")
            return default
        
    async def check_weights(self):
        """
        Check weights directory for weights
        """
        weights = os.listdir("weights")
        self.config['available_weights'] = weights
        self.logger.info(f"Available weights {weights}")
        
    async def update(self, new_config: Dict[str, Any]):
        """
        Update the configuration with new values and save to file.
        """
        self.config.update(new_config)

        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)  
            self.logger.info(f"Configuration updated and saved to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.
        """
        return self.config.copy()

    def get_mode(self) -> str:
        return self.get(PayloadKeys.MODE, "idle")

    def get_stream_config(self) -> Dict[str, Any]:
        return {
            'enabled': self.get(f"{PayloadKeys.STREAM}.enabled", False),
            'url': self.get(f"{PayloadKeys.STREAM}.url", ""),
            'resolution': self.get(f"{PayloadKeys.STREAM}.resolution", (640, 480)),
        }

    def get_tracker_config(self) -> Dict[str, Any]:
        return {
            'weight_file': self.get('weight_file', "weights/best.pt"),
            'conf_threshold': self.get('conf_threshold', 0.25),
            'motion_detection': self.get('motion_detection', False),
        }
    