"""
共享文件存储操作
用于读写JSON文件
"""
import json
import fcntl
import os
from typing import Any


def load_json_file(filepath: str, default: Any = None) -> Any:
    """加载JSON文件"""
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 获取共享锁（读锁）
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (json.JSONDecodeError, IOError):
        return default if default is not None else []


def save_json_file(filepath: str, data: Any):
    """保存JSON文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        # 获取独占锁（写锁）
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def generate_id() -> str:
    """生成唯一ID"""
    import uuid
    return str(uuid.uuid4())
