import pytest
from Django_app.AI_Trip_Planner.utils.Expense_calculator import Calculator


class TestMultiply:
    def test_basic_multiplication(self):
        assert Calculator.multiply(3, 4) == 12

    def test_multiply_by_zero(self):
        assert Calculator.multiply(100, 0) == 0

    def test_multiply_floats(self):
        assert Calculator.multiply(2.5, 4) == 10.0


class TestCalculateTotal:
    def test_sums_multiple_costs(self):
        assert Calculator.calculate_total(100, 250.5, 30) == 380.5

    def test_no_costs_returns_zero(self):
        assert Calculator.calculate_total() == 0

    def test_single_cost(self):
        assert Calculator.calculate_total(42) == 42


class TestCalculateDailyBudget:
    def test_even_split(self):
        assert Calculator.calculate_daily_budget(1000, 5) == 200

    def test_zero_days_returns_zero_instead_of_dividing_by_zero(self):
        # Calculator.calculate_daily_budget guards against ZeroDivisionError;
        # this pins that behavior down so it can't regress silently.
        assert Calculator.calculate_daily_budget(500, 0) == 0

    def test_fractional_result(self):
        assert Calculator.calculate_daily_budget(100, 3) == pytest.approx(33.333, rel=1e-3)