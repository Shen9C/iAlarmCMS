// 添加 AJAX 请求拦截器
$(document).ajaxSend(function(e, xhr, settings) {
    // 为所有 AJAX 请求添加 X-Requested-With 头
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    
    // 获取当前 URL 中的 user_token
    const urlParams = new URLSearchParams(window.location.search);
    const userToken = urlParams.get('user_token');
    
    // 如果存在 user_token，添加到请求 URL 中
    if (userToken) {
        // 检查 URL 是否已经包含参数
        const separator = settings.url.includes('?') ? '&' : '?';
        settings.url += `${separator}user_token=${userToken}`;
    }
});

$(document).ajaxComplete(function(e, xhr, settings) {
    // 检查是否需要刷新令牌
    if (xhr.status === 200 && xhr.responseJSON && xhr.responseJSON.status === 'refresh') {
        // 获取当前 URL
        let url = new URL(window.location.href);
        // 更新令牌
        url.searchParams.set('user_token', xhr.responseJSON.new_token);
        // 更新 URL，不刷新页面
        window.history.replaceState({}, '', url);
    }
    // 如果会话过期，重定向到登录页面
    if (xhr.status === 401) {
        window.location.href = '/auth/login';
    }
});