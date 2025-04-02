// 添加统一的 API 请求工具
function apiRequest(url, options = {}) {
    // 设置默认 headers
    options.headers = {
        'Content-Type': 'application/json',
        'Token': localStorage.getItem('token'),
        ...options.headers
    };
    
    return fetch(url, options)
        .then(response => {
            if (response.status === 401) {
                // Token 无效或过期，重定向到登录页
                window.location.href = '/login';
                throw new Error('未授权访问');
            }
            return response.json();
        });
}