import time

from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
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

class IDAStar8PuzzleEngine(BaseAlgorithmEngine):
    key = "idastar"
    display_name = "IDA* Search"
    source_filename = "idastar_algorithm.py"
    source_title = "IDA* Algorithm Source"
    TRACE_PROGRAM = [
        "if stack empty: update threshold, restart",
        "current, g, path = stack.pop()",
        "f = g + h(current)",
        "if f > threshold: update min_exceeded, prune",
        "if current == goal: success",
        "for neighbor in neighbors: push to stack"
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        initial_h = manhattan_distance(state)
        return {
            "threshold": initial_h,
            "min_exceeded": float('inf'),
            "stack": [(state, 0, [state])], # (current_state, g_cost, path_so_far)
            "finished": False,
            "solved": False,
            "start_time": None,
            "nodes_explored": 0,
            "trace_history": [{"line": 0, "message": f"Start with threshold={initial_h}", "nodes_explored": 0}],
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

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        # Nếu stack rỗng tức là duyệt xong một ngưỡng f-limit
        if not self.search_state["stack"]:
            if self.search_state["min_exceeded"] == float('inf'):
                self.search_state["finished"] = True
                trace_step.append(self._push_trace(0, "No solution found."))
                return self._with_trace({"finished": True, "success": False, "msg": "No solution found"}, trace_step)
            
            # Tăng threshold lên mức f-score vượt giới hạn nhỏ nhất
            new_threshold = self.search_state["min_exceeded"]
            self.search_state["threshold"] = new_threshold
            self.search_state["min_exceeded"] = float('inf')
            self.search_state["stack"] = [(self.initial_state, 0, [self.initial_state])]
            trace_step.append(self._push_trace(0, f"Iteration done. New threshold={new_threshold}"))
            
            return self._with_trace(
                {
                    "current_state": list(self.initial_state),
                    "current_path": [list(self.initial_state)],
                    "frontier_size": len(self.search_state["stack"]),
                    "nodes_explored": self.search_state["nodes_explored"],
                    "finished": False,
                },
                trace_step,
            )

        current, g, path = self.search_state["stack"].pop()
        self.search_state["nodes_explored"] += 1
        f = g + manhattan_distance(current)
        
        trace_step.append(self._push_trace(1, f"Pop node, f={f}, threshold={self.search_state['threshold']}"))

        if f > self.search_state["threshold"]:
            self.search_state["min_exceeded"] = min(self.search_state["min_exceeded"], f)
            trace_step.append(self._push_trace(3, "f > threshold -> Pruned."))
            return self._with_trace(
                {
                    "current_state": list(current),
                    "current_path": [list(s) for s in path],
                    "frontier_size": len(self.search_state["stack"]),
                    "nodes_explored": self.search_state["nodes_explored"],
                    "finished": False,
                },
                trace_step,
            )

        if current == GOAL_STATE:
            self.search_state["finished"] = True
            self.search_state["solved"] = True
            trace_step.append(self._push_trace(4, "Current node is GOAL -> finished."))
            return self._with_trace(
                {
                    "current_state": list(current),
                    "nodes_explored": self.search_state["nodes_explored"],
                    "processing_time": f"{time.time() - self.search_state['start_time']:.4f}s",
                    "final_path": [list(s) for s in path],
                    "finished": True,
                    "success": True,
                },
                trace_step,
            )

        # Duyệt hàng xóm ngược lại để mô phỏng DFS trái-sang-phải khi dùng Stack
        neighbors = get_neighbors(current)
        pushed = 0
        for neighbor in reversed(neighbors):
            if neighbor not in path: # Chống lặp trạng thái trên cùng 1 nhánh
                new_path = path + [neighbor]
                self.search_state["stack"].append((neighbor, g + 1, new_path))
                pushed += 1
                
        trace_step.append(self._push_trace(5, f"Expand neighbors -> pushed {pushed} node(s)."))

        return self._with_trace(
            {
                "current_state": list(current),
                "current_path": [list(s) for s in path],
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
        return """def idastar_8puzzle(start, goal):
    threshold = manhattan_distance(start)
    
    while True:
        # Stack stores: (state, g_cost, path)
        stack = [(start, 0, [start])]
        min_exceeded = float('inf')
        
        while stack:
            current, g, path = stack.pop()
            f = g + manhattan_distance(current)
            
            if f > threshold:
                min_exceeded = min(min_exceeded, f)
                continue
                
            if current == goal:
                return path
                
            for neighbor in reversed(get_neighbors(current)):
                if neighbor not in path:
                    stack.append((neighbor, g + 1, path + [neighbor]))
                    
        if min_exceeded == float('inf'):
            return None
        threshold = min_exceeded
"""