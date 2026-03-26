import time
import heapq # Sử dụng Priority Queue cho UCS
from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)

class UCS8PuzzleEngine(BaseAlgorithmEngine):
    key = "ucs"
    display_name = "Uniform Cost Search (UCS)"
    source_filename = "ucs_algorithm.py"
    source_title = "UCS Algorithm Source"
    
    # Trace program cập nhật để phản ánh logic của UCS (Priority Queue)
    TRACE_PROGRAM = [
        "if finished: return",
        "if priority_queue empty: fail",
        "cost, current = heapq.heappop(pq)",
        "if current == goal: success",
        "for neighbor in neighbors(current):",
        "  new_cost = cost + 1",
        "  if new_cost < best_cost: push to pq",
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        # Trong UCS, queue lưu tuple: (cost, state)
        # heapq mặc định sẽ ưu tiên giá trị cost nhỏ nhất lên đầu
        pq = []
        heapq.heappush(pq, (0, state))
        
        return {
            "queue": pq,
            "seen": {state: 0}, # Lưu trạng thái và chi phí thấp nhất tìm thấy
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
            trace_step.append(self._push_trace(0, "Search already finished."))
            return self._with_trace(
                {"finished": True, "success": self.search_state["solved"], "msg": "Search already finished"},
                trace_step,
            )

        if not self.search_state["queue"]:
            self.search_state["finished"] = True
            trace_step.append(self._push_trace(1, "Priority Queue is empty -> no solution found."))
            return self._with_trace({"finished": True, "success": False, "msg": "No solution found"}, trace_step)

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        # UCS lấy node có cost thấp nhất
        cost, current = heapq.heappop(self.search_state["queue"])
        
        trace_step.append(self._push_trace(2, f"Pop node with lowest cost ({cost}): {list(current)}"))
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
        new_cost = cost + 1
        for neighbor in get_neighbors(current):
            # Nếu chưa thấy neighbor hoặc tìm thấy đường đi rẻ hơn
            if neighbor not in self.search_state["seen"] or new_cost < self.search_state["seen"][neighbor]:
                self.search_state["seen"][neighbor] = new_cost
                self.search_state["parent"][neighbor] = current
                heapq.heappush(self.search_state["queue"], (new_cost, neighbor))
                pushed += 1
        
        trace_step.append(self._push_trace(6, f"Expand neighbors with cost {new_cost} -> pushed {pushed} node(s)."))

        return self._with_trace(
            {
                "current_state": list(current),
                "current_path": [list(s) for s in current_path],
                "frontier_size": len(self.search_state["queue"]),
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
        return """import heapq

def ucs_8puzzle(start, goal):
    # queue contains (cost, state)
    pq = [(0, start)]
    visited = {start: 0}
    parent = {start: None}

    while pq:
        cost, current = heapq.heappop(pq)

        if current == goal:
            return reconstruct_path(parent, current)

        for neighbor in get_neighbors(current):
            new_cost = cost + 1
            if neighbor not in visited or new_cost < visited[neighbor]:
                visited[neighbor] = new_cost
                parent[neighbor] = current
                heapq.heappush(pq, (new_cost, neighbor))

    return None
"""