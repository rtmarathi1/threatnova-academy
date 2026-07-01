"""Route registration. Importing this module wires all handlers onto the app."""
from ..server import App
from .. import auth

app = App()

# global middleware: attach current user/session to every request
app.use(auth.load_user_middleware)


def register_all():
    # imported for their side effects (each module registers routes on `app`)
    from . import public       # noqa: F401
    from . import auth_routes  # noqa: F401
    from . import student      # noqa: F401
    from . import certificates # noqa: F401
    from . import admin        # noqa: F401
    return app
