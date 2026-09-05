"""Automated audit tests for Security (S1–S5) and Reliability (R1–R5)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


# ── Helpers ───────────────────────────────────────────────────────────────────


def read(path: str | Path) -> str:
    return (REPO_ROOT / path).read_text()


# ── Security ───────────────────────────────────────────────────────────────────


class TestSecurityS1:
    """S1: No hardcoded secrets in docker-compose.yml."""

    def test_no_token_patterns_in_compose(self):
        content = read("docker-compose.yml")
        patterns = [
            r"ghp_", r"api_key", r"password\s*=", r"secret\s*=",
            r"APPROTOKEN", r"BASE64",
        ]
        for pat in patterns:
            assert not re.search(pat, content, re.IGNORECASE), f"Found secret pattern: {pat}"

    def test_all_secrets_use_env_substitution(self):
        content = read("docker-compose.yml")
        # Known secret-adjacent vars must use ${VAR:-default}
        secret_vars = ["OLLAMA_HOST", "OLLAMA_MODEL", "LOG_LEVEL"]
        for var in secret_vars:
            # Should appear as ${VAR:-...} not as a bare value
            pattern = rf"\$\{{{var}:-"
            assert re.search(pattern, content), f"{var} should use ${{var:-default}} form"


class TestSecurityS2:
    """S2: .env.example contains no real credentials."""

    def test_no_ghp_tokens_in_env_example(self):
        content = read(".env.example")
        assert not re.search(r"ghp_[a-zA-Z0-9]{20,}", content)

    def test_no_sk_tokens_in_env_example(self):
        content = read(".env.example")
        assert not re.search(r"sk-[a-zA-Z0-9]{20,}", content)

    def test_no_uncommented_real_proxy_values(self):
        content = read(".env.example")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert "HTTP_PROXY=http://" not in line
            assert "HTTPS_PROXY=http://" not in line


class TestSecurityS3:
    """S3: Proxy env vars are commented or absent in committed files."""

    def test_no_uncommented_proxy_in_compose(self):
        content = read("docker-compose.yml")
        for line in content.splitlines():
            if not line.strip().startswith("#"):
                assert "HTTP_PROXY=" not in line.upper()
                assert "HTTPS_PROXY=" not in line.upper()


class TestSecurityS4:
    """S4: Dockerfile HEALTHCHECK uses python3 inline, not sqlite3 CLI."""

    def test_dockerfile_healthcheck_uses_python3(self):
        content = read("Dockerfile")
        assert re.search(r"HEALTHCHECK.*python3", content, re.DOTALL), \
            "Dockerfile HEALTHCHECK should use python3"

    def test_dockerfile_healthcheck_not_using_curl(self):
        content = read("Dockerfile")
        assert "curl" not in content, "Dockerfile HEALTHCHECK should not use curl"


class TestSecurityS5:
    """S5: docker-compose.yml has no hardcoded UID/GID."""

    def test_no_hardcoded_user_in_compose(self):
        content = read("docker-compose.yml")
        assert not re.search(r"^\s*user:\s*\"?\d+:\d+\"?", content, re.MULTILINE), \
            "docker-compose.yml should not have hardcoded UID:GID"


class TestSecurityGitIgnore:
    """General: .env files are gitignored."""

    def test_dotenv_gitignored(self):
        from subprocess import run
        for f in [".env", ".env.production"]:
            result = run(["git", "check-ignore", f],  # noqa: S603, S607
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"{f} should be gitignored"


# ── Reliability ───────────────────────────────────────────────────────────────


class TestReliabilityR1:
    """R1: App healthcheck uses SELECT 1 via Python urllib."""

    def test_app_healthcheck_uses_select_1(self):
        content = read("docker-compose.yml")
        # Extract app service block (from 'app:' to next service or networks)
        import re
        app_match = re.search(r"app:.*?(?=\n  \w+:|\nnetworks:|\Z)", content, re.DOTALL)
        assert app_match, "Could not find app service block"
        app_section = app_match.group(0)
        assert "SELECT 1" in app_section, "App healthcheck should use 'SELECT 1'"
        assert "sqlite3" in app_section, "App healthcheck should use Python sqlite3 module"
        assert "urllib" not in app_section, "App healthcheck should NOT use urllib (that's ollama's check)"


class TestReliabilityR2:
    """R2: Ollama healthcheck uses urllib /api/tags, not curl."""

    def test_ollama_healthcheck_uses_urllib(self):
        content = read("docker-compose.yml")
        # Extract ollama service block (from '  ollama:' to next service or networks)
        import re
        # Match from the ollama service line (indented) to next service
        ollama_match = re.search(r"\n  ollama:.*?(?=\n  \w+:|\nnetworks:|\Z)", content, re.DOTALL)
        assert ollama_match, "Could not find ollama service block"
        ollama_section = ollama_match.group(0)
        assert "urllib.request" in ollama_section, "Ollama healthcheck should use urllib"
        assert "/api/tags" in ollama_section, "Ollama healthcheck should hit /api/tags"

    def test_ollama_healthcheck_no_curl(self):
        content = read("docker-compose.yml")
        import re
        ollama_match = re.search(r"\n  ollama:.*?(?=\n  \w+:|\nnetworks:|\Z)", content, re.DOTALL)
        assert ollama_match, "Could not find ollama service block"
        ollama_section = ollama_match.group(0)
        # Remove comments to avoid false positives from comment text
        no_comments = re.sub(r"#.*", "", ollama_section)
        assert "curl" not in no_comments, "Ollama healthcheck should not use curl"


class TestReliabilityR3:
    """R3: startup_checker.py exists and contains all required check functions."""

    def test_startup_checker_exists(self):
        path = REPO_ROOT / "scripts" / "startup_checker.py"
        assert path.exists(), "scripts/startup_checker.py must exist"

    def test_startup_checker_has_required_functions(self):
        content = read("scripts/startup_checker.py")
        for fn in ["check_database", "check_ollama", "check_raw_dirs"]:
            assert fn in content, f"startup_checker.py must define {fn}()"

    def test_startup_checker_exits_zero_on_success(self):
        # Smoke-test: startup_checker --help should not crash
        from subprocess import run
        result = run(["python3", "scripts/startup_checker.py", "--help"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"--help should succeed, got: {result.stderr}"


class TestReliabilityR4:
    """R4: config.py has EBA_DELAY and MAS_DELAY."""

    def test_eba_delay_config(self):
        content = read("config.py")
        assert "EBA_DELAY" in content, "config.py must define EBA_DELAY"
        assert "MAS_DELAY" in content, "config.py must define MAS_DELAY"

    def test_delay_env_vars(self):
        content = read("docker-compose.yml")
        assert "${EBA_DELAY" in content, "docker-compose.yml must use ${EBA_DELAY:-...}"
        assert "${MAS_DELAY" in content, "docker-compose.yml must use ${MAS_DELAY:-...}"


class TestReliabilityR5:
    """R5: loguru configured for structured JSON logging."""

    def test_logging_config_has_json_handler(self):
        content = read("scripts/logging_config.py")
        assert "serialize=True" in content, \
            "logging_config.py must add a serialize=True handler for JSON logs"

    def test_json_log_uses_compression(self):
        content = read("scripts/logging_config.py")
        assert "compression" in content, "Both text and JSON log handlers should compress"
