import shutil
import os

def batch_copy_images():
    # 配置参数
    src_file = "E:\\20_Coding_交付项目\\320_oilfield_gateway\\app\\static\\alarms\\test_image_1.jpg"   # 源文件路径
    output_dir = "./"        # 输出目录
    
    # 检查源文件是否存在
    if not os.path.exists(src_file):
        print(f"错误：源文件 {src_file} 不存在！")
        return
    
    # 创建输出目录（自动创建不存在的目录）
    os.makedirs(output_dir, exist_ok=True)
    
    # 批量复制并重命名
    for i in range(2, 101):  # 从2到100
        # 格式化文件名（保持三位数格式，如 test_image_002.jpg）
        new_name = f"test_image_{i:03d}.jpg"
        dst_path = os.path.join(output_dir, new_name)
        
        try:
            # 执行复制操作（保留元数据）
            shutil.copy2(src_file, dst_path)
            print(f"✅ 成功创建: {new_name} ({i}/100)")
            
        except Exception as e:
            print(f"❌ 创建失败: {new_name} | 错误原因: {str(e)}")

# 执行批量复制
if __name__ == "__main__":
    print("开始批量复制文件...")
    batch_copy_images()
    print("操作完成！")