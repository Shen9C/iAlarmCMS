import os
import sys
import logging

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    app = create_app()
    
    with app.app_context():
        # 测试数据库连接
        try:
            # 尝试执行一个简单的查询
            result = db.session.execute("SELECT 1").fetchone()
            logger.info(f"数据库连接测试结果: {result}")
            
            # 打印SQLAlchemy配置
            logger.info(f"SQLAlchemy数据库URI: {db.engine.url}")
            
            # 尝试创建表
            db.create_all()
            logger.info("表创建完成")
            
            # 验证表是否存在
            tables = db.engine.table_names()
            logger.info(f"数据库中的表: {tables}")
            
        except Exception as e:
            logger.error(f"数据库操作出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()