from veridex.text import content_hash, line_diff, normalize_text


def test_normalize_stable():
    assert normalize_text("A   B\n\n C") == "A B\nC"


def test_hash_stable_after_whitespace_normalization():
    a = normalize_text("hello   world")
    b = normalize_text("hello world")
    assert content_hash(a) == content_hash(b)


def test_diff_detects_change():
    diff = line_diff("Rule A\nOld", "Rule A\nNew")
    assert "-Old" in diff
    assert "+New" in diff
