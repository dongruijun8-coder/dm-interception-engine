from pathlib import Path
from mitmproxy.options import Options
from mitmproxy.master import Master
from mitmproxy.addons import default_addons
from toolkit.proxy.addon import FlowRecorder


def start_proxy(app: str, host_filter: str, output_dir: str, frida_script: str | None = None):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    recorder = FlowRecorder(host_filter=host_filter, output_dir=output_dir)

    opts = Options(listen_host="0.0.0.0", listen_port=8080)
    master = Master(opts)
    master.addons.add(*default_addons())
    master.addons.add(recorder)

    if frida_script:
        print(f"[提示] 请先在目标设备上运行 Frida 脚本: frida -U -f <package> -l {frida_script} --no-pause")
    else:
        frida_dir = Path(__file__).resolve().parent / "frida_scripts"
        print(f"[提示] 可用 Frida SSL Unpin 脚本:")
        for js in frida_dir.glob("*.js"):
            print(f"  frida -U -f <package> -l {js} --no-pause")

    print(f"[代理] 启动在 0.0.0.0:8080")
    print(f"[过滤] 域名: {host_filter}")
    print(f"[输出] {output_dir}")
    print(f"[停止] 按 Ctrl+C 退出")
    print()

    try:
        master.run()
    except KeyboardInterrupt:
        print("\n[代理] 已停止")
        master.shutdown()
