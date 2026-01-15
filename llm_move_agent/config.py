"""
LLM Agent 配置管理
支持 DeepSeek / OpenAI / Gemini 多种模型
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class LLMConfig:
    """LLM 配置类"""
    
    # 提供商配置
    PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
    
    # DeepSeek 配置
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # OpenAI 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Gemini 配置
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class RobotConfig:
    """机器人硬件配置"""
    
    # 串口配置 - 使用udev符号链接（固定路径）
    LEFT_ARM_PORT = "/dev/arm_left"   # 左臂 + 头部 (8个电机)
    RIGHT_ARM_PORT = "/dev/arm_right"  # 右臂 + 底盘 (9个电机)
    
    # 摄像头配置
    MAIN_CAMERA = "/dev/video0"
    HEAD_CAMERA = "/dev/video2"
    RIGHT_CAMERA = "/dev/video4"
    
    # 底盘电机ID (在 RIGHT_ARM_PORT 上)
    WHEEL_LEFT_ID = 7
    WHEEL_BACK_ID = 8
    WHEEL_RIGHT_ID = 9
    
    # 运动参数
    DEFAULT_SPEED = 200      # 默认速度
    TURN_SPEED = 150         # 转弯速度
    MOVE_DURATION = 0.5      # 单次移动时长(秒)


def get_llm():
    """
    根据配置获取 LLM 实例
    支持 DeepSeek / OpenAI / Gemini
    """
    provider = LLMConfig.PROVIDER
    
    if provider == "deepseek":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLMConfig.DEEPSEEK_MODEL,
            api_key=LLMConfig.DEEPSEEK_API_KEY,
            base_url=LLMConfig.DEEPSEEK_BASE_URL,
            temperature=0.7,
        )
    
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLMConfig.OPENAI_MODEL,
            api_key=LLMConfig.OPENAI_API_KEY,
            temperature=0.7,
        )
    
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=LLMConfig.GEMINI_MODEL,
            google_api_key=LLMConfig.GOOGLE_API_KEY,
            temperature=0.7,
        )
    
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def check_config():
    """检查配置是否正确"""
    provider = LLMConfig.PROVIDER
    
    print(f"[配置] LLM 提供商: {provider}")
    
    if provider == "deepseek":
        if not LLMConfig.DEEPSEEK_API_KEY:
            raise ValueError("请在 .env 中设置 DEEPSEEK_API_KEY")
        print(f"[配置] 模型: {LLMConfig.DEEPSEEK_MODEL}")
        print(f"[配置] API URL: {LLMConfig.DEEPSEEK_BASE_URL}")
        
    elif provider == "openai":
        if not LLMConfig.OPENAI_API_KEY:
            raise ValueError("请在 .env 中设置 OPENAI_API_KEY")
        print(f"[配置] 模型: {LLMConfig.OPENAI_MODEL}")
        
    elif provider == "gemini":
        if not LLMConfig.GOOGLE_API_KEY:
            raise ValueError("请在 .env 中设置 GOOGLE_API_KEY")
        print(f"[配置] 模型: {LLMConfig.GEMINI_MODEL}")
    
    print("[配置] ✅ 配置检查通过")
    return True


if __name__ == "__main__":
    check_config()
