#!/usr/bin/env python3
"""
测试 LLM 连接
先运行这个脚本确认 API 配置正确
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_llm():
    """测试 LLM 连接"""
    print("=" * 50)
    print("测试 LLM 连接")
    print("=" * 50)
    
    try:
        from llm_move_agent.config import get_llm, check_config
        
        # 检查配置
        check_config()
        
        # 获取 LLM
        print("\n[测试] 初始化 LLM...")
        llm = get_llm()
        
        # 测试调用
        print("[测试] 发送测试消息...")
        response = llm.invoke("你好，请用一句话介绍你自己")
        
        print(f"\n[响应] {response.content}")
        print("\n✅ LLM 连接测试成功！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_llm()
