from problem_time.aggregate import geometric_mean, median_time
from problem_time.clean import adopt_primary, clean_if_geo_median_diverge, relative_gap


def test_no_clean_when_close():
    values = [10.0, 11.0, 9.5, 10.5, 10.2, 9.8, 10.1, 10.3, 9.9, 10.4]
    result = clean_if_geo_median_diverge(values, gap_threshold=0.25)
    assert result.triggered is False
    assert list(result.values) == values


def test_clean_when_outlier_blows_geo():
    values = [10.0, 11.0, 9.5, 10.5, 10.2, 9.8, 10.1, 10.3, 9.9, 1000.0]
    gap = relative_gap(geometric_mean(values), median_time(values))
    assert gap >= 0.25
    primary, cleaned = adopt_primary(values, gap_threshold=0.25)
    assert cleaned.triggered is True
    assert 1000.0 in cleaned.removed
    assert primary < geometric_mean(values)
