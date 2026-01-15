#!/usr/bin/env python
"""
SSH终端下的键盘遥控脚本
使用termios实现非阻塞键盘输入，不需要图形界面
"""

import sys
import os
import time
import select
import termios
import tty

# 添加lerobot路径
sys.path.insert(0, '/home/sunrise/XLeRobot/lerobot/src')

from lerobot.robots.xlerobot import XLerobotConfig, XLerobot
from lerobot.model.SO101Robot import SO101Kinematics

# 按键映射 - 左臂
LEFT_KEYMAP = {
    'shoulder_pan+': 'q', 'shoulder_pan-': 'e',
    'wrist_roll+': 'r', 'wrist_roll-': 'f',
    'gripper+': 't', 'gripper-': 'g',
    'x+': 'w', 'x-': 's', 'y+': 'a', 'y-': 'd',
    'pitch+': 'z', 'pitch-': 'x',
    'reset': 'c',
}

# 按键映射 - 右臂 (使用数字键)
RIGHT_KEYMAP = {
    'shoulder_pan+': '7', 'shoulder_pan-': '9',
    'wrist_roll+': '/', 'wrist_roll-': '*',
    'gripper+': '+', 'gripper-': '-',
    'x+': '8', 'x-': '2', 'y+': '4', 'y-': '6',
    'pitch+': '1', 'pitch-': '3',
    'reset': '0',
}

# 底盘控制
BASE_KEYMAP = {
    'forward': 'i',
    'backward': 'k',
    'left': 'j',
    'right': 'l',
    'rotate_left': 'u',
    'rotate_right': 'o',
}

LEFT_JOINT_MAP = {
    "shoulder_pan": "left_arm_shoulder_pan",
    "shoulder_lift": "left_arm_shoulder_lift",
    "elbow_flex": "left_arm_elbow_flex",
    "wrist_flex": "left_arm_wrist_flex",
    "wrist_roll": "left_arm_wrist_roll",
    "gripper": "left_arm_gripper",
}

RIGHT_JOINT_MAP = {
    "shoulder_pan": "right_arm_shoulder_pan",
    "shoulder_lift": "right_arm_shoulder_lift",
    "elbow_flex": "right_arm_elbow_flex",
    "wrist_flex": "right_arm_wrist_flex",
    "wrist_roll": "right_arm_wrist_roll",
    "gripper": "right_arm_gripper",
}


class TerminalKeyboard:
    """终端键盘输入类，支持SSH"""
    
    def __init__(self):
        self.old_settings = None
        
    def connect(self):
        """设置终端为非阻塞模式"""
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        
    def disconnect(self):
        """恢复终端设置"""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def get_key(self):
        """非阻塞获取按键"""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None


class SimpleTeleopArm:
    """简化的机械臂遥控类"""
    
    def __init__(self, kinematics, joint_map, initial_obs, prefix="left", kp=0.81):
        self.kinematics = kinematics
        self.joint_map = joint_map
        self.prefix = prefix
        self.kp = kp
        
        # 初始位置
        self.target_positions = {
            "shoulder_pan": 0.0,
            "shoulder_lift": 0.0,
            "elbow_flex": 0.0,
            "wrist_flex": 0.0,
            "wrist_roll": 0.0,
            "gripper": 0.0,
        }
        
        # IK参数
        self.current_x = 0.1629
        self.current_y = 0.1131
        self.pitch = 0.0
        self.degree_step = 3
        self.xy_step = 0.0081

    def move_to_zero(self, robot):
        """移动到零位"""
        print(f"[{self.prefix}] 移动到零位...")
        self.target_positions = dict.fromkeys(self.target_positions, 0.0)
        self.current_x = 0.1629
        self.current_y = 0.1131
        self.pitch = 0.0
        action = self.get_action(robot)
        robot.send_action(action)

    def handle_key(self, key, keymap):
        """处理按键"""
        moved = False
        
        if key == keymap.get('shoulder_pan+'):
            self.target_positions["shoulder_pan"] += self.degree_step
            print(f"[{self.prefix}] shoulder_pan: {self.target_positions['shoulder_pan']:.1f}")
        elif key == keymap.get('shoulder_pan-'):
            self.target_positions["shoulder_pan"] -= self.degree_step
            print(f"[{self.prefix}] shoulder_pan: {self.target_positions['shoulder_pan']:.1f}")
        elif key == keymap.get('wrist_roll+'):
            self.target_positions["wrist_roll"] += self.degree_step
            print(f"[{self.prefix}] wrist_roll: {self.target_positions['wrist_roll']:.1f}")
        elif key == keymap.get('wrist_roll-'):
            self.target_positions["wrist_roll"] -= self.degree_step
            print(f"[{self.prefix}] wrist_roll: {self.target_positions['wrist_roll']:.1f}")
        elif key == keymap.get('gripper+'):
            self.target_positions["gripper"] += self.degree_step
            print(f"[{self.prefix}] gripper: {self.target_positions['gripper']:.1f}")
        elif key == keymap.get('gripper-'):
            self.target_positions["gripper"] -= self.degree_step
            print(f"[{self.prefix}] gripper: {self.target_positions['gripper']:.1f}")
        elif key == keymap.get('pitch+'):
            self.pitch += self.degree_step
            print(f"[{self.prefix}] pitch: {self.pitch:.1f}")
        elif key == keymap.get('pitch-'):
            self.pitch -= self.degree_step
            print(f"[{self.prefix}] pitch: {self.pitch:.1f}")
        elif key == keymap.get('x+'):
            self.current_x += self.xy_step
            moved = True
        elif key == keymap.get('x-'):
            self.current_x -= self.xy_step
            moved = True
        elif key == keymap.get('y+'):
            self.current_y += self.xy_step
            moved = True
        elif key == keymap.get('y-'):
            self.current_y -= self.xy_step
            moved = True
            
        if moved:
            try:
                joint2, joint3 = self.kinematics.inverse_kinematics(self.current_x, self.current_y)
                self.target_positions["shoulder_lift"] = joint2
                self.target_positions["elbow_flex"] = joint3
                print(f"[{self.prefix}] x={self.current_x:.4f}, y={self.current_y:.4f}")
            except Exception as e:
                print(f"[{self.prefix}] IK失败: {e}")
                # 回退
                if key == keymap.get('x+'):
                    self.current_x -= self.xy_step
                elif key == keymap.get('x-'):
                    self.current_x += self.xy_step
                elif key == keymap.get('y+'):
                    self.current_y -= self.xy_step
                elif key == keymap.get('y-'):
                    self.current_y += self.xy_step
        
        # 更新wrist_flex
        self.target_positions["wrist_flex"] = (
            -self.target_positions["shoulder_lift"]
            - self.target_positions["elbow_flex"]
            + self.pitch
        )

    def get_action(self, robot):
        """获取P控制动作"""
        obs = robot.get_observation()
        action = {}
        for j in self.target_positions:
            current = obs[f"{self.prefix}_arm_{j}.pos"]
            error = self.target_positions[j] - current
            control = self.kp * error
            action[f"{self.joint_map[j]}.pos"] = current + control
        return action


