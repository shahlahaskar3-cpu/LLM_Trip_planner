import os
from unittest.mock import patch, MagicMock

import pytest

# Direct top-level import (not through mock.patch's string-based resolver).
# If this raises, pytest will show the REAL underlying ImportError traceback
# during collection, instead of mock.patch's misleading generic AttributeError.
from Django_app.AI_Trip_Planner.Agent import agentic_workflow  # noqa: F401


def _build_graph_builder_with_mocked_deps():
    """
    Constructs a GraphBuilder with every external dependency mocked out, so
    no real API keys or network calls are needed. Returns the instance with
    `llm_with_tools` ready to be replaced by the caller for retry testing.
    """
    with patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.ModelLoader") as mock_loader_cls, \
         patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.WeatherInfoTool") as mock_weather_cls, \
         patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.PlaceSearchTool") as mock_place_cls, \
         patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.CalculatorTool") as mock_calc_cls, \
         patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.CurrencyConverter") as mock_currency_cls:

        mock_weather_cls.return_value.weather_tool_list = []
        mock_place_cls.return_value.place_search_tool_list = []
        mock_calc_cls.return_value.calculator_tool_list = []
        mock_currency_cls.return_value.currency_converter_tool_list = []

        mock_llm_instance = MagicMock()
        mock_loader_cls.return_value.load_llm.return_value = mock_llm_instance

        from Django_app.AI_Trip_Planner.Agent.agentic_workflow import GraphBuilder

        builder = GraphBuilder(model_provider="groq")

    return builder


class TestGraphBuilderConstruction:
    def test_graph_builder_merges_all_four_tool_lists(self):
        with patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.ModelLoader") as mock_loader_cls, \
             patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.WeatherInfoTool") as mock_weather_cls, \
             patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.PlaceSearchTool") as mock_place_cls, \
             patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.CalculatorTool") as mock_calc_cls, \
             patch("Django_app.AI_Trip_Planner.Agent.agentic_workflow.CurrencyConverter") as mock_currency_cls:

            mock_weather_cls.return_value.weather_tool_list = ["weather_tool_1", "weather_tool_2"]
            mock_place_cls.return_value.place_search_tool_list = ["place_tool_1"]
            mock_calc_cls.return_value.calculator_tool_list = ["calc_tool_1"]
            mock_currency_cls.return_value.currency_converter_tool_list = ["currency_tool_1"]
            mock_loader_cls.return_value.load_llm.return_value = MagicMock()

            from Django_app.AI_Trip_Planner.Agent.agentic_workflow import GraphBuilder

            builder = GraphBuilder(model_provider="groq")

        # Regression test confirming all four tool wrappers correctly expose
        # their tool lists and get merged - protects against future wiring
        # mistakes if any of these classes are refactored.
        assert builder.tools == [
            "weather_tool_1",
            "weather_tool_2",
            "place_tool_1",
            "calc_tool_1",
            "currency_tool_1",
        ]


class TestAgentFunctionRetryLogic:
    def test_agent_function_returns_response_on_first_success(self):
        builder = _build_graph_builder_with_mocked_deps()
        fake_response = MagicMock()
        builder.llm_with_tools = MagicMock()
        builder.llm_with_tools.invoke.return_value = fake_response

        result = builder.agent_function({"messages": ["Plan a trip to Goa"]})

        assert result == {"messages": [fake_response]}
        builder.llm_with_tools.invoke.assert_called_once()

    def test_agent_function_retries_once_on_tool_use_failed_then_succeeds(self):
        builder = _build_graph_builder_with_mocked_deps()
        fake_response = MagicMock()
        builder.llm_with_tools = MagicMock()
        builder.llm_with_tools.invoke.side_effect = [
            Exception("tool_use_failed: malformed function call"),
            fake_response,
        ]

        result = builder.agent_function({"messages": ["Plan a trip to Goa"]})

        assert result == {"messages": [fake_response]}
        assert builder.llm_with_tools.invoke.call_count == 2

    def test_agent_function_retries_on_failed_to_call_a_function_message(self):
        builder = _build_graph_builder_with_mocked_deps()
        fake_response = MagicMock()
        builder.llm_with_tools = MagicMock()
        builder.llm_with_tools.invoke.side_effect = [
            Exception("Failed to call a function: bad arguments"),
            fake_response,
        ]

        result = builder.agent_function({"messages": ["Plan a trip to Goa"]})

        assert result == {"messages": [fake_response]}
        assert builder.llm_with_tools.invoke.call_count == 2

    def test_agent_function_raises_last_error_after_exhausting_retries(self):
        builder = _build_graph_builder_with_mocked_deps()
        builder.llm_with_tools = MagicMock()
        # max_retries = 2, so range(max_retries + 1) = 3 total attempts
        builder.llm_with_tools.invoke.side_effect = [
            Exception("tool_use_failed: attempt 1"),
            Exception("tool_use_failed: attempt 2"),
            Exception("tool_use_failed: attempt 3"),
        ]

        with pytest.raises(Exception, match="attempt 3"):
            builder.agent_function({"messages": ["Plan a trip to Goa"]})

        assert builder.llm_with_tools.invoke.call_count == 3

    def test_agent_function_raises_immediately_on_unrelated_error(self):
        # A non-tool-call error (e.g. auth failure, rate limit) should not be
        # retried - it should propagate on the first attempt.
        builder = _build_graph_builder_with_mocked_deps()
        builder.llm_with_tools = MagicMock()
        builder.llm_with_tools.invoke.side_effect = Exception("401 Unauthorized")

        with pytest.raises(Exception, match="401 Unauthorized"):
            builder.agent_function({"messages": ["Plan a trip to Goa"]})

        builder.llm_with_tools.invoke.assert_called_once()


@pytest.mark.skipif(
    os.environ.get("RUN_LLM_SMOKE_TESTS") != "1",
    reason=(
        "Real-API smoke test - calls the actual Groq API and costs quota. "
        "Skipped by default in CI. Run locally with: "
        "RUN_LLM_SMOKE_TESTS=1 pytest tests/test_agentic_workflow.py -v"
    ),
)
class TestGraphBuilderRealSmoke:
    def test_real_trip_question_returns_nonempty_answer(self):
        """
        End-to-end smoke test against the real Groq API and real tools.
        Does not assert exact wording (LLM output isn't deterministic) -
        only checks the pipeline runs without crashing and returns a
        reasonable-looking answer.
        """
        from Django_app.AI_Trip_Planner.Agent.agentic_workflow import GraphBuilder

        graph = GraphBuilder(model_provider="groq")
        app = graph.build_graph()

        output = app.invoke({"messages": ["Plan a 2 day trip to Kochi"]})

        assert "messages" in output
        final_message = output["messages"][-1].content

        assert isinstance(final_message, str)
        assert len(final_message) > 100  # a real itinerary should not be a one-liner
        assert "kochi" in final_message.lower() or "Kochi" in final_message