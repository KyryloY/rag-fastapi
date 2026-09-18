import importlib
import sys

from fastapi import FastAPI


def test_importing_create_app_does_not_build_gemini_clients(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    sys.modules.pop("app.main", None)
    sys.modules.pop("app.config", None)
    module = importlib.import_module("app.main")
    assert callable(module.create_app)
    assert callable(module.create_default_app)
    assert not isinstance(getattr(module, "app", None), FastAPI)
