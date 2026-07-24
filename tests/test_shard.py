import pytest

from django_inshard import Shard

from .models import Item


class TestShardParsing:
    def test_parse_valid(self) -> None:
        assert Shard.parse('3of10') == Shard(3, 10)

    def test_parse_case_insensitive(self) -> None:
        assert Shard.parse('3OF10') == Shard(3, 10)

    def test_parse_1of1(self) -> None:
        assert Shard.parse('1of1') == Shard(1, 1)

    def test_parse_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="must look like 'MofN'"):
            Shard.parse('bad')

    def test_parse_m_zero(self) -> None:
        with pytest.raises(ValueError, match='must satisfy 1 <= M <= N'):
            Shard.parse('0of10')

    def test_parse_m_greater_than_n(self) -> None:
        with pytest.raises(ValueError, match='must satisfy 1 <= M <= N'):
            Shard.parse('11of10')

    def test_str(self) -> None:
        assert str(Shard(3, 10)) == '3of10'

    def test_range(self) -> None:
        assert Shard.range(3) == [Shard(1, 3), Shard(2, 3), Shard(3, 3)]


@pytest.mark.django_db
class TestShardPartitioning:
    @pytest.fixture(autouse=True)
    def _items(self) -> None:
        Item.objects.bulk_create([Item(name=f'item{i}') for i in range(200)])

    def test_shards_cover_all_rows(self) -> None:
        """Union of all shards equals the full queryset."""
        all_pks = set(Item.objects.values_list('pk', flat=True))
        shard_pks: set[int] = set()
        for shard in Shard.range(10):
            shard_pks |= set(
                Item.objects.filter(pk__inshard=str(shard)).values_list(
                    'pk', flat=True,
                ),
            )
        assert shard_pks == all_pks

    def test_shards_are_disjoint(self) -> None:
        """No row belongs to two different shards of the same n."""
        sets = [
            set(
                Item.objects.filter(pk__inshard=str(shard)).values_list(
                    'pk', flat=True,
                ),
            )
            for shard in Shard.range(7)
        ]
        for i, a in enumerate(sets):
            for b in sets[i + 1 :]:
                assert a.isdisjoint(b)

    def test_shard_nonempty(self) -> None:
        """With 200 rows and 10 shards, each shard should have items."""
        for shard in Shard.range(10):
            count = Item.objects.filter(pk__inshard=str(shard)).count()
            assert count > 0, f'{shard} is empty'

    def test_1of1_returns_all(self) -> None:
        total = Item.objects.count()
        shard_count = Item.objects.filter(pk__inshard='1of1').count()
        assert shard_count == total


@pytest.mark.django_db
class TestXORScramble:
    """The XOR with hash(n) means different n values scramble assignments."""

    @pytest.fixture(autouse=True)
    def _items(self) -> None:
        Item.objects.bulk_create([Item(name=f'item{i}') for i in range(2000)])

    def test_different_n_not_subset(self) -> None:
        """Shard 1of10 and shard 1of100 should not be subset-related.

        Without the XOR, bucket = hash(pk) % n, so every pk with
        hash(pk) % 100 == 0 also has hash(pk) % 10 == 0 — i.e. 1of100
        is always a subset of 1of10.  The XOR breaks this relationship.
        """
        pks_10 = set(
            Item.objects.filter(pk__inshard='1of10').values_list(
                'pk', flat=True,
            ),
        )
        pks_100 = set(
            Item.objects.filter(pk__inshard='1of100').values_list(
                'pk', flat=True,
            ),
        )
        assert len(pks_100) > 0
        assert len(pks_10) > 0
        assert not pks_100.issubset(pks_10)


@pytest.mark.django_db
class TestShardQ:
    """Test the programmatic Shard.q() interface."""

    @pytest.fixture(autouse=True)
    def _items(self) -> None:
        Item.objects.bulk_create([Item(name=f'item{i}') for i in range(100)])

    def test_filter_with_q(self) -> None:
        shard = Shard(1, 10)
        via_lookup = set(
            Item.objects.filter(pk__inshard='1of10').values_list(
                'pk', flat=True,
            ),
        )
        via_q = set(
            Item.objects.filter(shard.q()).values_list('pk', flat=True),
        )
        assert via_lookup == via_q

    def test_exclude_with_q(self) -> None:
        shard = Shard(1, 10)
        included = set(
            Item.objects.filter(shard.q()).values_list('pk', flat=True),
        )
        excluded = set(
            Item.objects.exclude(shard.q()).values_list('pk', flat=True),
        )
        all_pks = set(Item.objects.values_list('pk', flat=True))
        assert included | excluded == all_pks
        assert included & excluded == set()
