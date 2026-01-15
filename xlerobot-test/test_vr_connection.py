#!/usr/bin/env python3
"""
测试VR连接 - 只测试VR数据接收，不连接机械臂
"""

import sys
import os

# 强制无缓冲输出
os.environ['PYTHONUNBUFFERED'] = '1'

import asyncio
import threading
import time

# 添加XLeVR路径
sys.path.insert(0, '/home/sunrise/XLeRobot/XLeVR')

from vr_monitor import VRMonitor

def main():
    print("="*50)
    print("VR连接测试")
    print("="*50)
    
    # 初始化VR Monitor
    print("\n🔧 初始化VR Monitor...")
    vr_monitor = VRMonitor()
    
    if not vr_monitor.initialize():
        print("❌ VR Monitor初始化失败")
        return
    
    print("✅ VR Monitor初始化成功")
    
    # 启动VR监控线程
    print("🚀 启动VR监控...")
    vr_thread = threading.Thread(
        target=lambda: asyncio.run(vr_monitor.start_monitoring()), 
        daemon=True
    )
    vr_thread.start()
    
    # 等待服务启动
    time.sleep(3)
    
    print("\n" + "="*50)
    print("现在请在Pico浏览器中访问显示的HTTPS地址")
    print("然后点击'Enter VR'进入VR模式")
    print("按 Ctrl+C 退出")
    print("="*50 + "\n")
    
    # 主循环 - 检查VR数据
    try:
        count = 0
        while True:
            dual_goals = vr_monitor.get_latest_goal_nowait()
            
            if dual_goals:
                left_goal = dual_goals.get("left")
                right_goal = dual_goals.get("right")
                has_left = dual_goals.get("has_left", False)
                has_right = dual_goals.get("has_right", False)
                
                count += 1
                if count % 30 == 0:  # 每30次打印一次
                    print(f"\n[{count}] VR数据状态:")
                    print(f"  has_left: {has_left}, has_right: {has_right}")
                    
                    if left_goal:
                        pos = left_goal.target_position if hasattr(left_goal, 'target_position') else None
                        print(f"  左手柄位置: {pos}")
                    else:
                        print(f"  左手柄: None")
                    
                    if right_goal:
                        pos = right_goal.target_position if hasattr(right_goal, 'target_position') else None
                        print(f"  右手柄位置: {pos}")
                    else:
                        print(f"  右手柄: None")
            else:
                if count % 100 == 0:
                    print("等待VR连接...")
                count += 1
            
            time.sleep(0.033)  # ~30Hz
            
    except KeyboardInterrupt:
        print("\n\n退出测试")

if __name__ == "__main__":
    main()
