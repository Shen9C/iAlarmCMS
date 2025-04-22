import os
import sys
import random
import json
from datetime import datetime, timedelta
import uuid

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.oil_wells import OilWell
from app.models.settings import SystemConfig, KeyValueSetting

app = create_app()

# 读取配置文件
config_path = os.path.join(os.path.dirname(__file__), 'test_data_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    test_config = json.load(f)

# 辅助函数：生成任务编号
def generate_task_code(well_code=None, task_type=None):
    """生成任务编号，基于油井编码和任务类型"""
    if not well_code:
        return f"TASK_UNKNOWN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 任务类型的前缀映射
    prefix_map = {
        "启停检测": "QT",
        "皮带检测": "PD", 
        "毛辫子检测": "MBZ",
        "压力表检测": "YLB",
        "井口泄漏检测": "JK",
        "烟火检测": "F"
    }
    
    # 获取任务类型前缀
    type_prefix = prefix_map.get(task_type, "TASK")
    
    # 生成唯一标识符
    unique_suffix = f"{datetime.now().strftime('%m%d')}_{random.randint(1000, 9999)}"
    
    return f"TSK_{well_code}_{type_prefix}_{unique_suffix}"

# 辅助函数：生成告警编号
def generate_alarm_code(well_code=None, alarm_type=None):
    """生成告警编号，基于油井编码和故障类型映射"""
    if not well_code:
        return f"ALM_UNKNOWN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 获取油井对应的故障码映射
    well_code_upper = well_code.upper()
    fault_codes = test_config.get('well_code_fault_mapping', {}).get(well_code_upper, [])
    
    # 如果没有该油井的故障码映射，使用默认格式
    if not fault_codes:
        return f"{well_code}_ALM"
    
    # 如果提供了告警类型，尝试选择与之匹配的故障码
    if alarm_type:
        # 根据告警类型前缀尝试匹配对应的故障码
        prefix_map = {
            "启停检测": "QT",
            "皮带检测": "PD", 
            "毛辫子检测": "MBZ",
            "压力表检测": "YLB",
            "井口泄漏检测": "JK",
            "烟火检测": "F"
        }
        
        prefix = prefix_map.get(alarm_type)
        matching_codes = [code for code in fault_codes if prefix and code.startswith(prefix)]
        
        # 如果找到匹配的故障码，随机选择一个
        if matching_codes:
            selected_code = random.choice(matching_codes)
            return f"{well_code}_{selected_code}"
    
    # 如果没有找到匹配的故障码或没有提供告警类型，随机选择一个故障码
    selected_code = random.choice(fault_codes)
    return f"{well_code}_{selected_code}"

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
                'oil_wells',  # 添加油井表检查
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
            
            # 检查油井表的字段
            if 'oil_wells' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('oil_wells')]
                if 'well_code' in columns:
                    print("油井表结构正确，包含well_code字段")
                else:
                    print("警告：油井表结构不正确，不包含well_code字段")
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
            
            existing_wells = OilWell.query.limit(10).all()
            print(f"\n油井表现有数据（前10条）:")
            for well in existing_wells:
                print(f"  - {well.well_name} (编号: {well.well_code})")
            
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
            db.session.query(OilWell).delete()  # 先删除油井表，因为任务表有外键引用
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
                    active=True
                )
                # 设置密码
                user.set_password(user_data['password'])
                # 设置其他属性
                user.login_count = random.randint(0, 100)
                user.last_login_time = datetime.now() - timedelta(days=random.randint(0, 30))
                user.last_login_ip = f"192.168.1.{random.randint(2, 254)}"
                
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
                # 生成一个1-5内的随机数来决定设备状态
                status_num = random.randint(1, 5)
                if status_num == 1:
                    status = 'error'  # 20%的设备处于错误状态
                elif status_num <= 3:
                    status = 'offline'  # 40%的设备处于离线状态
                else:
                    status = 'online'  # 40%的设备处于在线状态
                
                device = EdgeDevice(
                    device_name=device_name,
                    ip_address=f"192.168.1.{random.randint(10, 250)}",
                    device_id=str(uuid.uuid4())[:8],
                    status=status
                )
                
                # 如果设备是在线状态，设置一个最近的认证时间
                if status == 'online':
                    device.last_auth_time = datetime.now() - timedelta(minutes=random.randint(5, 55))
                elif status == 'offline':
                    # 离线设备可能在过去有认证记录
                    if random.random() > 0.3:  # 70%的离线设备有历史认证记录
                        device.last_auth_time = datetime.now() - timedelta(days=random.randint(1, 30))
                
                devices.append(device)
                db.session.add(device)
            
            db.session.commit()
            print(f"成功生成 {len(devices)} 个测试设备")
            
            # 生成油井数据
            oil_wells = []
            well_codes = [f"WELL{str(i).zfill(3)}" for i in range(1, len(test_config['oil_well_names']) + 1)]
            
            for idx, well_name in enumerate(test_config['oil_well_names']):
                well_code = well_codes[idx]
                oil_well = OilWell(
                    well_code=well_code,
                    well_name=well_name,
                    location=f"测试区域-{chr(65 + random.randint(0, 5))}{random.randint(1, 10)}",
                    status=random.choice(['正常', '维护中', '停机']),
                    description=f"{well_name}的描述信息，这是一个测试油井。",
                    created_at=datetime.now() - timedelta(days=random.randint(30, 365))
                )
                oil_wells.append(oil_well)
                db.session.add(oil_well)
            
            db.session.commit()
            
            # 验证油井数据
            saved_wells = OilWell.query.all()
            if len(saved_wells) == len(test_config['oil_well_names']):
                print(f"成功生成 {len(saved_wells)} 个油井数据")
            else:
                print(f"油井数据写入不完整，预期 {len(test_config['oil_well_names'])} 个，实际写入 {len(saved_wells)} 个")
            
            # 生成测试任务数据
            tasks = []
            for i in range(int(test_config['task_count'])):
                # 随机选择一个设备
                device = random.choice(devices)
                # 随机选择一个油井
                oil_well = random.choice(oil_wells)
                
                # 随机选择一个任务类型
                task_type = random.choice(test_config['task_types'])
                
                # 生成摄像头相关信息
                camera_ip = f"192.168.1.{random.randint(2, 254)}"
                camera_preset = random.randint(1, 8)
                # 添加摄像头用户名和密码的随机数据
                camera_username = random.choice(test_config.get('camera_usernames', ["admin", "operator", "hikvision"]))
                camera_password = random.choice(test_config.get('camera_passwords', ["admin123", "Admin@123", "123456"]))
                
                # 生成压力表量程
                pressure_range = random.choice([10.0, 16.0, 25.0, 40.0, 60.0])
                
                # 生成任务描述
                task_description = f"{task_type}任务：{oil_well.well_name}（{oil_well.well_code}）- {device.device_name}"
                
                # 生成任务编码
                task_code = generate_task_code(oil_well.well_code, task_type)
                
                # 创建任务对象
                task = Task(
                    task_code=task_code,
                    task_name=f"{oil_well.well_name}-{oil_well.well_code}-{task_type}",
                    well_name=oil_well.well_name,
                    well_code=oil_well.well_code,
                    task_type=task_type,
                    camera_ip=camera_ip,
                    camera_preset=camera_preset,
                    camera_username=camera_username,
                    camera_password=camera_password,
                    pressure_range=pressure_range,
                    task_description=task_description,
                    device_id=device.device_id
                )
                tasks.append(task)
                db.session.add(task)
            
            db.session.commit()
            
            # 验证任务数据
            saved_tasks = Task.query.all()
            if len(saved_tasks) == int(test_config['task_count']):
                print(f"成功生成 {len(saved_tasks)} 个任务数据")
            else:
                print(f"任务数据写入不完整，预期 {int(test_config['task_count'])} 个，实际写入 {len(saved_tasks)} 个")
            
            # 生成告警数据
            alarms = []
            for _ in range(100):  # 生成100个告警
                # 随机选择一个油井
                oil_well = random.choice(oil_wells)
                # 随机选择告警类型
                alarm_type = random.choice(test_config['alarm_types'])
                # 随机选择设备
                device = random.choice(devices)
                
                # 使用新的状态字段：is_processed, is_confirmed
                processed_status = random.choices(
                    ['待处理', '已确认', '已处理'], 
                    weights=[0.5, 0.3, 0.2], 
                    k=1
                )[0]
                
                is_processed = False
                processed_time = None
                processed_by = None
                
                is_confirmed = False
                confirmed_at = None
                confirmed_by = None
                confirmation_type = None
                description = None
                
                # 根据状态设置相关信息
                if processed_status == '已确认':
                    is_confirmed = True
                    confirmed_at = datetime.now() - timedelta(hours=random.randint(1, 48))
                    confirmed_by = random.choice(users).username
                    confirmation_type = random.choice(test_config['confirm_types'])['confirm_type']
                    description = f"确认备注：这是{confirmation_type}告警"
                
                if processed_status == '已处理':
                    is_processed = True
                    is_confirmed = True
                    processed_time = datetime.now() - timedelta(hours=random.randint(1, 24))
                    processed_by = random.choice(users).username
                    confirmed_at = processed_time - timedelta(hours=random.randint(1, 24))
                    confirmed_by = processed_by if random.random() > 0.5 else random.choice(users).username
                    confirmation_type = random.choice(test_config['confirm_types'])['confirm_type']
                    description = f"处理备注：{confirmation_type}告警已处理完成"
                
                # 生成告警时间
                alarm_time = datetime.now() - timedelta(days=random.randint(0, 30))
                
                # 创建告警对象，确保包含正确的油井编码
                alarm = Alarm(
                    alarm_code=generate_alarm_code(oil_well.well_code, alarm_type),
                    alarm_type=alarm_type,
                    device_id=device.device_id,
                    device_name=device.device_name,
                    well_name=oil_well.well_name,
                    well_code=oil_well.well_code,
                    camera_ip=f"192.168.1.{random.randint(10, 250)}",
                    alarm_time=alarm_time,
                    last_report_time=alarm_time + timedelta(minutes=random.randint(5, 60)),
                    report_count=random.randint(1, 10),
                    alarm_image=f"/static/images/sample/alarm_{random.randint(1, 5)}.jpg" if random.random() > 0.3 else None,
                    is_processed=is_processed,
                    processed_time=processed_time,
                    processed_by=processed_by,
                    is_confirmed=is_confirmed,
                    confirmed_at=confirmed_at,
                    confirmed_by=confirmed_by,
                    confirmation_type=confirmation_type,
                    description=description,
                    created_at=alarm_time
                )
                alarms.append(alarm)
                db.session.add(alarm)
            
            db.session.commit()
            
            # 验证告警数据
            saved_alarms = Alarm.query.all()
            if len(saved_alarms) == 100:
                print(f"成功生成 {len(saved_alarms)} 个告警数据")
            else:
                print(f"告警数据写入不完整，预期 100 个，实际写入 {len(saved_alarms)} 个")
            
            # 创建系统配置
            system_config = SystemConfig(
                system_name_zh="油田智能监控系统",
                system_name_en="Oilfield Smart Monitoring System",
                company_name="油田公司",
                logo_url="/static/images/logo.png",
                theme_color="#3498db"
            )
            db.session.add(system_config)
            
            # 创建键值设置
            settings = [
                KeyValueSetting(key="alarm_refresh_interval", value="30", description="告警刷新间隔（秒）"),
                KeyValueSetting(key="max_alarm_age_days", value="90", description="最大告警保留天数"),
                KeyValueSetting(key="default_page_size", value="20", description="默认分页大小"),
                KeyValueSetting(key="enable_email_notification", value="false", description="启用邮件通知"),
                KeyValueSetting(key="smtp_server", value="smtp.example.com", description="SMTP服务器"),
                KeyValueSetting(key="smtp_port", value="587", description="SMTP端口"),
                KeyValueSetting(key="notification_email", value="alert@example.com", description="通知邮箱"),
                KeyValueSetting(key="api_rate_limit", value="100", description="API速率限制（次/分钟）"),
                KeyValueSetting(key="login_attempts", value="5", description="最大登录尝试次数"),
                KeyValueSetting(key="session_timeout_minutes", value="120", description="会话超时时间（分钟）")
            ]
            
            for setting in settings:
                db.session.add(setting)
            
            db.session.commit()
            
            print("\n=== 测试数据生成完成 ===")
            print(f"用户: {len(saved_users)}个")
            print(f"设备: {len(devices)}个")
            print(f"油井: {len(saved_wells)}个")
            print(f"任务: {len(saved_tasks)}个")
            print(f"告警: {len(saved_alarms)}个")
            print(f"系统配置: 1个")
            print(f"键值设置: {len(settings)}个")
            print("======================\n")
            
            print("测试数据已成功生成，可以通过以下账户登录系统：")
            for user_data in test_users:
                print(f"用户名: {user_data['username']}, 密码: {user_data['password']}, 角色: {user_data['role']}")
            
        except Exception as e:
            import traceback
            print(f"生成测试数据失败: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()

if __name__ == "__main__":
    generate_test_data()