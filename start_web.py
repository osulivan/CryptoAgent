"""
启动Web API服务器
"""
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 启动FastAPI服务器
    uvicorn.run(
        "src.web.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
