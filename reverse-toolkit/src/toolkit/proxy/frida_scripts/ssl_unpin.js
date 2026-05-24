// Frida 通用 SSL Pinning 绕过脚本 (Java 层)
// 用法: frida -U -f <package> -l ssl_unpin.js --no-pause

Java.perform(function() {
    var array_list = Java.use("java.util.ArrayList");
    var SSLContext = Java.use("javax.net.ssl.SSLContext");
    var TrustManager = Java.use("javax.net.ssl.X509TrustManager");

    // 信任所有证书
    var TrustAllCerts = Java.registerClass({
        name: "com.reverse.toolkit.TrustAllCerts",
        implements: [TrustManager],
        methods: {
            checkClientTrusted: function(chain, authType) {},
            checkServerTrusted: function(chain, authType) {},
            getAcceptedIssuers: function() { return array_list.$new().toArray(); }
        }
    });

    // Hook SSLContext.init 替换 TrustManager
    SSLContext.init.overload(
        '[Ljavax.net.ssl.KeyManager;',
        '[Ljavax.net.ssl.TrustManager;',
        'java.security.SecureRandom'
    ).implementation = function(km, tm, sr) {
        console.log("[SSL Unpin] SSLContext.init hooked");
        var trustAll = [TrustAllCerts.$new()];
        this.init(km, trustAll, sr);
    };
});
