import os
import sys
import random
import json
from datetime import datetime, timedelta
import uuid
import pytz

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.settings import SystemConfig, KeyValueSetting

app = create_app()

# 读取配置文件
config_path = os.path.join(os.path.dirname(__file__), 'test_data_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    test_config = json.load(f)

def check_database_tables():
    """检查数据库表是否存在"""
    with app.app_context():
        try:
            # 检查所有必要的表是否存在
            required_tables = [
                'users',
                'edge_devices',
                'tasks',
                'alarms',
                'system_config',
                'key_value_settings'
            ]
            
            for table in required_tables:
                from sqlalchemy import text
                db.session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                print(f"表 {table} 存在")
            
            # 额外检查告警表的字段
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'alarms' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('alarms')]
                if 'alarm_code' in columns:
                    print("告警表结构正确，包含alarm_code字段")
                else:
                    print("警告：告警表结构不正确，不包含alarm_code字段")
                    if 'alarm_id' in columns:
                        print("警告：告警表使用了旧的alarm_id字段，请先运行init_pg_db.py清空并重建表结构")
                        return False
            
            # 检查任务表的字段
            if 'tasks' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('tasks')]
                if 'task_type' in columns:
                    print("任务表结构正确，包含task_type字段")
                else:
                    print("警告：任务表结构不正确，不包含task_type字段")
                    if 'detection_type' in columns:
                        print("警告：任务表使用了旧的detection_type字段，请先运行init_pg_db.py清空并重建表结构")
                        return False
            
            return True
        except Exception as e:
            print(f"数据库表检查失败: {str(e)}")
            print("请先运行 init_db.py 初始化数据库")
            return False

