"""Tests for ServiceConfig and @service decorator."""

import pytest

from mcli.lib.services.config import SERVICE_CONFIG_ATTR, ServiceConfig, service


class TestServiceConfig:
    def test_defaults(self):
        cfg = ServiceConfig(name="test-svc")
        assert cfg.name == "test-svc"
        assert cfg.description == ""
        assert cfg.port is None
        assert cfg.host == "127.0.0.1"
        assert cfg.service_type == "daemon"
        assert cfg.restart_policy == "never"
        assert cfg.env == {}
        assert cfg.health_check is None
        assert cfg.command is None

    def test_custom_values(self):
        cfg = ServiceConfig(
            name="my-api",
            description="My API",
            port=8080,
            host="0.0.0.0",
            service_type="http",
            restart_policy="always",
            env={"KEY": "val"},
            health_check="/health",
            command="python -m myapp",
            working_dir="/tmp",
        )
        assert cfg.port == 8080
        assert cfg.host == "0.0.0.0"
        assert cfg.service_type == "http"
        assert cfg.restart_policy == "always"
        assert cfg.env == {"KEY": "val"}
        assert cfg.health_check == "/health"
        assert cfg.command == "python -m myapp"
        assert cfg.working_dir == "/tmp"

    def test_env_default_is_independent(self):
        cfg1 = ServiceConfig(name="a")
        cfg2 = ServiceConfig(name="b")
        cfg1.env["x"] = "1"
        assert "x" not in cfg2.env


class TestServiceDecorator:
    def test_decorator_attaches_config(self):
        @service(name="deco-svc", port=3000, service_type="http")
        def my_func():
            pass

        assert hasattr(my_func, SERVICE_CONFIG_ATTR)
        cfg = getattr(my_func, SERVICE_CONFIG_ATTR)
        assert isinstance(cfg, ServiceConfig)
        assert cfg.name == "deco-svc"
        assert cfg.port == 3000

    def test_decorator_preserves_function(self):
        @service(name="f")
        def my_func():
            return 42

        assert my_func() == 42

    def test_decorator_with_click_command(self):
        import click

        # @service must be below @click.command() so it decorates the raw function,
        # which then becomes the Command's .callback with the attr attached.
        @click.command()
        @service(name="click-svc", restart_policy="on-failure")
        def my_cmd():
            pass

        assert hasattr(my_cmd.callback, SERVICE_CONFIG_ATTR)
        cfg = getattr(my_cmd.callback, SERVICE_CONFIG_ATTR)
        assert cfg.name == "click-svc"
        assert cfg.restart_policy == "on-failure"
