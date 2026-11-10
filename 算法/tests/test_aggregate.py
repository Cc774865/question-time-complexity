from problem_time.aggregate import geometric_mean, median_time, summarize


def test_geometric_mean_basic():
    assert abs(geometric_mean([1.0, 4.0]) - 2.0) < 1e-12


def test_median_odd_even():
    assert median_time([1.0, 3.0, 2.0]) == 2.0
    assert median_time([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_summarize_keys():
    s = summarize([1.0, 2.0, 4.0])
    assert "geo" in s and "median" in s and "n" in s
    assert s["n"] == 3.0
