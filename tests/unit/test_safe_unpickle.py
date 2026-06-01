"""Security regression: cache deserialization must reject arbitrary classes.

Bug #170: `cached_vectorizer._get_from_cache` called bare `pickle.loads` on
data from Redis. A poisoned/compromised cache entry could execute arbitrary
code on load (pickle RCE). `safe_loads` must only reconstruct an allowlist of
builtin containers/scalars (+ numpy when present) and reject anything else.
"""

import pickle

import pytest

from mcli.lib.pickles.pickles import safe_loads


class _Evil:
    def __reduce__(self):
        # Classic pickle RCE gadget: would run os.system on load.
        import os

        return (os.system, ("echo pwned > /tmp/mcli_pwned_canary",))


def test_safe_loads_rejects_code_execution_gadget(tmp_path):
    payload = pickle.dumps(_Evil())
    with pytest.raises(pickle.UnpicklingError):
        safe_loads(payload)
    # The gadget must not have run.
    assert not (tmp_path / "mcli_pwned_canary").exists()
    import os

    assert not os.path.exists("/tmp/mcli_pwned_canary")


def test_safe_loads_rejects_arbitrary_class():
    class Foo:
        pass

    # Module-level pickling needs a top-level class; emulate with a known
    # dangerous global instead.
    payload = pickle.dumps(eval)  # builtin 'eval' is NOT in the allowlist
    with pytest.raises(pickle.UnpicklingError):
        safe_loads(payload)


@pytest.mark.parametrize(
    "value",
    [
        {"a": 1, "b": [1, 2, 3]},
        [1, 2.5, "x", True, None],
        ("t", 1, 2),
        {"nested": {"k": [1, 2, {"z": 9}]}},
    ],
)
def test_safe_loads_roundtrips_plain_containers(value):
    assert safe_loads(pickle.dumps(value)) == value


def test_safe_loads_roundtrips_numpy_if_available():
    np = pytest.importorskip("numpy")
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    out = safe_loads(pickle.dumps({"vec": arr}))
    assert np.array_equal(out["vec"], arr)
