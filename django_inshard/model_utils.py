"""ShardHash: database function for shard bucket computation."""

from __future__ import annotations

from typing import Any

from django.db import models


_MUL = 1111111111111111111
_MASK64 = (1 << 64) - 1
_SIGN_MASK = (1 << 63) - 1


def _inshard_hash(v: int) -> int:
    """FNV-like hash of a 64-bit integer. Returns a non-negative int63."""
    v = int(v) & _MASK64
    h = 0
    for shift in (56, 48, 40, 32, 24, 16, 8, 0):
        h ^= (v >> shift) & 0xFF
        h = (h * _MUL) & _MASK64
    return h & _SIGN_MASK


def _inshard_bucket(value: int | None, n: int | None) -> int | None:
    """SQLite UDF: compute shard bucket for *value* with *n* shards."""
    if value is None or n is None:
        return None
    return (_inshard_hash(value) ^ _inshard_hash(n)) % int(n)


class ShardHash(models.Func):
    """Shard bucket index: ``(hash(expr) XOR hash(n)) mod n``.

    Takes two arguments: the expression to hash and the shard count.
    Returns an integer in ``[0, n)``.

    On PostgreSQL, uses the built-in ``hashint8`` with a double-modulo to
    handle signed remainders.  On SQLite, delegates to a Python UDF
    (``inshard_bucket``) registered by the app's ``ready()`` hook.
    """

    arity = 2
    output_field = models.IntegerField()

    def as_sql(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        msg = f'ShardHash is not supported on {connection.vendor}'
        raise NotImplementedError(msg)

    def as_postgresql(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        e_sql, e_params = compiler.compile(self.source_expressions[0])
        n_sql, n_params = compiler.compile(self.source_expressions[1])
        sql = (
            f'((hashint8({e_sql}) # hashint8({n_sql}))'
            f' %% {n_sql} + {n_sql}) %% {n_sql}'
        )
        params = list(e_params) + list(n_params) * 4
        return sql, params

    def as_sqlite(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, list[Any]]:
        e_sql, e_params = compiler.compile(self.source_expressions[0])
        n_sql, n_params = compiler.compile(self.source_expressions[1])
        sql = f'inshard_bucket({e_sql}, {n_sql})'
        params = list(e_params) + list(n_params)
        return sql, params
