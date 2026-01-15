#!/usr/bin/env python3
"""
XLerobot LLM 移动 Agent
使用 LangChain + DeepSeek/OpenAI/Gemini 控制机器人底盘移动

使用方法:
    cd /home/sunrise/XLeRobot
    conda activate xlerobot
    python llm_move_agent/move_agent.py
"""

import sys
import warnings
import cv2
import base64
from pathlib import Path

# 忽略 langgraph deprecation 警告，看着别扭
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*deprecated.*")

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from llm_move_agent.config import get_llm, check_config, RobotConfig
from llm_move_agent.tools import (
    ALL_TOOLS, 
    WheelController, 
    set_wheel_controller
)


# 系统提示词
SYSTEM_PROMPT = """你是小如，一个移动机器人。

能力：move_forward, move_backward, turn_left, turn_right, strafe_left, strafe_right, stop_robot

移动参数：
- 前进/后退：每步约10cm
- 转向：每步约13度
  - 转45度 ≈ 3-4步
  - 转90度 ≈ 7步
  - 转180度 ≈ 14步
  - 转一圈360度 ≈ 28步

规则：
1. 执行用户指令，调用对应工具
2. 回复简短，10字以内，如"好的"、"已前进3步"
3. 直接执行，不要解释
"""


class MoveAgent:
    """底盘移动 Agent"""
    
    def __init__(self, use_real_robot: bool = True):
        """
        初始化 Agent
        
        Args:
            use_real_robot: 是否连接真实机器人，False 则为模拟模式
        """
        self.use_real_robot = use_real_robot
        self.robot = None
        self.motors_bus = None
        self.camera = None
        
        # 检查配置
        check_config()
        
        # 初始化 LLM
        print("[Agent] 初始化 LLM...")
        self.llm = get_llm()
        
        # 初始化工具
        self.tools = ALL_TOOLS
        
        # 创建 Agent
        self._create_agent()
        
        # 初始化机器人
        if use_real_robot:
            self._init_robot()
        else:
            self._init_mock()
    
    def _create_agent(self):
        """创建 LangChain Agent"""
        # 使用 langgraph 的 react agent
        self.agent = create_react_agent(
            self.llm, 
            self.tools,
            prompt=SYSTEM_PROMPT,
        )
        
        print("[Agent] ✅ Agent 创建完成")
    
    def _init_robot(self):
        """初始化真实机器人"""
        print("[Agent] 连接机器人...")
        
        try:
            from lerobot.motors.feetech import FeetechMotorsBus
            from lerobot.motors.motors_bus import Motor, MotorNormMode
            
            # 创建电机配置
            motors = {
                "wheel_left": Motor(id=RobotConfig.WHEEL_LEFT_ID, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
                "wheel_back": Motor(id=RobotConfig.WHEEL_BACK_ID, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
                "wheel_right": Motor(id=RobotConfig.WHEEL_RIGHT_ID, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
            }
            
            # 尝试连接，最多重试3次
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.motors_bus = FeetechMotorsBus(
                        port=RobotConfig.RIGHT_ARM_PORT,
                        motors=motors,
                    )
                    self.motors_bus.connect()
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[Agent] 连接尝试 {attempt + 1} 失败，重试...")
                        import time
                        time.sleep(0.5)
                    else:
                        raise e
            
            # 创建轮子控制器
            # 注意: 配置中的变量名与实际轮子位置对应关系:
            # WHEEL_LEFT_ID(7) -> 实际是右轮
            # WHEEL_BACK_ID(8) -> 实际是前轮  
            # WHEEL_RIGHT_ID(9) -> 实际是左轮
            wheel_controller = WheelController(
                self.motors_bus,
                right_id=RobotConfig.WHEEL_LEFT_ID,   # ID7 实际是右轮
                front_id=RobotConfig.WHEEL_BACK_ID,   # ID8 实际是前轮
                left_id=RobotConfig.WHEEL_RIGHT_ID,   # ID9 实际是左轮
            )
            set_wheel_controller(wheel_controller)
            
            print("[Agent] ✅ 机器人连接成功")
            
        except Exception as e:
            print(f"[Agent] ⚠️ 机器人连接失败: {e}")
            print("[Agent] 切换到模拟模式")
            self._init_mock()
    
    def _init_mock(self):
        """初始化模拟模式"""
        print("[Agent] 使用模拟模式 (不连接真实机器人)")
        
        class MockWheelController:
            last_error = None
            
            def move_forward(self, *args, **kwargs):
                print("[模拟] 前进")
                return True
            def move_backward(self, *args, **kwargs):
                print("[模拟] 后退")
                return True
            def turn_left(self, *args, **kwargs):
                print("[模拟] 左转")
                return True
            def turn_right(self, *args, **kwargs):
                print("[模拟] 右转")
                return True
            def strafe_left(self, *args, **kwargs):
                print("[模拟] 左平移")
                return True
            def strafe_right(self, *args, **kwargs):
                print("[模拟] 右平移")
                return True
            def stop(self):
                print("[模拟] 停止")
                return True
        
        set_wheel_controller(MockWheelController())
        print("[Agent] ✅ 模拟模式初始化完成")
    
    def init_camera(self):
        """初始化摄像头 (可选)"""
        try:
            self.camera = cv2.VideoCapture(RobotConfig.MAIN_CAMERA)
            if self.camera.isOpened():
                print(f"[Agent] ✅ 摄像头已打开: {RobotConfig.MAIN_CAMERA}")
            else:
                print("[Agent] ⚠️ 摄像头打开失败")
                self.camera = None
        except Exception as e:
            print(f"[Agent] ⚠️ 摄像头初始化失败: {e}")
            self.camera = None
    
    def get_camera_image(self) -> str:
        """获取摄像头图像的 base64 编码"""
        if self.camera is None:
            return None
        
        ret, frame = self.camera.read()
        if not ret:
            return None
        
        # 压缩图像
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return base64.b64encode(buffer).decode('utf-8')
    
    def run(self, task: str) -> str:
        """
        执行任务
        
        Args:
            task: 用户指令
            
        Returns:
            执行结果
        """
        print(f"\n[Agent] 收到任务: {task}")
        print("-" * 50)
        
        try:
            # 使用 langgraph agent
            messages = [HumanMessage(content=task)]
            result = self.agent.invoke({"messages": messages})
            
            # 获取最后一条消息作为结果
            if result.get("messages"):
                last_msg = result["messages"][-1]
                return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            return "任务执行完成"
        except Exception as e:
            return f"执行出错: {e}"
    
    def chat(self):
        """交互式对话模式"""
        print("\n" + "=" * 50)
        print("XLerobot 移动 Agent")
        print("输入指令控制机器人移动，输入 'quit' 退出")
        print("=" * 50 + "\n")
        
        while True:
            try:
                user_input = input("你: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                    print("再见！")
                    break
                
                response = self.run(user_input)
                print(f"\n机器人: {response}\n")
                
            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                print(f"错误: {e}")
    
    def cleanup(self):
        """清理资源"""
        if self.camera:
            self.camera.release()
        if self.motors_bus:
            try:
                # 停止轮子
                values = {
                    "wheel_left": 0,
                    "wheel_back": 0, 
                    "wheel_right": 0,
                }
                self.motors_bus.sync_write("Goal_Velocity", values, normalize=False)
                
                # 释放力矩（让轮子可以自由转动）
                self.motors_bus.sync_write("Torque_Enable", values, normalize=False)
                
                self.motors_bus.disconnect()
            except Exception as e:
                print(f"[Agent] 清理时出错: {e}")
        print("[Agent] 资源已清理")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="XLerobot LLM 移动 Agent")
    parser.add_argument("--mock", action="store_true", 
                       help="使用模拟模式，不连接真实机器人")
    parser.add_argument("--task", type=str, default=None,
                       help="直接执行指定任务，不进入交互模式")
    args = parser.parse_args()
    
    # 创建 Agent
    agent = MoveAgent(use_real_robot=not args.mock)
    
    try:
        if args.task:
            # 执行单个任务
            result = agent.run(args.task)
            print(f"\n结果: {result}")
        else:
            # 交互模式
            agent.chat()
    finally:
        agent.cleanup()


if __name__ == "__main__":
    main()
