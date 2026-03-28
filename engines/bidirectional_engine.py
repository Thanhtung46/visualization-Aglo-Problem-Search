import time
from collections import deque
from engines.base_engine import BaseAlgorithmEngine
from engines.puzzle_common import (
    DEFAULT_INITIAL_STATE,
    GOAL_STATE,
    get_neighbors,
    random_solvable_state,
    reconstruct_path,
)

class Bidirectional8PuzzleEngine(BaseAlgorithmEngine):
    key = "bidirectional"
    display_name = "Bidirectional Search"
    source_filename = "bidirectional_algorithm.py"
    source_title = "Bidirectional Search Source"

    TRACE_PROGRAM = [
        "if finished: return",
        "if fwd_queue empty or bwd_queue empty: fail",
        "fwd_curr = fwd_queue.popleft()",
        "if fwd_curr in bwd_seen: success (intersected)",
        "expand neighbors for fwd_curr",
        "bwd_curr = bwd_queue.popleft()",
        "if bwd_curr in fwd_seen: success (intersected)",
        "expand neighbors for bwd_curr"
    ]

    def __init__(self):
        self.initial_state = DEFAULT_INITIAL_STATE
        self.search_state = self._build_initial_state(self.initial_state)

    def _build_initial_state(self, state):
        return {
            "fwd_queue": deque([state]),
            "bwd_queue": deque([GOAL_STATE]),
            "fwd_seen": {state: None},  # state -> parent
            "bwd_seen": {GOAL_STATE: None}, # state -> parent
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
            return self._with_trace({"finished": True, "success": self.search_state["solved"], "msg": "Finished"}, trace_step)

        if not self.search_state["fwd_queue"] or not self.search_state["bwd_queue"]:
            self.search_state["finished"] = True
            trace_step.append(self._push_trace(1, "One of the queues is empty -> no solution found."))
            return self._with_trace({"finished": True, "success": False, "msg": "No solution found"}, trace_step)

        if self.search_state["nodes_explored"] == 0:
            self.search_state["start_time"] = time.time()

        # --- FORWARD STEP ---
        fwd_curr = self.search_state["fwd_queue"].popleft()
        self.search_state["nodes_explored"] += 1
        trace_step.append(self._push_trace(2, f"Forward pop: {list(fwd_curr)}"))

        if fwd_curr in self.search_state["bwd_seen"]:
            return self._finish_with_success(fwd_curr, trace_step, 3, "Forward intersected with backward!")

        for neighbor in get_neighbors(fwd_curr):
            if neighbor not in self.search_state["fwd_seen"]:
                self.search_state["fwd_seen"][neighbor] = fwd_curr
                self.search_state["fwd_queue"].append(neighbor)
        trace_step.append(self._push_trace(4, "Expanded forward neighbors."))

        # --- BACKWARD STEP ---
        bwd_curr = self.search_state["bwd_queue"].popleft()
        self.search_state["nodes_explored"] += 1
        trace_step.append(self._push_trace(5, f"Backward pop: {list(bwd_curr)}"))

        if bwd_curr in self.search_state["fwd_seen"]:
            return self._finish_with_success(bwd_curr, trace_step, 6, "Backward intersected with forward!")

        for neighbor in get_neighbors(bwd_curr):
            if neighbor not in self.search_state["bwd_seen"]:
                self.search_state["bwd_seen"][neighbor] = bwd_curr
                self.search_state["bwd_queue"].append(neighbor)
        trace_step.append(self._push_trace(7, "Expanded backward neighbors."))

        total_frontier = len(self.search_state["fwd_queue"]) + len(self.search_state["bwd_queue"])
        return self._with_trace(
            {
                "current_state": list(fwd_curr),
                "frontier_size": total_frontier,
                "nodes_explored": self.search_state["nodes_explored"],
                "finished": False,
            },
            trace_step,
        )

    def _finish_with_success(self, intersect_node, trace_step, line, msg):
        self.search_state["finished"] = True
        self.search_state["solved"] = True
        trace_step.append(self._push_trace(line, msg))
        
        # Build path: Start -> Intersect -> Goal
        path_fwd = reconstruct_path(self.search_state["fwd_seen"], intersect_node)
        path_bwd = reconstruct_path(self.search_state["bwd_seen"], intersect_node)
        
        path_bwd.reverse() # Reverse from goal to intersect
        final_path = path_fwd + path_bwd[1:] # Avoid duplicating the intersect node

        return self._with_trace({
            "current_state": list(intersect_node),
            "nodes_explored": self.search_state["nodes_explored"],
            "processing_time": f"{time.time() - self.search_state['start_time']:.4f}s",
            "final_path": [list(s) for s in final_path],
            "finished": True,
            "success": True,
        }, trace_step)

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
        return """def bidirectional_search(start, goal):
    fwd_queue = deque([start])
    bwd_queue = deque([goal])
    fwd_seen = {start: None}
    bwd_seen = {goal: None}

    while fwd_queue and bwd_queue:
        # Bước tiến phía trước (Forward)
        fwd_curr = fwd_queue.popleft()
        if fwd_curr in bwd_seen:
            return reconstruct_bidirectional_path(fwd_seen, bwd_seen, fwd_curr)
        
        for neighbor in get_neighbors(fwd_curr):
            if neighbor not in fwd_seen:
                fwd_seen[neighbor] = fwd_curr
                fwd_queue.append(neighbor)

        # Bước tiến phía sau (Backward)
        bwd_curr = bwd_queue.popleft()
        if bwd_curr in fwd_seen:
            return reconstruct_bidirectional_path(fwd_seen, bwd_seen, bwd_curr)
            
        for neighbor in get_neighbors(bwd_curr):
            if neighbor not in bwd_seen:
                bwd_seen[neighbor] = bwd_curr
                bwd_queue.append(neighbor)
    return None
"""