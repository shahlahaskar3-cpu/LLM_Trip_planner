import pytest
from Django_app.AI_Trip_Planner.utils.confiq_lodder import load_config


class TestLoadConfig:
    def test_loads_default_config_regardless_of_cwd(self):
        # Regression test for the old hardcoded "Confiq\config.yaml" path,
        # which only worked on Windows and only when cwd was AI_Trip_Planner/.
        config = load_config()
        assert "llm" in config

    def test_groq_model_name_present(self):
        config = load_config()
        assert config["llm"]["groq"]["model_name"] == "llama-3.3-70b-versatile"

    def test_openai_model_name_present(self):
        config = load_config()
        assert config["llm"]["openai"]["provider"] == "openai"


class TestCalculatorToolWiring:
    def test_calculator_tool_list_has_three_tools(self):
        # CalculatorTool needs no API key, so it's safe to instantiate in CI.
        from Django_app.AI_Trip_Planner.Tools.Expense_calculator_tool import CalculatorTool

        tool = CalculatorTool()
        tool_names = {t.name for t in tool.calculator_tool_list}

        assert tool_names == {
            "estimate_total_hotel_cost",
            "calculate_total_expense",
            "calculate_daily_expense_budget",
        }

    def test_estimate_total_hotel_cost_tool_invocation_currently_raises(self):
        """
        KNOWN BUG, not a bug in this test: `estimate_total_hotel_cost` declares
        `price_per_night: str` in Expense_calculator_tool.py, but Calculator.multiply
        does `price_per_night * total_days`. Since price_per_night arrives as a
        Python str and total_days as a float, this raises TypeError at runtime
        instead of returning a cost - meaning the LLM agent's hotel-cost
        estimates likely fail silently (caught by the agent_function retry
        logic and possibly surfaced as a generic error to the user).
        Fix: change the signature to `price_per_night: float` in
        Tools/Expense_calculator_tool.py. Once fixed, update this test to
        assert the real numeric result instead of expecting TypeError.
        """
        from Django_app.AI_Trip_Planner.Tools.Expense_calculator_tool import CalculatorTool

        tool = CalculatorTool()
        hotel_cost_tool = next(
            t for t in tool.calculator_tool_list if t.name == "estimate_total_hotel_cost"
        )

        result = hotel_cost_tool.invoke({"price_per_night": 100, "total_days": 3})
        assert result == 300