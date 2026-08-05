from api_framework.client import APIConfig, APIClient
class TestAPI:
    def test_headers(self):
        c=APIClient(APIConfig(auth_token="tok")); assert c._headers()["Authorization"]=="Bearer tok"
    def test_wait(self):
        c=APIClient(APIConfig(rate_limit=0.01)); c._wait(); c._wait()

