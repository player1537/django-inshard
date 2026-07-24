"""Custom Django lookup: ``__inshard``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db import models
from django.db.models import lookups

from .utils import Shard

__all__ = [
    'InShard',
    'register_lookups',
]


_deferred: list[tuple[Callable, tuple, dict]] = []


def _defer(
    func: Callable,
    *args: Any,
    **kwargs: Any,
) -> None:
    _deferred.append((func, args, kwargs))


def register_lookups() -> None:
    """Run all deferred lookup registrations."""
    for func, args, kwargs in _deferred:
        func(*args, **kwargs)


class InShard(lookups.Exact):
    """Check if a field value falls in a specified shard.

    Example::

        Foo.objects.filter(pk__inshard='1of10')

    """

    lookup_name = 'inshard'
    prepare_rhs = False

    def as_sql(
        self,
        compiler: Any,
        connection: Any,
        **extra_context: Any,
    ) -> tuple[str, Any]:
        if not isinstance(self.rhs, str):
            msg = f'Expected a string, got {type(self.rhs)}'
            raise TypeError(msg)

        shard = Shard.parse(self.rhs)
        q = shard.q(self.lhs)
        return q.as_sql(compiler, connection, **extra_context)


_defer(models.IntegerField.register_lookup, InShard)
