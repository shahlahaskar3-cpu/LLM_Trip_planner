from AI_Trip_Planner.utils.model_loader import ModelLoader
from AI_Trip_Planner.Prompt_library.prompt import SYSTEM_PROMPT
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from ..Tools.weather_search_tool import WeatherInfoTool
from ..Tools.place_info_tool import PlaceSearchTool
from ..Tools.Expense_calculator_tool import CalculatorTool
from ..utils.corrency_converter import CurrencyConverter


class GraphBuilder():
    def __init__(self, model_provider: str = "groq"):
        self.model_loader = ModelLoader(model_provider=model_provider)
        self.llm = self.model_loader.load_llm()

        self.tools = []

        self.weather_tools = WeatherInfoTool()
        self.place_search_tools = PlaceSearchTool()
        self.calculator_tools = CalculatorTool()
        self.currency_converter_tools = CurrencyConverter()

        self.tools.extend([*self.weather_tools.weather_tool_list,
                            *self.place_search_tools.place_search_tool_list,
                            *self.calculator_tools.calculator_tool_list,
                            *self.currency_converter_tools.currency_converter_tool_list])

        self.llm_with_tools = self.llm.bind_tools(tools=self.tools)

        self.graph = None
        self.system_prompt = SYSTEM_PROMPT

    def agent_function(self, state: MessagesState):
        """Main agent function, with retry on malformed tool-call generations."""
        user_question = state["messages"]
        input_question = [self.system_prompt] + user_question

        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = self.llm_with_tools.invoke(input_question)
                return {"messages": [response]}
            except Exception as e:
                # Groq/Llama sometimes emits a text-based fake function call
                # instead of a real structured tool call ("tool_use_failed").
                # A retry often succeeds since generation isn't deterministic.
                if "tool_use_failed" in str(e) or "Failed to call a function" in str(e):
                    last_error = e
                    continue
                raise

        # All retries exhausted: raise the last tool-call error so the
        # Django view's try/except can still show a clean message to the user.
        raise last_error

    def build_graph(self):
        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node("agent", self.agent_function)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_edge(START, "agent")
        graph_builder.add_conditional_edges("agent", tools_condition)
        graph_builder.add_edge("tools", "agent")
        graph_builder.add_edge("agent", END)
        self.graph = graph_builder.compile()
        return self.graph

    def __call__(self):
        return self.build_graph()