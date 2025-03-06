from datetime import datetime, timedelta
from app import create_app, db
from app.models.alarm import Alarm
import random

def generate_alarm_number():
    """生成告警编号：AL + 时间戳 + 微秒 + 随机数"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')  # 添加微秒
    random_num = str(random.randint(100, 999))  # 减少为3位随机数
    return f"AL{timestamp}{random_num}"

def generate_device_name():
    device_types = ['Camera', 'NVR', 'DVR', 'Server']
    locations = ['East', 'West', 'North', 'South']
    numbers = range(1, 100)
    return f"{random.choice(device_types)}_{random.choice(locations)}_{random.choice(numbers)}"

def generate_ip():
    return f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"

def create_test_alarms(num_records=50):
    alarm_types = ['视频丢失', '移动侦测', '硬盘错误', '网络断开', '设备离线']
    
    for _ in range(num_records):
        alarm = Alarm(
            alarm_number=generate_alarm_number(),  # 使用生成的唯一告警编号
            alarm_type=random.choice(alarm_types),
            device_name=generate_device_name(),
            device_ip=generate_ip(),
            alarm_time=datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            ),
            is_processed=random.choice([True, False])
        )
        db.session.add(alarm)
    
    db.session.commit()

def clear_test_alarms():
    """清空所有告警数据"""
    try:
        Alarm.query.delete()
        db.session.commit()
        print("所有告警数据已清空！")
    except Exception as e:
        db.session.rollback()
        print(f"清空数据失败：{str(e)}")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        clear_test_alarms()
        create_test_alarms(50)
        print("测试数据生成完成！")