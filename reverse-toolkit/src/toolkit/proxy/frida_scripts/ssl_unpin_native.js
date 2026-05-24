// Frida Native 层 SSL Pinning 绕过脚本
// 用于对抗 Native 层实现的 SSL 校验（如 libsslsdk.so）
// 用法: frida -U -f <package> -l ssl_unpin_native.js --no-pause

// Hook SSL_read / SSL_write 查看明文流量
// Hook libssl.so 中的 SSL_set_fd, SSL_connect 等函数

(function() {
    var SSL_get_verify_result = Module.findExportByName("libssl.so", "SSL_get_verify_result");
    if (SSL_get_verify_result) {
        Interceptor.attach(SSL_get_verify_result, {
            onLeave: function(retval) {
                console.log("[SSL Unpin Native] SSL_get_verify_result -> forcing X509_V_OK");
                retval.replace(0); // X509_V_OK
            }
        });
    }

    console.log("[SSL Unpin Native] Loaded. Hooked SSL_get_verify_result.");
})();
