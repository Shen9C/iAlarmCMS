import re
from werkzeug.security import check_password_hash

def validate_password(password):
    """验证密码复杂度"""
    if len(password) < 8:
        return False, "密码长度至少为8位"
    
    if not re.search(r"[A-Z]", password):
        return False, "密码必须包含大写字母"
    
    if not re.search(r"[a-z]", password):
        return False, "密码必须包含小写字母"
    
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "密码必须包含特殊字符"
    
    return True, "密码符合要求"

def verify_password(user, password):
    """验证用户密码"""
    if not user or not user.password_hash:
        return False
    return check_password_hash(user.password_hash, password)