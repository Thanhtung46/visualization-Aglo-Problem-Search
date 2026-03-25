import time

from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)


class DFS8PuzzleEngine(BaseAlgorithmEngine):
    key = "dfs"
    display_name = "Depth-First Search (DFS)"
    source_filename = "dfs_algorithm.py"
    source_title = "DFS Algorithm Source"
    TRACE_PROGRAM = [
        "if finished: return",
        "if stack empty: fail",
        "current = stack.pop()",
        "if current == goal: success",
        "for neighbor in reversed(neighbors(current)): push unseen",
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        return {
            "stack": [state],
            "seen": {state},
            "parent": {state: None},
            "finished": False,
            "solved": False,
            "start_time": None,
            "nodes_explored": 0,
            "trace_history": [{"line": 0, "message": "Reset search state.", "nodes_explored": 0}],
        }

    def _push_trace(self, line, message):
        entry = {"line": line, "message": message, "nodes_explored": self.search_state["nodes_explored"]}
        self.search_state["trace_history"].append(entry)
        if len(self.search_state["trace_history"]) > 240:
            self.search_state["trace_history"] = self.search_state["trace_history"][-240:]
        return entry

    def step(self):
        trace_step = []
        if self.search_state["finished"]:
            trace_step.append(self._push_trace(1, "Search already finished."))
            return self._with_trace(
                {"finished": True, "success": self.search_state["solved"], "msg": "Search already finished"},
                trace_step,
            )

        if not self.search_state["stack"]:
            self.search_state["finished"] = True
            trace_step.append(self._push_trace(2, "Stack is empty -> no solution found."))
            return self._with_trace({"finished": True, "success": False, "msg": "No solution found"}, trace_step)

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        current = self.search_state["stack"].pop()
        trace_step.append(self._push_trace(3, f"Pop current node: {list(current)}"))
        self.search_state["nodes_explored"] += 1

        current_path = reconstruct_path(self.search_state["parent"], current)
        if current == GOAL_STATE:
            self.search_state["finished"] = True
            self.search_state["solved"] = True
            trace_step.append(self._push_trace(4, "Current node is GOAL -> finished."))
            return self._with_trace(
                {
                    "current_state": list(current),
                    "nodes_explored": self.search_state["nodes_explored"],
                    "processing_time": f"{time.time() - self.search_state['start_time']:.4f}s",
                    "final_path": [list(s) for s in current_path],
                    "finished": True,
                    "success": True,
                },
                trace_step,
            )

        pushed = 0
        for neighbor in reversed(get_neighbors(current)):
            if neighbor not in self.search_state["seen"]:
                self.search_state["seen"].add(neighbor)
                self.search_state["parent"][neighbor] = current
                self.search_state["stack"].append(neighbor)
                pushed += 1
        trace_step.append(self._push_trace(5, f"Expand neighbors -> pushed {pushed} node(s)."))

        return self._with_trace(
            {
                "current_state": list(current),
                "current_path": [list(s) for s in current_path],
                "frontier_size": len(self.search_state["stack"]),
                "nodes_explored": self.search_state["nodes_explored"],
                "finished": False,
            },
            trace_step,
        )

    def _with_trace(self, payload, trace_step):
        payload["trace_step"] = trace_step
        payload["trace_history"] = self.search_state["trace_history"]
        payload["trace_program"] = self.TRACE_PROGRAM
        return payload

    def reset(self):
        self.search_state = self._build_initial_state(self.initial_state)
        return {
            "ok": True,
            "message": "Search state reset successfully",
            "current_state": list(self.initial_state),
            "trace_history": self.search_state["trace_history"],
            "trace_program": self.TRACE_PROGRAM,
        }

    def random_state(self):
        self.initial_state = random_solvable_state()
        self.search_state = self._build_initial_state(self.initial_state)
        self._push_trace(0, "Generate random solvable initial state.")
        return {
            "ok": True,
            "message": "Generated a random solvable puzzle",
            "current_state": list(self.initial_state),
            "trace_history": self.search_state["trace_history"],
            "trace_program": self.TRACE_PROGRAM,
        }

    def algorithm_source(self):
        return """def dfs_8puzzle(start, goal):
    stack = [start]
    visited = {start}
    parent = {start: None}

    while stack:
        current = stack.pop()

        if current == goal:
            return reconstruct_path(parent, current)

        for neighbor in get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    return None
"""
