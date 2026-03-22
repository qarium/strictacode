from strictacode.calc.score import calculate, Metric


class TestCalculateNegativeInputs:
    def test_negative_inputs_with_imbalance(self):
        """Negative rp/oe with imbalance enabled should not crash."""
        result = calculate(
            rp=-50,
            oe=50,
            complexity_density=10.0,
            use_imbalance=True,
        )
        assert isinstance(result, Metric)
