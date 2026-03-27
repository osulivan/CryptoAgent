"""
启动API服务
"""
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    # 从环境变量获取端口，默认8000
    port = int(os.getenv("API_SERVICE_PORT", "8000"))
    
    print(f"🚀 启动API服务，端口: {port}")
    
    # 启动FastAPI服务器
    uvicorn.run(
        "src.web.api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
