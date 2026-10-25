"""
Central authorization helpers (Phase 2).

Before this module existed, several route files (admin.py, logs.py,
chat.py, ...) each defined their own identical `_require_admin()` /
`_get_user()` pair. This module is the single source of truth for "who is
the current user" and "does their role grant this permission", so that
role/permission enforcement lives in one place instead of being copied by
hand into every new blueprint (and, as a result, is easy to get
inconsistently wrong across files).

This intentionally does NOT change how any existing route decides *what*
to check (e.g. "role == admin" still means the same thing it always did)
-- it only removes the duplication and adds a genuinely new capability
(`require_permission`) for checking the Phase 1 Permission/RolePermission
model instead of hardcoded role-name comparisons.
"""

from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app import db
from app.models.user import User
from app.services.permissions import permissions_for_role


def get_current_user() -> "User | None":
    """Resolve the User for the current request's JWT identity.

    Verifies the JWT itself, so this is safe to call even on a route that
    forgot to add @jwt_required() -- though existing routes should keep
    doing so for clarity/consistency with the rest of the codebase.
    """
    verify_jwt_in_request()
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _effective_role_name(user: "User") -> str:
    """The role name used for permission lookups.

    Prefers the linked Role row's display name (e.g. "Software Engineer")
    over the legacy lowercase `user.role` string, since that's what
    services.permissions.permissions_for_role() expects. Falls back to
    `user.role` for any account that predates role_id being populated.
    """
    if user.role_ref and user.role_ref.name:
        return user.role_ref.name
    return user.role or ""


def require_role(*allowed_roles: str):
    """Decorator restricting a route to specific `user.role` string values.

    Matches the exact comparison style already used throughout the
    codebase (case-sensitive against the lowercase `role` column, e.g.
    "admin"), so this is a behavior-preserving drop-in for the old
    per-file `_require_admin()` helpers, generalized to N roles.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in allowed_roles:
                return jsonify({"error": "You do not have access to this resource."}), 403
            g.current_user = user
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def require_permission(permission_name: str):
    """Decorator restricting a route to roles granted `permission_name`.

    Unlike require_role(), this checks the Phase 1 permission catalog
    (services/permissions.py) rather than a hardcoded role name, so
    granting/revoking access for a role is a data change (ROLE_PERMISSION_MAP
    or, later, the RolePermission table) rather than a code change in every
    route that cares about it.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "User not found"}), 404
            role_name = _effective_role_name(user)
            if permission_name not in permissions_for_role(role_name):
                return jsonify({
                    "error": "Your role does not have permission to perform this action.",
                    "required_permission": permission_name,
                    "role": role_name,
                }), 403
            g.current_user = user
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


# Convenience alias for the single most common check in the existing codebase.
require_admin = require_role("admin")