def print_help():
    """打印帮助信息"""
    print("\n" + "="*60)
    print("XLerobot SSH键盘遥控")
    print("="*60)
    print("\n左臂控制:")
    print("  W/S: 前进/后退 (X轴)")
    print("  A/D: 左/右 (Y轴)")
    print("  Q/E: 肩部旋转")
    print("  R/F: 手腕旋转")
    print("  T/G: 夹爪开/合")
    print("  Z/X: 俯仰角")
    print("  C: 复位")
    print("\n右臂控制 (小键盘):")
    print("  8/2: 前进/后退")
    print("  4/6: 左/右")
    print("  7/9: 肩部旋转")
    print("  ///*: 手腕旋转")
    print("  +/-: 夹爪")
    print("  1/3: 俯仰角")
    print("  0: 复位")
    print("\n底盘控制:")
    print("  I/K: 前进/后退")
    print("  J/L: 左/右平移")
    print("  U/O: 左/右旋转")
    print("\n按 ESC 或 Ctrl+C 退出")
    print("="*60 + "\n")


def main():
    print_help()
    
    # 初始化机器人
    robot_config = XLerobotConfig()
    robot = XLerobot(robot_config)
    
    try:
        robot.connect()
        print("[MAIN] 机器人连接成功!")
    except Exception as e:
        print(f"[MAIN] 连接失败: {e}")
        return
    
    # 初始化键盘
    kb = TerminalKeyboard()
    kb.connect()
    
    # 初始化机械臂控制
    obs = robot.get_observation()
    kin_left = SO101Kinematics()
    kin_right = SO101Kinematics()
    left_arm = SimpleTeleopArm(kin_left, LEFT_JOINT_MAP, obs, prefix="left")
    right_arm = SimpleTeleopArm(kin_right, RIGHT_JOINT_MAP, obs, prefix="right")
    
    # 移动到零位
    left_arm.move_to_zero(robot)
    right_arm.move_to_zero(robot)
    
    # 底盘速度
    base_speed = 0.15
    base_theta = 45
    
    print("\n开始遥控，按ESC退出...\n")
    
    try:
        while True:
            key = kb.get_key()
            
            if key:
                # ESC退出
                if key == '\x1b':
                    print("\n退出遥控...")
                    break
                
                # 左臂控制
                if key == LEFT_KEYMAP.get('reset'):
                    left_arm.move_to_zero(robot)
                else:
                    left_arm.handle_key(key, LEFT_KEYMAP)
                
                # 右臂控制
                if key == RIGHT_KEYMAP.get('reset'):
                    right_arm.move_to_zero(robot)
                else:
                    right_arm.handle_key(key, RIGHT_KEYMAP)
            
            # 获取动作
            left_action = left_arm.get_action(robot)
            right_action = right_arm.get_action(robot)
            
            # 底盘动作
            base_action = {"x.vel": 0.0, "y.vel": 0.0, "theta.vel": 0.0}
            if key:
                if key == BASE_KEYMAP['forward']:
                    base_action["x.vel"] = base_speed
                    print("[BASE] 前进")
                elif key == BASE_KEYMAP['backward']:
                    base_action["x.vel"] = -base_speed
                    print("[BASE] 后退")
                elif key == BASE_KEYMAP['left']:
                    base_action["y.vel"] = base_speed
                    print("[BASE] 左移")
                elif key == BASE_KEYMAP['right']:
                    base_action["y.vel"] = -base_speed
                    print("[BASE] 右移")
                elif key == BASE_KEYMAP['rotate_left']:
                    base_action["theta.vel"] = base_theta
                    print("[BASE] 左转")
                elif key == BASE_KEYMAP['rotate_right']:
                    base_action["theta.vel"] = -base_theta
                    print("[BASE] 右转")
            
            # 合并并发送动作
            action = {**left_action, **right_action, **base_action}
            robot.send_action(action)
            
            time.sleep(0.02)  # 50Hz
            
    except KeyboardInterrupt:
        print("\n\nCtrl+C 退出...")
    finally:
        kb.disconnect()
        robot.disconnect()
        print("遥控结束。")


if __name__ == "__main__":
    main()
