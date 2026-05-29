# logger.info("I am in mcli.__init__.py")

try:
    from mcli.app.main import main as main_func

    # from mcli.public import *
    # from mcli.private import *
except ImportError:
    from .app.main import main as main_func

__all__ = ["main_func"]

if __name__ == "__main__":
    main_func()
