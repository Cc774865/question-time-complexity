from problem_time.stars import LevelsBeforeStarsError, assign_levels, assign_stars, pair_tau


def test_pair_tau_uses_mean_below_gap() -> None:
    row = pair_tau(0.942927, 0.942927)
    assert row["pair_rule"] == "mean"
    assert abs(row["tau_set"] - 0.942927) < 1e-12


def test_pair_tau_uses_higher_at_gap() -> None:
    row = pair_tau(0.998693, 0.960283)
    assert row["gap"] >= 0.03
    assert row["pair_rule"] == "higher"
    assert abs(row["tau_set"] - 0.998693) < 1e-12


def test_stars_follow_ascending_pair_tau() -> None:
    # W3-L5L6-4 的七对。原文件上的编号只用来核对，不参加排序。
    pairs = [
        {"pair_id": "同分母看图", "tau_example": 0.865536, "tau_practice": 0.891143},
        {"pair_id": "通分四组", "tau_example": 0.924433, "tau_practice": 0.918600},
        {"pair_id": "分数尺", "tau_example": 0.942927, "tau_practice": 0.942927},
        {"pair_id": "直接写得数", "tau_example": 0.950893, "tau_practice": 0.933680},
        {"pair_id": "脱式", "tau_example": 0.998693, "tau_practice": 0.960283},
        {"pair_id": "选算式", "tau_example": 1.006944, "tau_practice": 0.972517},
        {"pair_id": "单位1连减", "tau_example": 0.909353, "tau_practice": 0.909353},
    ]
    ranked = assign_stars(pairs)
    by_star = {row["star"]: row["pair_id"] for row in ranked}
    assert [by_star[star] for star in range(2, 9)] == [
        "同分母看图",
        "单位1连减",
        "通分四组",
        "直接写得数",
        "分数尺",
        "脱式",
        "选算式",
    ]
    assert ranked[4]["pair_rule"] == "higher"
    assert ranked[5]["pair_rule"] == "higher"


def test_levels_require_finished_stars_and_follow_content() -> None:
    ranked = assign_stars([
        {"pair_id": str(i), "tau_example": 0.8 + i * 0.04, "tau_practice": 0.8 + i * 0.04}
        for i in range(7)
    ])
    try:
        assign_levels([{"similar_star": 6}], "homework", [])
        raise AssertionError("empty stars must be refused")
    except LevelsBeforeStarsError:
        pass
    homework = assign_levels(
        [{"similar_star": 6}, {"similar_star": 5}, {"similar_star": 8}, {"similar_star": 3}],
        "homework",
        ranked,
    )
    assert [row["level"] for row in homework] == ["AAA", "AA", "S", "B"]
    assert homework[0]["stars"] == (5, 6)
    promotion = assign_levels([{"similar_star": 7}], "promotion", ranked)
    assert promotion[0]["level"] is None
    assert promotion[0]["rejected"] == "晋级赛没有 S 级"
