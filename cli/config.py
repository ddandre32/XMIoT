# -*- coding: utf-8 -*-
"""
CLI配置管理 - 符合CLI设计规范

配置优先级（从高到低）：
1. 命令行参数
2. 环境变量 (MIOT_*)
3. 配置文件 (~/.miot/config.json)
4. 系统默认
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class CLIConfig:
    """CLI配置管理器"""

    DEFAULT_CONFIG = {
        "uuid": None,
        "redirect_uri": "http://127.0.0.1:8000/callback",
        "cache_path": "~/.miot/cache",
        "cloud_server": "cn",
        "oauth_info": None,
        "format": None,  # None表示自动检测(TTY=table, 非TTY=json)
    }

    # 环境变量映射
    ENV_MAPPINGS = {
        "MIOT_CLOUD_SERVER": "cloud_server",
        "MIOT_REDIRECT_URI": "redirect_uri",
        "MIOT_CACHE_PATH": "cache_path",
        "MIOT_FORMAT": "format",
    }

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}
        self._load()

    @staticmethod
    def _get_default_config_path() -> str:
        """获取默认配置文件路径"""
        # 支持通过环境变量指定配置文件
        env_path = os.environ.get("MIOT_CONFIG_PATH")
        if env_path:
            return os.path.expanduser(env_path)
        return os.path.expanduser("~/.miot/config.json")

    def _load(self) -> None:
        """加载配置（按优先级）"""
        # 1. 加载默认值
        self._config = dict(self.DEFAULT_CONFIG)

        # 2. 加载配置文件
        config_file = Path(self._config_path)
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
            except Exception:
                pass

        # 3. 加载环境变量（覆盖配置文件）
        self._load_from_env()

    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        for env_key, config_key in self.ENV_MAPPINGS.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                # 尝试解析JSON值
                try:
                    parsed_value = json.loads(env_value)
                except json.JSONDecodeError:
                    parsed_value = env_value
                self._config[config_key] = parsed_value

        # OAuth信息可以从环境变量加载（用于CI/自动化场景）
        oauth_token = os.environ.get("MIOT_ACCESS_TOKEN")
        if oauth_token:
            self._config["oauth_info"] = {"access_token": oauth_token}

    def save(self) -> None:
        """保存配置到文件"""
        config_file = Path(self._config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        self._config[key] = value

    def get_cache_path(self) -> str:
        """获取缓存路径"""
        path = self.get("cache_path", "~/.miot/cache")
        return os.path.expanduser(path)

    def get_default_format(self) -> Optional[str]:
        """获取默认输出格式（None表示自动检测）"""
        return self.get("format")

    def get_oauth_info(self) -> Optional[Dict[str, Any]]:
        """获取OAuth信息"""
        return self.get("oauth_info")

    def set_oauth_info(self, oauth_info: Dict[str, Any]) -> None:
        """设置OAuth信息"""
        self._config["oauth_info"] = oauth_info
        self.save()

    @property
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        oauth = self.get_oauth_info()
        return oauth is not None and "access_token" in oauth

    @property
    def config_path(self) -> str:
        """获取配置文件路径"""
        return self._config_path
