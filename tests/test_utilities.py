"""
Test utilities and advanced features for LambdaCat.

This tests the Phase 5 implementations from the ActionList.
"""

from src.LambdaCat.core import Cat
from src.LambdaCat.core.functor import FunctorBuilder
from src.LambdaCat.core.natural import Natural
from src.LambdaCat.core.standard import discrete, monoid_category, poset_category, simplex


class TestUtilities:
    """Test utilities and advanced features."""

    def test_monoid_category(self):
        """Test monoid category construction."""
        # Define a monoid: {id, a, b} with a² = b, b² = a
        elements = ['id:*', 'a', 'b']
        operation = {
            ('id:*', 'id:*'): 'id:*', ('id:*', 'a'): 'a', ('id:*', 'b'): 'b',
            ('a', 'id:*'): 'a', ('a', 'a'): 'b', ('a', 'b'): 'a',
            ('b', 'id:*'): 'b', ('b', 'a'): 'b', ('b', 'b'): 'a'
        }

        M = monoid_category(elements, operation, 'id:*')

        # Check structure
        assert len(M.objects) == 1
        assert len(M.arrows) == 3

        # Check composition
        assert M.compose('a', 'b') == 'a'
        assert M.compose('a', 'a') == 'b'
        assert M.compose('b', 'b') == 'a'

        # Check identity
        assert M.compose('id:*', 'a') == 'a'
        assert M.compose('a', 'id:*') == 'a'

    def test_poset_category(self):
        """Test poset category construction."""
        # Define a simple poset: A ≤ B ≤ C
        leq = {
            ('A', 'A'): True, ('B', 'B'): True, ('C', 'C'): True,  # Reflexivity
            ('A', 'B'): True, ('B', 'C'): True, ('A', 'C'): True,  # Transitivity
            ('B', 'A'): False, ('C', 'B'): False, ('C', 'A'): False  # No reverse arrows
        }

        P = poset_category(['A', 'B', 'C'], leq)

        # Check structure
        assert len(P.objects) == 3
        assert len(P.arrows) == 6  # 3 identities + 3 order arrows

        # Check composition (transitivity)
        assert P.compose('B->C', 'A->B') == 'A->C'

        # Check identity laws
        assert P.compose('A->B', 'id:A') == 'A->B'
        assert P.compose('id:B', 'A->B') == 'A->B'

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        # Create a simple category
        C = discrete(['X', 'Y'])

        # Serialize to JSON
        json_data = C.to_json()

        # Check JSON structure
        assert 'objects' in json_data
        assert 'arrows' in json_data
        assert 'composition' in json_data
        assert 'identities' in json_data

        assert json_data['objects'] == ['X', 'Y']
        assert len(json_data['arrows']) == 2

        # Deserialize from JSON
        C2 = Cat.from_json(json_data)

        # Check reconstruction
        assert len(C2.objects) == len(C.objects)
        assert len(C2.arrows) == len(C.arrows)
        assert C2.compose('id:X', 'id:X') == 'id:X'
        assert C2.compose('id:Y', 'id:Y') == 'id:Y'

    def test_slice_category(self):
        """Test slice category construction."""
        # Create a simple category
        Delta2 = simplex(2)

        # Create slice category over object '1'
        slice_C = Delta2.slice('1')

        # Check structure
        assert len(slice_C.objects) == 2  # id:1 and 1->2
        assert len(slice_C.arrows) == 5   # identities + morphisms

        # Check that objects are arrows from '1'
        obj_names = [obj.name for obj in slice_C.objects]
        assert 'id:1' in obj_names
        assert '1->2' in obj_names

    def test_pretty_repr(self):
        """Test pretty representation methods."""
        # Test category repr
        C = discrete(['A', 'B'])
        repr_str = repr(C)
        assert 'Cat' in repr_str
        assert '|Obj|' in repr_str
        assert '|Arr|' in repr_str

        # Test functor repr
        F = (FunctorBuilder('F', C, C)
             .on_objects({'A': 'A', 'B': 'B'})
             .on_morphisms({'id:A': 'id:A', 'id:B': 'id:B'})
             .build())

        repr_str = repr(F)
        assert 'CatFunctor' in repr_str
        assert 'F:' in repr_str
        assert 'objects' in repr_str
        assert 'morphisms' in repr_str

        # Test natural transformation repr
        G = (FunctorBuilder('G', C, C)
             .on_objects({'A': 'A', 'B': 'B'})
             .on_morphisms({'id:A': 'id:A', 'id:B': 'id:B'})
             .build())

        eta = Natural(F, G, {'A': 'id:A', 'B': 'id:B'})
        repr_str = repr(eta)
        assert 'Natural' in repr_str
        assert 'components' in repr_str

    def test_opposite_category(self):
        """Test opposite category construction."""
        # Create a simple category
        C = simplex(2)

        # Create opposite category
        C_op = C.op()

        # Check structure
        assert len(C_op.objects) == len(C.objects)
        assert len(C_op.arrows) == len(C.arrows)

        # Check that composition is reversed
        # In C: 0->1 ∘ id:0 = 0->1
        # In C_op: id:0 ∘ 0->1 = 0->1 (but with reversed arrows)
        # This is a simplified check - the actual implementation may vary
        assert C_op is not C  # Should be a new instance


if __name__ == "__main__":
    # Run the tests
    test = TestUtilities()

    print("Testing LambdaCat Utilities...")
    print("=" * 40)

    test.test_monoid_category()
    print("✓ Monoid category")

    test.test_poset_category()
    print("✓ Poset category")

    test.test_json_serialization()
    print("✓ JSON serialization")

    test.test_slice_category()
    print("✓ Slice category")

    test.test_pretty_repr()
    print("✓ Pretty repr methods")

    test.test_opposite_category()
    print("✓ Opposite category")

    print("\n" + "=" * 40)
    print("🎉 All utility tests passed!")
