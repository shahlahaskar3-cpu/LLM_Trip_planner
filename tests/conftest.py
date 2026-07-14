import os
import sys

# AI_Trip_Planner/Tools and AI_Trip_Planner/utils use absolute imports like
# "from utils.calculator import Calculator", which only resolve if the
# AI_Trip_Planner/ directory itself is on sys.path (same trick settings.py
# does for the Django app). Do the same here so `pytest` works standalone.
_TRIP_PLANNER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TRIP_PLANNER_DIR not in sys.path:
    sys.path.insert(0, _TRIP_PLANNER_DIR)

    