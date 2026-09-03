from aistack.priority.cpu import cpus_equal, format_cpus


def test_equal_values_match():
    assert cpus_equal(3.0, 3.0) is True


def test_different_values_do_not_match():
    assert cpus_equal(3.0, 4.0) is False


def test_none_and_zero_are_the_same_unlimited_state():
    assert cpus_equal(None, 0.0) is True
    assert cpus_equal(0.0, None) is True


def test_none_and_none_match():
    assert cpus_equal(None, None) is True


def test_a_tiny_rounding_difference_still_matches():
    """
    `docker inspect` answers in nanocpus; converting back can lose
    the last bit or two of a decimal like 0.1. The smallest real
    gap between two governed values is 0.1 core, so an epsilon well
    below that absorbs rounding without hiding an actual change.
    """

    assert cpus_equal(0.1, 0.1 + 1e-9) is True


def test_a_real_difference_below_one_core_still_does_not_match():
    assert cpus_equal(0.1, 0.2) is False


def test_format_cpus_trims_the_trailing_zero():
    assert format_cpus(3.0) == "3"
    assert format_cpus(0.5) == "0.5"
    assert format_cpus(0.1) == "0.1"


def test_format_cpus_of_none_is_dockers_own_unlimited_value():
    assert format_cpus(None) == "0"
