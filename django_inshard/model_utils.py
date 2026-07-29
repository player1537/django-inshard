"""Shard bucket computation using Django ORM expressions."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import Value
from django.db.models.expressions import CombinedExpression
from django.db.models.functions import Cast, Mod

_M = 2147483647  # 2^31 - 1, shared modulus for all hash variants

__all__ = [
    "ShardHash",
    "ShardHash1",
    "ShardHash2",
    "ShardHash3",
    "ShardBucket",
    "Xor",
]


def _bigval(n: int) -> Cast:
    """Return a ``Value`` explicitly cast to ``bigint``.

    psycopg3's ``ClientCursor`` (used by Django 6+) uses client-side binding
    which sends parameter values as text.  Without an explicit ``::bigint``
    cast, PostgreSQL infers bare integer literals as ``int4``, causing
    overflow in the LCG intermediate multiplications.
    """
    return Cast(Value(n), models.BigIntegerField())


class Xor(models.Func):
    """Bitwise XOR of two integer expressions.

    PostgreSQL uses the ``#`` operator; SQLite simulates with
    ``(a | b) - (a & b)``.
    """

    arity = 2
    output_field = models.BigIntegerField()

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


class ShardHash(models.Transform):
    """Two-round LCG hash: ``((A * (((A * (expr % M)) + C) % M)) + C) % M``.

    Subclasses supply ``_A`` and ``_C``.  The product ``(M - 1) * A < 2^63``
    guarantees no overflow on SQLite's 64-bit signed integers.
    """

    template = "%(expressions)s"
    output_field = models.BigIntegerField()
    _A: int
    _C: int

    def __init__(self, expression, **extra):
        bigint = models.BigIntegerField()
        x = Mod(expression, _bigval(_M), output_field=bigint)
        for _ in range(2):
            mul = CombinedExpression(
                _bigval(self._A),
                "*",
                x,
                output_field=bigint,
            )
            add = CombinedExpression(
                mul,
                "+",
                _bigval(self._C),
                output_field=bigint,
            )
            x = Mod(add, _bigval(_M), output_field=bigint)
        super().__init__(x, **extra)


class ShardHash1(ShardHash):
    _A = 1103515245  # glibc LCG
    _C = 12345
    lookup_name = "shardhash1"


class ShardHash2(ShardHash):
    _A = 1664525  # Numerical Recipes
    _C = 1013904223
    lookup_name = "shardhash2"


class ShardHash3(ShardHash):
    _A = 22695477  # Borland
    _C = 1
    lookup_name = "shardhash3"


# Register the three variants so ``field__shardhash1`` etc. work.
models.IntegerField.register_lookup(ShardHash1)
models.IntegerField.register_lookup(ShardHash2)
models.IntegerField.register_lookup(ShardHash3)


class ShardBucket(models.Transform):
    """Hash *expr* with Hash1, *n* with Hash2, XOR them, then Hash3 → mod *n*.

    The result is an integer in ``[0, n)``.
    """

    template = "%(expressions)s"
    output_field = models.IntegerField()

    def __init__(self, expression, n, **extra):
        bigint = models.BigIntegerField()
        inner = ShardHash3(
            Xor(ShardHash1(expression), ShardHash2(n)),
        )
        result = Mod(
            inner,
            n,
            output_field=bigint,
        )
        super().__init__(result, **extra)
