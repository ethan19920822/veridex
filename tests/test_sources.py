from veridex.sources.australia import source_specs


def test_unique_source_keys():
    specs = source_specs()
    keys = [s.key for s in specs]
    assert len(keys) == len(set(keys))
    assert {s.regulator for s in specs} == {"AUSTRAC", "APRA", "ASIC"}
