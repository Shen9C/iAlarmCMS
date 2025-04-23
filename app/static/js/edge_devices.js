// 添加设备的函数
function addDevice() {
    const form = document.getElementById('addDeviceForm');
    const formData = new FormData(form);
    
    // 打印调试信息
    console.log('FormData:', {
        name: formData.get('device_name'),
        device_type: formData.get('device_type'),
        ip_address: formData.get('ip_address'),
        port: formData.get('port')
    });

    // 获取表单中的输入值
    const deviceData = {
        name: document.querySelector('#device_name').value,
        device_type: document.querySelector('#device_type').value,
        ip_address: document.querySelector('#ip_address').value,
        port: document.querySelector('#port').value
    };

    // 发送请求
    fetch('/api/edge_devices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(deviceData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.code === 200) {
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('addDeviceModal'));
            modal.hide();
            
            // 显示成功消息
            showAlert('success', '设备添加成功');
            
            // 刷新页面
            window.location.reload();
        } else {
            showAlert('danger', data.message || '添加设备失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('danger', '服务器错误，请稍后再试');
    });
}

// 修改文档加载完成后的事件绑定
document.addEventListener('DOMContentLoaded', function() {
    // 修改按钮 ID 为 addDeviceBtn
    const addDeviceBtn = document.getElementById('addDeviceBtn');
    if (addDeviceBtn) {
        addDeviceBtn.addEventListener('click', function() {
            // 打开添加设备的模态框
            const modal = new bootstrap.Modal(document.getElementById('addDeviceModal'));
            modal.show();
        });
    }

    // 绑定模态框中的保存按钮事件
    const saveDeviceBtn = document.getElementById('saveDeviceBtn');
    if (saveDeviceBtn) {
        saveDeviceBtn.addEventListener('click', function(e) {
            e.preventDefault();
            addDevice();
        });
    }

    // 保留原有的表单提交事件绑定
    const addDeviceForm = document.getElementById('addDeviceForm');
    if (addDeviceForm) {
        addDeviceForm.addEventListener('submit', function(e) {
            e.preventDefault();
            addDevice();
        });
    }
});

// 显示提示信息的辅助函数
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 3秒后自动关闭
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// 重新生成设备认证密钥
function regenerateKeys(deviceId) {
    if (!confirm('确定要重新生成该设备的认证密钥吗？这将使当前的密钥失效。')) {
        return;
    }
    
    // 添加调试信息
    console.log(`正在重新生成设备ID为${deviceId}的密钥...`);
    
    fetch(`/api/edge_devices/${deviceId}/regenerate_keys`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        console.log('接口响应状态:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('接口响应数据:', data);
        if (data.code === 200) {
            showAlert('success', '认证密钥重新生成成功');
            // 显示新生成的密钥
            const keysHtml = `
                <div class="alert alert-info">
                    <p><strong>新生成的密钥:</strong> ${data.data.secret_key}</p>
                    <p class="text-warning">请立即保存这个信息，它不会再次显示！</p>
                </div>
            `;
            const keysContainer = document.getElementById(`keys-container-${deviceId}`);
            if (keysContainer) {
                keysContainer.innerHTML = keysHtml;
            } else {
                const container = document.createElement('div');
                container.id = `keys-container-${deviceId}`;
                container.innerHTML = keysHtml;
                const deviceRow = document.querySelector(`[data-device-id="${deviceId}"]`);
                if (deviceRow) {
                    deviceRow.after(container);
                }
            }
        } else {
            showAlert('danger', data.message || '重新生成密钥失败');
        }
    })
    .catch(error => {
        console.error('请求错误:', error);
        showAlert('danger', '服务器错误，请稍后再试');
    });
}