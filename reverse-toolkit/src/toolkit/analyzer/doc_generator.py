from toolkit.schema import ApiSpec


def generate_doc(spec: ApiSpec) -> str:
    lines = []
    lines.append(f"# {spec.app} API 分析报告")
    lines.append("")
    lines.append(f"**Base URL:** {spec.base_url}")
    lines.append(f"**版本:** {spec.version}")
    lines.append(f"**认证方式:** {spec.auth.type}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 公共参数")
    lines.append("")
    if spec.common_params.headers:
        lines.append("### 公共请求头")
        lines.append("```")
        for k, v in spec.common_params.headers.items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("")
    if spec.common_params.body:
        lines.append("### 公共 Body 字段")
        lines.append("")
        for field in spec.common_params.body:
            lines.append(f"- `{field}`")
        lines.append("")

    lines.append("## 状态码")
    lines.append("")
    if spec.status_codes:
        lines.append("| 状态码 | 说明 |")
        lines.append("|--------|------|")
        for code, desc in spec.status_codes.items():
            lines.append(f"| `{code}` | {desc} |")
    lines.append("")

    lines.append("## API 端点")
    lines.append("")

    categories: dict[str, list] = {}
    for ep in spec.endpoints:
        cat = ep.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ep)

    for cat in ["auth", "rooms", "rank", "message", "profile", "other"]:
        if cat not in categories:
            continue
        lines.append(f"### {_cat_label(cat)}")
        lines.append("")
        lines.append("| 方法 | 路径 | 分页 | 参数 |")
        lines.append("|------|------|------|------|")
        for ep in categories[cat]:
            params_str = ", ".join(ep.params.keys()) if ep.params else "-"
            pagination = ep.pagination or "-"
            lines.append(f"| {ep.method} | `{ep.path}` | {pagination} | {params_str} |")
        lines.append("")

    lines.append("## 反调信息")
    lines.append("")
    ar = spec.anti_reverse
    lines.append(f"- SSL Pinning: {'是' if ar.ssl_pinning else '否'}")
    lines.append(f"- 加密: {ar.encryption}")
    lines.append(f"- 设备指纹: {ar.device_fingerprint}")
    lines.append(f"- 验证码: {ar.captcha}")
    if ar.notes:
        lines.append(f"- 备注: {ar.notes}")
    lines.append("")

    return "\n".join(lines)


def _cat_label(cat: str) -> str:
    return {
        "auth": "认证",
        "rooms": "房间",
        "rank": "排行榜",
        "message": "私信",
        "profile": "用户",
        "other": "其他"
    }.get(cat, cat)
