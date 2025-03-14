import os
import sys
from sqlalchemy import create_engine, inspect, event, text  # 添加 text 导入
from sqlalchemy.exc import OperationalError
import pandas as pd
from time import sleep

# 添加项目根目录到 Python 路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

# 数据库连接配置
instance_path = os.path.join(root_dir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
DB_URI = 'sqlite:///' + os.path.join(instance_path, 'alarms.db')

def connect_with_retry(max_attempts=3):
    """带重试机制的数据库连接"""
    attempt = 0
    while attempt < max_attempts:
        try:
            engine = create_engine(DB_URI)
            # 测试连接
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))  # 使用 text() 函数包装 SQL
            return engine
        except OperationalError as e:
            attempt += 1
            if attempt == max_attempts:
                raise
            print(f"连接失败，{max_attempts - attempt}次重试机会...")
            sleep(1)

def check_alarm_data():
    try:
        # 创建数据库连接
        engine = connect_with_retry()
        
        # 获取所有表名
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print("\n=== 数据库中的表 ===")
        for table in tables:
            print(f"\n表名: {table}")
            try:
                # 打印每个表的列信息
                columns = inspector.get_columns(table)
                print("列信息:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
                
                # 打印表中的数据数量，使用 text() 包装 SQL
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"数据量: {count} 条")
            except Exception as table_error:
                print(f"读取表 {table} 信息时出错: {str(table_error)}")
            print("-" * 50)
            
    except Exception as e:
        print(f"查询出错: {str(e)}")
        print(f"数据库路径: {os.path.join(instance_path, 'alarms.db')}")
        if not os.path.exists(os.path.join(instance_path, 'alarms.db')):
            print("错误: 数据库文件不存在！")

if __name__ == "__main__":
    check_alarm_data()