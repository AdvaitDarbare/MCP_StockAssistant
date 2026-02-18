def __getattr__(name: str):
    if name == "app":
        from .gateway.main import app

        return app
    raise AttributeError(name)


__all__ = ["app"]
