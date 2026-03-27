"""
共享常量定义
"""
import os

# 数据存储路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# JSON文件路径
MODELS_FILE = os.path.join(DATA_DIR, "models.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
EXECUTIONS_FILE = os.path.join(DATA_DIR, "executions.json")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")

# 服务配置
DEFAULT_API_PORT = 8000
DEFAULT_EXECUTOR_PORT = 8001
DEFAULT_EXECUTOR_URL = f"http://localhost:{DEFAULT_EXECUTOR_PORT}"
DEFAULT_API_URL = f"http://localhost:{DEFAULT_API_PORT}"
