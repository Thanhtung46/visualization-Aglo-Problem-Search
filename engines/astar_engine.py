import time
import heapq

from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)

def manhattan_distance(state):
    dist = 0
    for i, val in enumerate(state):
        if val == 0:
            continue
        target_r, target_c = (val - 1) // 3, (val - 1) % 3
        curr_r, curr_c = i // 3, i % 3
        dist += abs(target_r - curr_r) + abs(target_c - curr_c)
    return dist

class AStar8PuzzleEngine(BaseAlgorithmEngine):
    key = "astar"
    display_name = "A* Search"
    source_filename = "astar_algorithm.py"
    source_title = "A* Algorithm Source"
    TRACE_PROGRAM = [
        "if finished: return",
        "if pq empty: fail",
        "current = pq.heappop()",
        "if current == goal: success",
        "for neighbor in neighbors(current):",
        "  if new_g < g_score[neighbor]: update and push"
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        h_start = manhattan_distance(state)
        # PQ lưu tuple: (f_score, counter, state)
        # counter dùng để tie-break khi f_score bằng nhau
        return {
            "pq": [(h_start, 0, state)],
            "g_score": {state: 0},
            "parent": {state: None},
            "counter": 1, 
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
            trace_step.append(self._push_trace(0, "Search already finished."))
            return self._with_trace(
                {"finished": True, "success": self.search_state["solved"], "msg": "Search already finished"},
                trace_step,
            )

        if not self.search_state["pq"]:
            self.search_state["finished"] = True
            trace_step.append(self._push_trace(1, "PQ is empty -> no solution found."))
            return self._with_trace({"finished": True, "success": False, "msg": "No solution found"}, trace_step)

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        f_curr, _, current = heapq.heappop(self.search_state["pq"])
        trace_step.append(self._push_trace(2, f"Pop node with f={f_curr}"))
        self.search_state["nodes_explored"] += 1

        current_path = reconstruct_path(self.search_state["parent"], current)
        if current == GOAL_STATE:
            self.search_state["finished"] = True
            self.search_state["solved"] = True
            trace_step.append(self._push_trace(3, "Current node is GOAL -> finished."))
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
        current_g = self.search_state["g_score"][current]
        
        for neighbor in get_neighbors(current):
            tentative_g = current_g + 1
            if tentative_g < self.search_state["g_score"].get(neighbor, float('inf')):
                self.search_state["parent"][neighbor] = current
                self.search_state["g_score"][neighbor] = tentative_g
                f_score = tentative_g + manhattan_distance(neighbor)
                heapq.heappush(self.search_state["pq"], (f_score, self.search_state["counter"], neighbor))
                self.search_state["counter"] += 1
                pushed += 1
                
        trace_step.append(self._push_trace(5, f"Expand neighbors -> pushed {pushed} node(s)."))

        return self._with_trace(
            {
                "current_state": list(current),
                "current_path": [list(s) for s in current_path],
                "frontier_size": len(self.search_state["pq"]),
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
        return """
def astar_8puzzle(start, goal):
    pq = [(manhattan(start), 0, start)]
    g_score = {start: 0}
    parent = {start: None}
    counter = 1

    while pq:
        f, _, current = heapq.heappop(pq)

        if current == goal:
            return reconstruct_path(parent, current)

        for neighbor in get_neighbors(current):
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float('inf')):
                g_score[neighbor] = tentative_g
                parent[neighbor] = current
                f_score = tentative_g + manhattan(neighbor)
                heapq.heappush(pq, (f_score, counter, neighbor))
                counter += 1
    return None
"""