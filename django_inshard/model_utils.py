"""Shard bucket computation using Django ORM expressions."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import Value
from django.db.models.expressions import CombinedExpression

_SIGN_MASK = (1 << 63) - 1
_SHIFTS = (33, 13, 47)

__all__ = [
    "Xor",
    "shard_bucket",
    "shard_hash",
]


class Xor(models.Func):
    """Bitwise XOR of two integer expressions.

    PostgreSQL uses the ``#`` operator; SQLite simulates with
    ``(a | b) - (a & b)``.
    """

    arity = 2
    output_field = models.IntegerField()

    def as_sql(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        msg = f"Xor is not supported on {connection.vendor}"
        raise NotImplementedError(msg)

    def as_postgresql(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        a, b = self.source_expressions
        a_sql, a_params = compiler.compile(a)
        b_sql, b_params = compiler.compile(b)
        return f"({a_sql} # {b_sql})", a_params + b_params

    def as_sqlite(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        a, b = self.source_expressions
        a_sql, a_params = compiler.compile(a)
        b_sql, b_params = compiler.compile(b)
        return (
            f"(({a_sql} | {b_sql}) - ({a_sql} & {b_sql}))",
            a_params + b_params + a_params + b_params,
        )


def shard_hash(expr):
    """Return an ORM expression computing the hash of *expr*.

    Uses XOR-shift mixing (``Xor`` + ``>>``) to avoid any multiplication
    overflow, which SQLite's 64-bit signed integers cannot represent.
    """
    h = CombinedExpression(expr, "&", Value(_SIGN_MASK))
    for shift in _SHIFTS:
        h = Xor(h, CombinedExpression(h, ">>", Value(shift)))
    return CombinedExpression(h, "&", Value(_SIGN_MASK))


def shard_bucket(expr, n):
    """Return an expression for ``(shard_hash(expr) XOR shard_hash(n)) % n``.

    The result is an integer in ``[0, n)``.
    """
    return CombinedExpression(
        Xor(shard_hash(expr), shard_hash(n)),
        "%",
        n,
        output_field=models.IntegerField(),
    )
