from api.config import get_allowed_origins


class TestGetAllowedOrigins:
    def test_defaults_to_local_dev_servers(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        assert get_allowed_origins() == ["http://localhost:5173", "http://localhost:3000"]

    def test_reads_comma_separated_env_var(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com")
        assert get_allowed_origins() == ["https://app.example.com", "https://admin.example.com"]

    def test_ignores_blank_entries(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com,,")
        assert get_allowed_origins() == ["https://app.example.com"]
