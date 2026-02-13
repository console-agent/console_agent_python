"""Tests for content anonymization."""

from console_agent.utils.anonymize import anonymize, anonymize_value


class TestAnonymize:
    def test_redacts_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = anonymize(text)
        assert "eyJhbGci" not in result
        assert "REDACTED_TOKEN" in result

    def test_redacts_email(self):
        text = "Contact user@example.com for details"
        result = anonymize(text)
        assert "user@example.com" not in result
        assert "[EMAIL]" in result

    def test_redacts_ipv4(self):
        text = "Server at 192.168.1.100"
        result = anonymize(text)
        assert "192.168.1.100" not in result
        assert "[IP]" in result

    def test_redacts_aws_key(self):
        text = "key: AKIAIOSFODNN7EXAMPLE"
        result = anonymize(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "REDACTED_AWS_KEY" in result

    def test_redacts_private_key(self):
        text = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...\n-----END PRIVATE KEY-----"
        result = anonymize(text)
        assert "MIIEvQIBADANBg" not in result
        assert "REDACTED_PRIVATE_KEY" in result

    def test_redacts_connection_string(self):
        text = "db = postgres://user:pass@host:5432/mydb"
        result = anonymize(text)
        assert "postgres://" not in result
        assert "REDACTED_CONNECTION_STRING" in result

    def test_redacts_env_secret(self):
        text = "DATABASE_URL=postgres://localhost/db"
        result = anonymize(text)
        assert "postgres://localhost" not in result
        assert "REDACTED" in result

    def test_preserves_normal_text(self):
        text = "This is a normal sentence without secrets."
        result = anonymize(text)
        assert result == text


class TestAnonymizeValue:
    def test_anonymizes_string(self):
        result = anonymize_value("email: user@test.com")
        assert isinstance(result, str)
        assert "[EMAIL]" in result

    def test_anonymizes_dict(self):
        data = {"email": "user@test.com", "count": 42}
        result = anonymize_value(data)
        assert isinstance(result, dict)
        assert "[EMAIL]" in result["email"]
        assert result["count"] == 42

    def test_anonymizes_list(self):
        data = ["user@test.com", "normal text"]
        result = anonymize_value(data)
        assert isinstance(result, list)
        assert "[EMAIL]" in result[0]
        assert result[1] == "normal text"

    def test_preserves_numbers(self):
        assert anonymize_value(42) == 42

    def test_preserves_none(self):
        assert anonymize_value(None) is None

    def test_preserves_bool(self):
        assert anonymize_value(True) is True

    def test_handles_nested(self):
        data = {
            "user": {"email": "a@b.com", "name": "John"},
            "ips": ["10.0.0.1", "safe text"],
        }
        result = anonymize_value(data)
        assert "[EMAIL]" in result["user"]["email"]
        assert result["user"]["name"] == "John"
        assert "[IP]" in result["ips"][0]
        assert result["ips"][1] == "safe text"
