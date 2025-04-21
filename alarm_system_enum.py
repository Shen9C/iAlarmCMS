# 油田设备故障类型和故障码枚举配置
FAULT_CONFIG = {
    "fault_mapping": {
        "启停检测": [
            {"alarm_suffix_code": "QT001", "alarm_type": "异常停机", "description": "设备未经指令突然停止运行"},
            {"alarm_suffix_code": "QT003", "alarm_type": "运行不稳定", "description": "设备运行状态波动，频繁启停"},
            {"alarm_suffix_code": "QT004", "alarm_type": "自动切换失败", "description": "自动切换装置未正常工作"},
            {"alarm_suffix_code": "QT005", "alarm_type": "超时无响应", "description": "设备长时间未响应控制指令"}
        ],
        "皮带检测": [
            {"alarm_suffix_code": "PD001", "alarm_type": "皮带断裂", "description": "传动皮带出现断裂现象"},
            {"alarm_suffix_code": "PD002", "alarm_type": "皮带松弛", "description": "皮带张力不足，出现松弛"},
            {"alarm_suffix_code": "PD003", "alarm_type": "皮带偏移", "description": "皮带运行轨迹偏离正常位置"},
        ],
        "毛辫子检测": [
            {"alarm_suffix_code": "MBZ001", "alarm_type": "毛辫子断开", "description": "钢丝绳毛辫子出现断开"},
            {"alarm_suffix_code": "MBZ002", "alarm_type": "毛辫子松散", "description": "毛辫子组织结构松散"},
            {"alarm_suffix_code": "MBZ003", "alarm_type": "毛辫子锈蚀", "description": "毛辫子表面出现严重锈蚀"},
            {"alarm_suffix_code": "MBZ004", "alarm_type": "毛辫子变形", "description": "毛辫子出现扭曲、弯折等变形"},
            {"alarm_suffix_code": "MBZ005", "alarm_type": "毛辫子连接异常", "description": "毛辫子与设备连接部位出现异常"}
        ],
        "压力表检测": [
            {"alarm_suffix_code": "YLB001", "alarm_type": "未检测到压力表", "description": "管道或容器内压力超过安全阈值"},
            {"alarm_suffix_code": "YLB002", "alarm_type": "压力表失准", "description": "管道或容器内压力低于正常工作值"},
            {"alarm_suffix_code": "YLB005", "alarm_type": "压力表损坏", "description": "压力表物理损坏或无法显示"}
        ],
        "井口泄漏检测": [
            {"alarm_suffix_code": "JK001", "alarm_type": "轻微泄漏", "description": "井口区域出现少量油气泄漏"},
            {"alarm_suffix_code": "JK002", "alarm_type": "严重泄漏", "description": "井口区域出现大量油气泄漏"},
            {"alarm_suffix_code": "JK003", "alarm_type": "密封失效", "description": "井口密封装置失效"},
            {"alarm_suffix_code": "JK004", "alarm_type": "阀门泄漏", "description": "井口阀门处出现泄漏"},
            {"alarm_suffix_code": "JK005", "alarm_type": "管线连接泄漏", "description": "井口管线连接处出现泄漏"}
        ],
        "烟火检测": [
            {"alarm_suffix_code": "YH001", "alarm_type": "烟雾报警", "description": "检测到异常烟雾信号"},
            {"alarm_suffix_code": "YH002", "alarm_type": "明火报警", "description": "检测到明火信号"},
        ]
    },

    "confirm_types": [
        {"confirm_code": "R001", "confirm_type": "故障", "description": "确认为实际故障情况"},
        {"confirm_code": "R002", "confirm_type": "误报", "description": "设备误报，实际无故障"},
        {"confirm_code": "R003", "confirm_type": "测试", "description": "系统测试过程中产生的告警"},
        {"confirm_code": "R004", "confirm_type": "其他", "description": "其他告警"},
    ],
    "process_methods": [
        {"process_code": False, "process_type": "未处理", "description": "未处理的故障"},
        {"process_code": True, "process_type": "已处理", "description": "已经处理的故障"},
    ],
    "priority_levels": [
        {"level": 1, "name": "紧急", "response_time": "30分钟内"},
        {"level": 2, "name": "高优先级", "response_time": "2小时内"},
        {"level": 3, "name": "中优先级", "response_time": "8小时内"},
        {"level": 4, "name": "低优先级", "response_time": "24小时内"},
        {"level": 5, "name": "计划性处理", "response_time": "下次维护时"}
    ],
    "fault_severity": {
        "high": ["QT001", "PD001", "MBZ001", "YLB001", "JK002", "F002"],
        "medium": ["QT002", "QT003", "PD002", "PD003", "MBZ002", "MBZ003", "YLB003", "JK001", "JK003", "F001", "F003"],
        "low": ["QT004", "QT005", "PD004", "PD005", "MBZ004", "MBZ005", "YLB002", "YLB004", "YLB005", "JK004", "JK005", "F005"]
    },
}

# 使用示例：获取某个检测类型下的所有故障类型
def get_fault_types_by_detection(detection_type):
    """获取指定检测类型下的所有故障类型"""
    if detection_type in FAULT_CONFIG["fault_mapping"]:
        return [item["type"] for item in FAULT_CONFIG["fault_mapping"][detection_type]]
    return []

# 使用示例：根据故障码获取故障详情
def get_fault_by_alarm_suffix_code(fault_alarm_suffix_code):
    """根据故障码获取故障详情"""
    for detection_type, faults in FAULT_CONFIG["fault_mapping"].items():
        for fault in faults:
            if fault["alarm_suffix_code"] == fault_alarm_suffix_code:
                return {
                    "detection_type": detection_type,
                    "fault_alarm_suffix_code": fault["alarm_suffix_code"],
                    "fault_type": fault["type"],
                    "description": fault["description"],
                    "severity": get_fault_severity(fault["alarm_suffix_code"])
                }
    return None

# 使用示例：获取故障严重程度
def get_fault_severity(fault_alarm_suffix_code):
    """获取故障严重程度"""
    for severity, alarm_suffix_codes in FAULT_CONFIG["fault_severity"].items():
        if fault_alarm_suffix_code in alarm_suffix_codes:
            return severity
    return "unknown"