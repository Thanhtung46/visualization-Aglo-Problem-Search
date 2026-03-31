import time
from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)

class IDDFS8PuzzleEngine(BaseAlgorithmEngine):
    key = "iddfs"
    display_name = "Iterative Deepening DFS (IDDFS)"
    source_filename = "iddfs_algorithm.py"
    source_title = "IDDFS Algorithm Source"
    
    TRACE_PROGRAM = [
        "for limit from 0 to max_depth:",
        "  result = DLS(start, goal, limit)",
        "  if result == success: return result",
        "def DLS(current, goal, depth):",
        "  if depth == 0 and current == goal: return success",
        "  if depth > 0:",
        "    for neighbor in neighbors(current):",
        "      DLS(neighbor, goal, depth - 1)",
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.max_depth_limit = 50  # Safety limit to avoid infinite loops
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        return {
            "current_limit": 0,      # Current depth limit (L)
            "stack": [(state, 0)],   # Stores tuples of (state, current_depth)
            "parent": {state: None},
            "nodes_explored": 0,
            "finished": False,
            "solved": False,
            "start_time": None,
            "trace_history": [{"line": 0, "message": "Starting IDDFS with limit = 0", "nodes_explored": 0}],
        }

    def step(self):
        s = self.search_state
        if s["finished"]:
            return self._with_trace(
                {
                    "finished": True,
                    "success": s["solved"],
                    "current_state": list(GOAL_STATE if s["solved"] else self.initial_state),
                    "nodes_explored": s["nodes_explored"],
                },
                [],
            )

        if s["nodes_explored"] == 0:
            s["start_time"] = time.time()

        # If stack is empty, we finished exploring the current_limit without finding the goal
        if not s["stack"]:
            s["current_limit"] += 1
            if s["current_limit"] > self.max_depth_limit:
                s["finished"] = True
                return self._with_trace(
                    {
                        "finished": True,
                        "success": False,
                        "msg": "Depth limit exceeded",
                        "current_state": list(self.initial_state),
                        "nodes_explored": s["nodes_explored"],
                        "current_limit": s["current_limit"],
                    },
                    [],
                )
            
            # Reset to restart from the root with a larger depth limit
            s["stack"] = [(self.initial_state, 0)]
            s["parent"] = {self.initial_state: None}
            msg = f"Increasing depth limit to L = {s['current_limit']}. Restarting from root..."
            return self._with_trace(
                {
                    "finished": False,
                    "success": False,
                    "current_state": list(self.initial_state),
                    "nodes_explored": s["nodes_explored"],
                    "current_limit": s["current_limit"],
                    "frontier_size": len(s["stack"]),
                },
                [self._push_trace(0, msg)],
            )

        # Pop node from Stack (DFS behavior)
        current, depth = s["stack"].pop()
        s["nodes_explored"] += 1
        
        trace_step = [self._push_trace(4, f"Checking node at depth {depth}")]

        if current == GOAL_STATE:
            s["finished"] = True
            s["solved"] = True
            path = reconstruct_path(s["parent"], current)
            return self._with_trace({
                "current_state": list(current),
                "nodes_explored": s["nodes_explored"],
                "final_path": [list(x) for x in path],
                "finished": True,
                "success": True
            }, trace_step)

        # If we haven't reached the current depth limit, continue expanding
        if depth < s["current_limit"]:
            pushed = 0
            # To save memory, IDDFS usually only avoids cycles on the current path
            current_path = reconstruct_path(s["parent"], current)
            for neighbor in get_neighbors(current):
                if neighbor not in current_path:
                    s["parent"][neighbor] = current
                    s["stack"].append((neighbor, depth + 1))
                    pushed += 1
            trace_step.append(self._push_trace(7, f"Pushed {pushed} child node(s) to stack (depth {depth + 1})"))

        return self._with_trace({
            "current_state": list(current),
            "nodes_explored": s["nodes_explored"],
            "current_limit": s["current_limit"],
            "finished": False
        }, trace_step)

    def _push_trace(self, line, message):
        entry = {"line": line, "message": message, "nodes_explored": self.search_state["nodes_explored"]}
        self.search_state["trace_history"].append(entry)
        if len(self.search_state["trace_history"]) > 240:
            self.search_state["trace_history"] = self.search_state["trace_history"][-240:]
        return entry

    def _with_trace(self, payload, trace_step):
        payload["trace_step"] = trace_step
        payload["trace_history"] = self.search_state["trace_history"]
        payload["trace_program"] = self.TRACE_PROGRAM
        return payload

    def reset(self):
        """Reset the search state to the beginning"""
        self.search_state = self._build_initial_state(self.initial_state)
        return {
            "ok": True,
            "message": "Search state reset successfully",
            "current_state": list(self.initial_state),
            "trace_history": self.search_state["trace_history"],
            "trace_program": self.TRACE_PROGRAM,
        }

    def random_state(self):
        """Generate a random solvable puzzle and reset the engine"""
        self.initial_state = random_solvable_state()
        self.search_state = self._build_initial_state(self.initial_state)
        self._push_trace(0, "Generated a random solvable initial state.")
        return {
            "ok": True,
            "message": "Generated a random solvable puzzle",
            "current_state": list(self.initial_state),
            "trace_history": self.search_state["trace_history"],
            "trace_program": self.TRACE_PROGRAM,
        }

    def algorithm_source(self):
        return """def iddfs(start, goal):
    for depth in range(100):
        found, path = dls(start, goal, depth)
        if found: return path

def dls(current, goal, limit):
    if current == goal: return True, [current]
    if limit <= 0: return False, None
    for nb in get_neighbors(current):
        found, path = dls(nb, goal, limit - 1)
        if found: return True, [current] + path
    return False, None"""