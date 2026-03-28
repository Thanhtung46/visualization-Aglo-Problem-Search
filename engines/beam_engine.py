import time
from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)

def calculate_F(state):
    """Hàm Heuristic (F): Tính khoảng cách Manhattan cho 8-puzzle"""
    dist = 0
    for i, val in enumerate(state):
        if val != 0:
            tr, tc = (val - 1) // 3, (val - 1) % 3
            r, c = i // 3, i % 3
            dist += abs(tr - r) + abs(tc - c)
    return dist

class BeamSearch8PuzzleEngine(BaseAlgorithmEngine):
    key = "beam"
    display_name = "Beam Search"
    source_filename = "beam_algorithm.py"
    source_title = "Beam Search Source"

    TRACE_PROGRAM = [
        "if finished: return",
        "if current_level empty:",
        "  if next_level empty: fail",
        "  sort next_level by F, keep top W (Beam Width)",
        "  current_level = next_level; next_level = empty",
        "current = current_level.pop(0)",
        "if current == goal: success",
        "expand neighbors -> add to next_level"
    ]

    def __init__(self, beam_width=3):
        self.beam_width = beam_width
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        return {
            "current_level": [state],
            "next_level": [],
            "seen": {state: None}, # parent map
            "finished": False,
            "solved": False,
            "start_time": None,
            "nodes_explored": 0,
            "trace_history": [{"line": 0, "message": f"Reset search state (Beam width: {self.beam_width}).", "nodes_explored": 0}],
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
            return self._with_trace({"finished": True, "success": self.search_state["solved"], "msg": "Finished"}, trace_step)

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        # Chuyển level nếu level hiện tại đã mở rộng xong
        if not self.search_state["current_level"]:
            trace_step.append(self._push_trace(1, "Current level is empty."))
            if not self.search_state["next_level"]:
                self.search_state["finished"] = True
                trace_step.append(self._push_trace(2, "Next level is also empty -> no solution found."))
                return self._with_trace({"finished": True, "success": False, "msg": "No solution"}, trace_step)

            # Sắp xếp theo hàm F và tỉa (prune) giữ lại K node tốt nhất
            self.search_state["next_level"].sort(key=calculate_F)
            self.search_state["current_level"] = self.search_state["next_level"][:self.beam_width]
            self.search_state["next_level"] = []
            trace_step.append(self._push_trace(3, f"Pruned to {len(self.search_state['current_level'])} nodes based on F."))
            trace_step.append(self._push_trace(4, "Switched to new level."))

        current = self.search_state["current_level"].pop(0)
        self.search_state["nodes_explored"] += 1
        trace_step.append(self._push_trace(5, f"Pop node (F={calculate_F(current)}): {list(current)}"))

        if current == GOAL_STATE:
            self.search_state["finished"] = True
            self.search_state["solved"] = True
            path = reconstruct_path(self.search_state["seen"], current)
            trace_step.append(self._push_trace(6, "Current node is GOAL -> finished."))
            return self._with_trace({
                "current_state": list(current),
                "nodes_explored": self.search_state["nodes_explored"],
                "processing_time": f"{time.time() - self.search_state['start_time']:.4f}s",
                "final_path": [list(s) for s in path],
                "finished": True,
                "success": True,
            }, trace_step)

        # Mở rộng các state con
        pushed = 0
        for neighbor in get_neighbors(current):
            if neighbor not in self.search_state["seen"]:
                self.search_state["seen"][neighbor] = current
                self.search_state["next_level"].append(neighbor)
                pushed += 1
        
        trace_step.append(self._push_trace(7, f"Expanded {pushed} neighbors to next_level candidates."))

        return self._with_trace(
            {
                "current_state": list(current),
                "frontier_size": len(self.search_state["current_level"]) + len(self.search_state["next_level"]),
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
            "current_state": list(self.initial_state),
            "trace_history": self.search_state["trace_history"],
            "trace_program": self.TRACE_PROGRAM,
        }

    def random_state(self):
        self.initial_state = random_solvable_state()
        self.search_state = self._build_initial_state(self.initial_state)
        return self.reset()

    def algorithm_source(self):
        return """def beam_search_8puzzle(start, goal, beam_width=3):
    # Hàm F tính Manhattan distance
    pass
"""