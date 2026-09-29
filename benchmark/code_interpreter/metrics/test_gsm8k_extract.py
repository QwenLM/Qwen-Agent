from metrics.gsm8k import extract_answer, is_correct


def test_a_decimal_ending_in_zero_keeps_the_fraction():
    assert extract_answer('result 1.50') == 1.5
    assert extract_answer('result 0.50') == 0.5
    assert is_correct('answer is 1.50', 'answer is 1') is False
    assert extract_answer('result 1.5') == 1.5
    assert extract_answer('answer 42') == 42
