from dataclasses import dataclass, field


@dataclass
class LoginStep:
    order: int
    endpoint: str
    method: str = "POST"
    params: dict = field(default_factory=dict)
    extract: str | None = None


@dataclass
class AuthInfo:
    type: str  # "token" | "cookie" | "oauth" | "none"
    login_flow: list[LoginStep] = field(default_factory=list)


@dataclass
class CommonParams:
    headers: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    url_params: list[str] = field(default_factory=list)


@dataclass
class PreStep:
    endpoint: str
    extract: str
    pass_to: str


@dataclass
class EndpointDef:
    name: str
    method: str
    path: str
    category: str  # auth|rooms|rank|message|profile|other
    params: dict = field(default_factory=dict)
    pagination: str | None = None  # offset_limit|page_num|cursor|None
    response_model: str | None = None
    pre_steps: list[PreStep] | None = None


@dataclass
class AntiReverseInfo:
    ssl_pinning: bool = False
    encryption: str = "none"
    device_fingerprint: str = "none"
    captcha: str = "none"
    notes: str = ""


@dataclass
class ApiSpec:
    app: str
    version: str
    base_url: str
    auth: AuthInfo = field(default_factory=AuthInfo)
    common_params: CommonParams = field(default_factory=CommonParams)
    endpoints: list[EndpointDef] = field(default_factory=list)
    status_codes: dict[str, str] = field(default_factory=dict)
    anti_reverse: AntiReverseInfo = field(default_factory=AntiReverseInfo)
