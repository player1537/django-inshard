"""Shard: a hash-based partition selector for querysets."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Self

from django.db.models import Value
from django.db.models.expressions import F
from django.db.models.lookups import Exact

from .model_utils import ShardHash

if TYPE_CHECKING:
    from django.db import models


class Shard(NamedTuple):
    """A '``m`` of ``n``' hash-based shard selection.

    ``m`` is 1-indexed: ``Shard(1, 10)`` is the first of ten shards.
    """

    m: int
    n: int

    @classmethod
    def range(cls, num_shards: int) -> list[Self]:
        """Return a list of shards for all partitions ``1..num_shards``."""
        return [cls(m, num_shards) for m in range(1, num_shards + 1)]

    @classmethod
    def parse(cls, value: str) -> Shard:
        """Parse a shard spec like ``'3of10'``."""
        try:
            m_str, n_str = value.lower().split('of')
            m, n = int(m_str), int(n_str)
        except ValueError as exc:
            msg = f"shard must look like 'MofN', got {value!r}"
            raise ValueError(msg) from exc
        if not (1 <= m <= n):
            msg = f'shard {value!r} must satisfy 1 <= M <= N'
            raise ValueError(msg)
        return cls(m, n)

    def __str__(self) -> str:
        return f'{self.m}of{self.n}'

    def bucket(self, e: models.Expression | None = None, /) -> ShardHash:
        """ORM expression for this shard's bucket index."""
        if e is None:
            e = F('pk')
        return ShardHash(e, Value(self.n))

    def q(self, e: models.Expression | None = None, /) -> Exact:
        """``Q`` object selecting rows in this shard."""
        return Exact(lhs=self.bucket(e), rhs=self.m - 1)
