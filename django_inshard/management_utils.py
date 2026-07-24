"""Reusable argument mixins for Django management commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .utils import Shard

if TYPE_CHECKING:
    import argparse


class WithShardArgumentMixin:
    """Mixin to add a ``--shard`` argument to management commands."""

    def add_shard_argument(
        self,
        parser: argparse.ArgumentParser | argparse._MutuallyExclusiveGroup,
        arg_name: str = '--shard',
        dest: str = 'shard',
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault('type', Shard.parse)
        kwargs.setdefault('metavar', 'MofN')
        parser.add_argument(arg_name, dest=dest, **kwargs)
