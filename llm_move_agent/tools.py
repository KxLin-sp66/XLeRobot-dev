"""
机器人控制工具定义
这些工具会被 LLM Agent 调用来控制机器人
"""

import time
from typing import Optional
from langchain_core.tools import tool

# 全局变量存储机器人实例
_robot = None
_servo_controller = None


def set_robot(robot):
    """设置机器人实例"""
    global _robot
    _robot = robot


def set_servo_controller(controller):
    """设置伺服控制器"""
    global _servo_controller
    _servo_controller = controller


class WheelController:
    """
    底盘轮子控制器
    三轮全向底盘: 右轮(ID7), 前轮(ID8), 左轮(ID9)
    
    布局 (俯视图):
          前轮(ID8)
            ○
           / \
          /   \
    左轮○     ○右轮
     (ID9)   (ID7)
    """
    
    def __init__(self, motors_bus, right_id=7, front_id=8, left_id=9):
        self.bus = motors_bus
        self.right_id = right_id
        self.front_id = front_id
        self.left_id = left_id
        self.default_speed = 600      # 默认速度 (调大)
        self.turn_duration = 1.0      # 转弯时长 (调大一倍)
        self.move_duration = 2.0      # 移动时长 (调大一倍)
        
        # 电机名称映射 - 与 motors 字典中的 key 对应
        self.motor_id7 = "wheel_left"   # ID7 右轮
        self.motor_id8 = "wheel_back"   # ID8 前轮
        self.motor_id9 = "wheel_right"  # ID9 左轮
        
        # 记录最后一次错误
        self.last_error = None
    
    def set_wheel_speeds(self, id7_speed: int, id8_speed: int, id9_speed: int) -> bool:
        """
        设置三个轮子的速度，返回是否成功
        
        Args:
            id7_speed: ID7电机(右轮)速度
            id8_speed: ID8电机(前轮)速度
            id9_speed: ID9电机(左轮)速度
        """
        try:
            values = {
                self.motor_id7: id7_speed,  # ID7 右轮
                self.motor_id8: id8_speed,  # ID8 前轮
                self.motor_id9: id9_speed,  # ID9 左轮
            }
            self.bus.sync_write("Goal_Velocity", values, normalize=False)
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[轮子] 设置速度失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止所有轮子"""
        return self.set_wheel_speeds(0, 0, 0)
    
    def move_forward(self, speed: int = None, duration: float = None) -> bool:
        """
        前进
        ID7(右轮)正转, ID8(前轮)停止, ID9(左轮)反转
        """
        speed = speed or self.default_speed
        duration = duration or self.move_duration
        success = self.set_wheel_speeds(speed, 0, -speed)
        time.sleep(duration)
        self.stop()
        return success
    
    def move_backward(self, speed: int = None, duration: float = None) -> bool:
        """
        后退
        ID7(右轮)反转, ID8(前轮)停止, ID9(左轮)正转
        """
        speed = speed or self.default_speed
        duration = duration or self.move_duration
        success = self.set_wheel_speeds(-speed, 0, speed)
        time.sleep(duration)
        self.stop()
        return success
    
    def turn_left(self, speed: int = None, duration: float = None) -> bool:
        """
        左转 (逆时针)
        所有轮子同向正转
        """
        speed = speed or self.default_speed
        duration = duration or self.turn_duration
        success = self.set_wheel_speeds(speed, speed, speed)
        time.sleep(duration)
        self.stop()
        return success
    
    def turn_right(self, speed: int = None, duration: float = None) -> bool:
        """
        右转 (顺时针)
        所有轮子同向反转
        """
        speed = speed or self.default_speed
        duration = duration or self.turn_duration
        success = self.set_wheel_speeds(-speed, -speed, -speed)
        time.sleep(duration)
        self.stop()
        return success
    
    def strafe_left(self, speed: int = None, duration: float = 0.5) -> bool:
        """左平移"""
        speed = speed or self.default_speed
        success = self.set_wheel_speeds(-speed // 2, speed, -speed // 2)
        time.sleep(duration)
        self.stop()
        return success
    
    def strafe_right(self, speed: int = None, duration: float = 0.5) -> bool:
        """右平移"""
        speed = speed or self.default_speed
        success = self.set_wheel_speeds(speed // 2, -speed, speed // 2)
        time.sleep(duration)
        self.stop()
        return success


# 全局轮子控制器
_wheel_controller: Optional[WheelController] = None


def set_wheel_controller(controller: WheelController):
    """设置轮子控制器"""
    global _wheel_controller
    _wheel_controller = controller


def get_wheel_controller() -> WheelController:
    """获取轮子控制器"""
    if _wheel_controller is None:
        raise RuntimeError("轮子控制器未初始化")
    return _wheel_controller


# ============ LangChain 工具定义 ============

@tool
def move_forward(steps: int = 1) -> str:
    """
    控制机器人向前移动。
    
    Args:
        steps: 移动步数，每步约0.5秒，默认1步
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(steps):
            if controller.move_forward():
                success_count += 1
            else:
                return f"❌ 前进失败: 第{i+1}步执行出错 - {controller.last_error}"
        return f"✅ 机器人向前移动了 {success_count} 步"
    except Exception as e:
        return f"❌ 前进失败: {e}"


