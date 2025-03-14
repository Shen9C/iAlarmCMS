// 在现有的筛选函数中添加设备名称
function updateFilters() {
    const params = new URLSearchParams(window.location.search);
    // ... 其他筛选条件 ...
    const device_name = document.getElementById('device_name').value;
    if (device_name) {
        params.set('device_name', device_name);
    } else {
        params.delete('device_name');
    }
    // ... 其他代码 ...
}

// 添加设备名称筛选事件监听
document.getElementById('device_name').addEventListener('change', updateFilters);