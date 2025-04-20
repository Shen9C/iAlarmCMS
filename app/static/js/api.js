/**
 * 通用API请求函数，自动处理token和CSRF保护
 * 
 * @param {string} url - API请求路径
 * @param {Object} options - 请求选项，同fetch的options
 * @returns {Promise<any>} 返回API响应的JSON数据
 */
function apiRequest(url, options = {}) {
    // 获取用户令牌
    const userToken = new URLSearchParams(window.location.search).get('user_token');
    if (userToken) {
        // 确保URL中包含user_token参数
        if (url.includes('?')) {
            url += `&user_token=${userToken}`;
        } else {
            url += `?user_token=${userToken}`;
        }
    }

    // 合并默认选项和传入选项
    const defaultOptions = {
        headers: {
        'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    };

    // 深度合并请求头
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    // 执行请求
    return fetch(url, mergedOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
            }
            
            // 检查响应类型并相应处理
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
            return response.json();
            } else {
                return response.text();
            }
        })
        .catch(error => {
            console.error('API请求错误:', error);
            throw error;
        });
}