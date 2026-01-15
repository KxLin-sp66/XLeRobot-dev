#!/usr/bin/env python
"""
摄像头测试脚本
测试所有连接的摄像头，显示画面
"""

import cv2
import sys

def test_single_camera(device_path, window_name="Camera"):
    """测试单个摄像头"""
    print(f"\n测试摄像头: {device_path}")
    
    cap = cv2.VideoCapture(device_path)
    if not cap.isOpened():
        print(f"  ❌ 无法打开 {device_path}")
        return False
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # 读取实际参数
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"  ✅ 打开成功: {width}x{height} @ {fps}fps")
    print(f"  按 'q' 退出, 按 'n' 测试下一个摄像头")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"  ❌ 读取帧失败")
            break
        
        # 在画面上显示信息
        cv2.putText(frame, f"{device_path} - {width}x{height}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' to quit, 'n' for next", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.imshow(window_name, frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            cap.release()
            return 'quit'
        elif key == ord('n'):
            break
    
    cap.release()
    return True

def test_all_cameras():
    """测试所有摄像头"""
    print("="*50)
    print("摄像头测试工具")
    print("="*50)
    
    # 使用udev符号链接（固定路径）
    cameras = [
        ("/dev/camera_right", "右臂摄像头"),
        ("/dev/camera_left", "左臂摄像头"),
        ("/dev/camera_head", "头部摄像头"),
    ]
    
    for cam_path, cam_name in cameras:
        print(f"\n--- {cam_name} ---")
        result = test_single_camera(cam_path, cam_name)
        if result == 'quit':
            break
    
    cv2.destroyAllWindows()
    print("\n测试完成!")

def test_multi_view():
    """同时显示多个摄像头"""
    print("="*50)
    print("多摄像头同时显示")
    print("="*50)
    
    # 使用udev符号链接（固定路径）
    cameras = [
        ("/dev/camera_right", "右臂"),
        ("/dev/camera_left", "左臂"),
        ("/dev/camera_head", "头部"),
    ]
    caps = []
    
    for cam_path, cam_name in cameras:
        cap = cv2.VideoCapture(cam_path)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            caps.append((cam_name, cap))
            print(f"  ✅ {cam_name} ({cam_path}) 打开成功")
        else:
            print(f"  ❌ {cam_name} ({cam_path}) 打开失败")
    
    if not caps:
        print("没有可用的摄像头!")
        return
    
    print("\n按 'q' 退出")
    
    import numpy as np
    
    while True:
        frames = []
        for cam_path, cap in caps:
            ret, frame = cap.read()
            if ret:
                # 添加标签
                cv2.putText(frame, cam_path, (5, 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                frames.append(frame)
        
        if frames:
            # 横向拼接所有画面
            combined = np.hstack(frames)
            cv2.imshow("All Cameras", combined)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    for _, cap in caps:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        test_multi_view()
    else:
        test_all_cameras()