@tool
def move_backward(steps: int = 1) -> str:
    """
    控制机器人向后移动。
    
    Args:
        steps: 移动步数，每步约0.5秒，默认1步
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(steps):
            if controller.move_backward():
                success_count += 1
            else:
                return f"❌ 后退失败: 第{i+1}步执行出错 - {controller.last_error}"
        return f"✅ 机器人向后移动了 {success_count} 步"
    except Exception as e:
        return f"❌ 后退失败: {e}"


@tool
def turn_left(times: int = 1) -> str:
    """
    控制机器人向左转。
    
    Args:
        times: 转动次数，默认1次
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(times):
            if controller.turn_left():
                success_count += 1
            else:
                return f"❌ 左转失败: 第{i+1}次执行出错 - {controller.last_error}"
        return f"✅ 机器人向左转了 {success_count} 次"
    except Exception as e:
        return f"❌ 左转失败: {e}"


@tool
def turn_right(times: int = 1) -> str:
    """
    控制机器人向右转。
    
    Args:
        times: 转动次数，默认1次
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(times):
            if controller.turn_right():
                success_count += 1
            else:
                return f"❌ 右转失败: 第{i+1}次执行出错 - {controller.last_error}"
        return f"✅ 机器人向右转了 {success_count} 次"
    except Exception as e:
        return f"❌ 右转失败: {e}"


@tool
def strafe_left(steps: int = 1) -> str:
    """
    控制机器人向左平移（横向移动）。
    
    Args:
        steps: 移动步数，默认1步
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(steps):
            if controller.strafe_left():
                success_count += 1
            else:
                return f"❌ 左平移失败: 第{i+1}步执行出错 - {controller.last_error}"
        return f"✅ 机器人向左平移了 {success_count} 步"
    except Exception as e:
        return f"❌ 左平移失败: {e}"


@tool
def strafe_right(steps: int = 1) -> str:
    """
    控制机器人向右平移（横向移动）。
    
    Args:
        steps: 移动步数，默认1步
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        success_count = 0
        for i in range(steps):
            if controller.strafe_right():
                success_count += 1
            else:
                return f"❌ 右平移失败: 第{i+1}步执行出错 - {controller.last_error}"
        return f"✅ 机器人向右平移了 {success_count} 步"
    except Exception as e:
        return f"❌ 右平移失败: {e}"


@tool
def stop_robot() -> str:
    """
    停止机器人所有运动。
    
    Returns:
        执行结果描述
    """
    try:
        controller = get_wheel_controller()
        if controller.stop():
            return "✅ 机器人已停止"
        else:
            return f"❌ 停止失败: {controller.last_error}"
    except Exception as e:
        return f"❌ 停止失败: {e}"


@tool
def finish_task() -> str:
    """
    完成当前任务，结束执行。
    当你认为任务已经完成时调用此工具。
    
    Returns:
        任务完成确认
    """
    return "🎉 任务完成！"


# 所有可用工具列表
ALL_TOOLS = [
    move_forward,
    move_backward,
    turn_left,
    turn_right,
    strafe_left,
    strafe_right,
    stop_robot,
    finish_task,
]