def generate_test_data():
    with app.app_context():
        try:
            # 检查数据库表
            if not check_database_tables():
                return
                
            # 检查数据库连接
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                print("数据库连接成功")
            except Exception as e:
                print(f"数据库连接失败: {str(e)}")
                return
                
            # 查询现有数据
            print("\n=== 现有数据查询 ===")
            existing_devices = EdgeDevice.query.limit(10).all()
            print(f"设备表现有数据（前10条）:")
            for device in existing_devices:
                print(f"  - {device.device_name} (ID: {device.device_id})")
            
            existing_tasks = Task.query.limit(10).all()
            print(f"\n任务表现有数据（前10条）:")
            for task in existing_tasks:
                print(f"  - {task.task_name} ({task.task_type})")
            
            existing_alarms = Alarm.query.limit(10).all()
            print(f"\n告警表现有数据（前10条）:")
            for alarm in existing_alarms:
                print(f"  - {alarm.alarm_code} ({alarm.alarm_type})")
            
            existing_config = SystemConfig.query.first()
            print(f"\n系统配置数据:")
            if existing_config:
                print(f"  - {existing_config.system_name_zh}")
            else:
                print("  - 暂无配置数据")
            
            existing_settings = KeyValueSetting.query.limit(10).all()
            print("\n键值设置数据（前10条）:")
            for setting in existing_settings:
                print(f"  - {setting.key}: {setting.value}")
            print("==================\n")
            
            # 清理已存在的数据
            print("正在清理已存在的数据...")
            db.session.query(Alarm).delete()
            db.session.query(Task).delete()
            db.session.query(EdgeDevice).delete()
            db.session.query(User).delete()  # 添加清理用户数据
            db.session.query(SystemConfig).delete()
            db.session.query(KeyValueSetting).delete()
            db.session.commit()
            print("数据清理完成")
            
            # 生成测试用户数据
            users = []
            test_users = [
                {'username': '管理员', 'password': 'admin123', 'role': 'admin', 'is_admin': True},
                {'username': '操作员A', 'password': 'Operator123#', 'role': 'operator', 'is_admin': False},
                {'username': '巡检员B', 'password': 'Viewer123@321', 'role': 'viewer', 'is_admin': False}
            ]
            
            for user_data in test_users:
                user = User(
                    username=user_data['username'],
                    role=user_data['role'],
                    is_admin=user_data['is_admin'],
                    login_count=random.randint(0, 100),
                    last_login_time=datetime.now().astimezone() - timedelta(days=random.randint(0, 30)),
                    last_login_ip=f"192.168.1.{random.randint(2, 254)}",
                    active=True
                )
                user.set_password(user_data['password'])
                users.append(user)
                db.session.add(user)
            
            db.session.commit()
            
            # 验证用户数据是否成功写入
            saved_users = User.query.all()
            if len(saved_users) == len(test_users):
                print(f"成功生成 {len(saved_users)} 个测试用户")
            else:
                print(f"用户数据写入不完整，预期 {len(test_users)} 个，实际写入 {len(saved_users)} 个")
            
            # 生成测试设备数据
            devices = []
            for device_name in test_config['device_names']:
                device = EdgeDevice(
                    device_name=device_name,
                    ip_address=f"192.168.1.{random.randint(10, 250)}",
                    device_id=str(uuid.uuid4())[:8],
                    secret_key=str(uuid.uuid4())
                )
                devices.append(device)
                db.session.add(device)
            db.session.commit()
            
            # 验证设备数据是否成功写入
            saved_devices = EdgeDevice.query.all()
            if len(saved_devices) == len(devices):
                print(f"成功生成 {len(devices)} 个测试设备")
            else:
                print(f"设备数据写入不完整，预期 {len(devices)} 个，实际写入 {len(saved_devices)} 个")

            # 生成测试任务数据
            tasks = []
            existing_devices = EdgeDevice.query.all()
            if not existing_devices:
                print("错误：没有找到边缘设备数据，请先确保设备数据已生成")
                return
            
            for device in existing_devices:
                # 为每个设备生成1-3个不同类型的监控任务
                for _ in range(random.randint(1, 3)):
                    task_type = random.choice(['压力表读数', '液位计读数', '温度计读数'])
                    task = Task(
                        task_name=f"{device.device_name}_{random.choice(['压力', '液位', '温度'])}监控",
                        well_name=device.device_name,
                        task_type=task_type,
                        camera_ip=device.ip_address,
                        camera_preset=random.randint(1, 10),
                        pressure_range=random.uniform(0, 100),
                        device_id=device.device_id
                    )
                    tasks.append(task)
                    db.session.add(task)
            db.session.commit()

            # 验证任务数据是否成功写入
            saved_tasks = Task.query.all()
            if len(saved_tasks) == len(tasks):
                print(f"成功生成 {len(tasks)} 个测试任务")
            else:
                print(f"任务数据写入不完整，预期 {len(tasks)} 个，实际写入 {len(saved_tasks)} 个")

            # 生成测试告警数据
            alarms = []
            status_choices = ['待确认', '已确认', '已处理']
            
            for device in existing_devices:
                # 获取该设备的任务列表
                device_tasks = [t for t in tasks if t.device_id == device.device_id]  # 使用 device_id 而不是 edge_device
                if not device_tasks:
                    continue
                    
                # 每个设备生成2-5个告警
                for _ in range(random.randint(2, 5)):
                    alarm_time = datetime.now().astimezone() - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    
                    task = random.choice(device_tasks)
                    alarm = Alarm(
                        alarm_code=Alarm.generate_alarm_code(),
                        alarm_type=random.choice(test_config['alarm_types']),
                        device_name=device.device_name,
                        device_id=device.device_id,  # 设备ID字段
                        camera_ip=device.ip_address,
                        alarm_time=alarm_time,
                        last_report_time=alarm_time + timedelta(minutes=random.randint(1, 60)),
                        report_count=random.randint(1, 5),
                        alarm_image=f"/static/test_images/alarm_{device.device_id}_{random.randint(1,10)}.jpg",
                        is_processed=random.choice([True, False]),
                        status=random.choice(status_choices)
                    )
                    
                    if alarm.is_processed:
                        alarm.processed_time = alarm.alarm_time + timedelta(hours=random.randint(1, 24))
                        alarm.is_confirmed = True
                        alarm.confirmed_time = alarm.alarm_time + timedelta(minutes=random.randint(30, 120))
                        alarm.confirm_type = random.choice(['自动', '手动'])
                    
                    alarms.append(alarm)
                    db.session.add(alarm)
            
            db.session.commit()
            
            # 验证告警数据是否成功写入
            saved_alarms = Alarm.query.all()
            if len(saved_alarms) == len(alarms):
                print(f"成功生成 {len(alarms)} 个测试告警")
            else:
                print(f"告警数据写入不完整，预期 {len(alarms)} 个，实际写入 {len(saved_alarms)} 个")

            # 生成系统配置数据
            if not SystemConfig.query.first():
                config = SystemConfig(
                    system_name_zh="智能告警综合管理系统",
                    system_name_en="Intelligent Alarm Management System",
                    company_name="测试油田公司",
                    logo_url="/static/images/logo.png",
                    theme_color="#1890ff"
                )
                db.session.add(config)
                db.session.commit()
                print(f"成功生成系统配置数据")
            
            # 生成默认设置
            settings = [
                {'key': 'alarm_check_interval', 'value': '60', 'description': '告警检查间隔（秒）'},
                {'key': 'auto_process_timeout', 'value': '1800', 'description': '告警自动处理超时时间（秒）'},
                {'key': 'report_threshold', 'value': '3', 'description': '告警上报阈值'},
                {'key': 'camera_timeout', 'value': '30', 'description': '摄像头连接超时（秒）'},
                {'key': 'location_info', 'value': '测试油田区域', 'description': '部署位置信息'}
            ]
            
            for setting in settings:
                kv = KeyValueSetting(
                    key=setting['key'],
                    value=setting['value'],
                    description=setting['description']
                )
                db.session.add(kv)
            
            db.session.commit()
            print(f"成功生成 {len(settings)} 个系统设置")
                
            return True
        except Exception as e:
            print(f"生成测试数据时发生错误: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

if __name__ == "__main__":
    result = generate_test_data()
    if result:
        print("测试数据生成完成！")
    else:
        print("测试数据生成失败！")