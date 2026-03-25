# -*- coding: utf-8 -*-
"""
MIoT数据存储模块 - 支持本地缓存
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union
import aiofiles

from .error import MIoTError

_LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class MIoTStorage:
    """MIoT数据存储类"""

    def __init__(self, base_path: Union[str, Path], encoding: str = "utf-8"):
        """
        初始化存储

        Args:
            base_path: 存储根目录
            encoding: 文件编码
        """
        self._base_path = Path(base_path)
        self._encoding = encoding
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, domain: str, name: str) -> Path:
        """获取文件路径"""
        domain_path = self._base_path / domain
        domain_path.mkdir(parents=True, exist_ok=True)
        return domain_path / f"{name}.json"

    async def save_async(
        self,
        domain: str,
        name: str,
        data: Any
    ) -> bool:
        """
        异步保存数据

        Args:
            domain: 数据域
            name: 数据名
            data: 数据内容

        Returns:
            是否成功
        """
        try:
            file_path = self._get_file_path(domain, name)
            async with aiofiles.open(file_path, "w", encoding=self._encoding) as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            _LOGGER.debug("Saved data to %s", file_path)
            return True
        except Exception as e:
            _LOGGER.error("Failed to save data: %s", e)
            return False

    def save(
        self,
        domain: str,
        name: str,
        data: Any
    ) -> bool:
        """
        同步保存数据

        Args:
            domain: 数据域
            name: 数据名
            data: 数据内容

        Returns:
            是否成功
        """
        try:
            file_path = self._get_file_path(domain, name)
            file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding=self._encoding
            )
            _LOGGER.debug("Saved data to %s", file_path)
            return True
        except Exception as e:
            _LOGGER.error("Failed to save data: %s", e)
            return False

    async def load_async(
        self,
        domain: str,
        name: str,
        type_: Optional[Type[T]] = None
    ) -> Optional[Union[T, Any]]:
        """
        异步加载数据

        Args:
            domain: 数据域
            name: 数据名
            type_: 数据类型

        Returns:
            数据内容，不存在返回None
        """
        try:
            file_path = self._get_file_path(domain, name)
            if not file_path.exists():
                return None

            async with aiofiles.open(file_path, "r", encoding=self._encoding) as f:
                content = await f.read()
                data = json.loads(content)
                if type_ and isinstance(data, dict):
                    return type_(**data)
                return data
        except Exception as e:
            _LOGGER.error("Failed to load data: %s", e)
            return None

    def load(
        self,
        domain: str,
        name: str,
        type_: Optional[Type[T]] = None
    ) -> Optional[Union[T, Any]]:
        """
        同步加载数据

        Args:
            domain: 数据域
            name: 数据名
            type_: 数据类型

        Returns:
            数据内容，不存在返回None
        """
        try:
            file_path = self._get_file_path(domain, name)
            if not file_path.exists():
                return None

            content = file_path.read_text(encoding=self._encoding)
            data = json.loads(content)
            if type_ and isinstance(data, dict):
                return type_(**data)
            return data
        except Exception as e:
            _LOGGER.error("Failed to load data: %s", e)
            return None

    async def delete_async(self, domain: str, name: str) -> bool:
        """异步删除数据"""
        try:
            file_path = self._get_file_path(domain, name)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            _LOGGER.error("Failed to delete data: %s", e)
            return False

    def delete(self, domain: str, name: str) -> bool:
        """同步删除数据"""
        try:
            file_path = self._get_file_path(domain, name)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            _LOGGER.error("Failed to delete data: %s", e)
            return False

    async def list_domains_async(self) -> list:
        """异步列出所有域"""
        try:
            return [d.name for d in self._base_path.iterdir() if d.is_dir()]
        except Exception:
            return []

    async def list_names_async(self, domain: str) -> list:
        """异步列出域下所有数据名"""
        try:
            domain_path = self._base_path / domain
            if not domain_path.exists():
                return []
            return [
                f.stem for f in domain_path.iterdir()
                if f.is_file() and f.suffix == ".json"
            ]
        except Exception:
            return []
