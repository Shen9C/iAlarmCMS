// 在现有的筛选函数中添加设备名称
function updateFilters() {
    const params = new URLSearchParams(window.location.search);
    const device_name = document.getElementById('device_name').value;
    if (device_name) {
        params.set('device_name', device_name);
    } else {
        params.delete('device_name');
    }
}

// 等待文档加载完成
$(document).ready(function() {
    console.log('Document ready');
    let currentAlarmId = null;

    // 筛选函数
    function updateFilters() {
        const params = new URLSearchParams(window.location.search);
        const device_name = document.getElementById('device_name').value;
        if (device_name) {
            params.set('device_name', device_name);
        } else {
            params.delete('device_name');
        }
    }

    // 添加设备名称筛选事件监听
    const deviceNameInput = document.getElementById('device_name');
    if (deviceNameInput) {
        deviceNameInput.addEventListener('change', updateFilters);
    }

    // 确认按钮点击事件
    $(document).on('click', '.confirm-btn', function(e) {
        e.preventDefault();
        const alarmNumber = $(this).data('alarm-number');  // 使用告警编号
        const userToken = new URLSearchParams(window.location.search).get('user_token');
        
        // 跳转到确认类型选择页面
        window.location.href = `/alarms_view/confirm_type/${alarmNumber}?user_token=${userToken}`;
    });

    // 确认类型表单提交事件
    $('#confirmForm').on('submit', function(e) {
        e.preventDefault();
        const alarmNumber = $(this).data('alarm-number');
        const confirmType = $('input[name="confirmType"]:checked').val();
        
        if (!confirmType) {
            alert('请选择确认类型');
            return;
        }

        const userToken = new URLSearchParams(window.location.search).get('user_token');
        const requestUrl = `/alarms_view/process/${alarmNumber}?user_token=${userToken}`;
        
        // 发送请求前禁用提交按钮
        $('#confirmSubmit').prop('disabled', true);
        
        fetch(requestUrl, {
            method: 'POST',
            body: new FormData(this)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect_url;
            } else {
                alert('确认失败：' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('操作失败：' + error.message);
        })
        .finally(() => {
            $('#confirmSubmit').prop('disabled', false);
        });
    });
    currentAlarmId = $(this).data('alarm-id');
    console.log('Current alarm ID:', currentAlarmId);
    
    // 显示模态框
    const modalElement = document.getElementById('confirmModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        // 重置单选按钮
        $('input[name="confirmType"]').prop('checked', false);
        modal.show();
    }
});

$(document).ready(function() {
    // 确认按钮点击事件
    $('.confirm-btn').click(function(e) {
        e.preventDefault();
        const alarmNumber = $(this).data('alarm-id');
        const userToken = new URLSearchParams(window.location.search).get('user_token');
        
        // 使用正确的URL格式
        window.location.href = `/alarms_view/${alarmNumber}?user_token=${userToken}`;
    });

    // 确认提交事件
    $('#confirmSubmit').click(function() {
        const alarmNumber = $('#confirmForm').data('alarm-number');
        const confirmType = $('input[name="confirmType"]:checked').val();
        
        if (!confirmType) {
            alert('请选择确认类型');
            return;
        }

        const userToken = new URLSearchParams(window.location.search).get('user_token');
        const requestUrl = `/alarms_view/process/${alarmNumber}?user_token=${userToken}`;
        
        const formData = new FormData();
        formData.append('confirm_type', confirmType);
        
        fetch(requestUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect_url;
            } else {
                alert('确认失败：' + (data.message || '未知错误'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('操作失败：' + error.message);
        });
    });
});