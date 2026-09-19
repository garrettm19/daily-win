"""Development-only TestClient that sends an isolated X-Demo-Session header."""

from fastapi.testclient import TestClient

DEMO_SESSION_A = "daily-win-demo-session-secret-aaa-mason"
DEMO_SESSION_B = "daily-win-demo-session-secret-bbb-cory"


class DemoClient(TestClient):
    """HTTP helper for isolated synthetic demo tenants. Not authentication."""

    def __init__(self, app, session_secret: str = DEMO_SESSION_A, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self.session_secret = session_secret

    def request(self, method, url, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("X-Demo-Session", self.session_secret)
        return super().request(method, url, headers=headers, **kwargs)

    def setup_hayes(self):
        response = self.post("/api/v1/demo/setup/hayes")
        assert response.status_code == 200, response.text
        return response

    def setup_profile(self, payload: dict):
        response = self.post("/api/v1/demo/setup/profile", json=payload)
        assert response.status_code == 200, response.text
        return response
