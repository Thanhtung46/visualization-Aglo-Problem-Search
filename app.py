import random
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from engines.registry import build_default_engines

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Cho phép mọi nguồn

engines = build_default_engines()
DEFAULT_ALGO = "bfs"


def get_engine(algo_key):
    key = (algo_key or DEFAULT_ALGO).lower()
    return engines.get(key)


def _reservoir_append_sample(reservoir, current_state, step_index, limit):
    """Giữ tối đa `limit` mẫu phân bố xấp xỉ đều trên stream các bước (reservoir sampling)."""
    if limit <= 0 or not current_state:
        return
    snap = list(current_state)
    if len(reservoir) < limit:
        reservoir.append(snap)
        return
    j = random.randint(1, step_index)
    if j <= limit:
        reservoir[j - 1] = snap


def _normalize_state(state):
    if not isinstance(state, (list, tuple)) or len(state) != 9:
        return None
    try:
        return tuple(int(x) for x in state)
    except (TypeError, ValueError):
        return None


def simulate_algorithm(
    algo_key,
    max_steps=5000,
    sample_limit=60,
    initial_state=None,
    max_duration_ms=None,
):
    
    isolated_engines = build_default_engines()
    engine = isolated_engines.get((algo_key or "").lower())
    

    if engine is None:
        return {
            "algo": algo_key,
            "supported": False,
            "error": f"Unsupported algorithm: {algo_key}",
        }

    normalized_initial = _normalize_state(initial_state)
    if normalized_initial is not None:
        engine.initial_state = normalized_initial
    engine.reset()
    started = time.perf_counter()
    steps_executed = 0
    frontier_peak = 0
    finished = False
    success = False
    nodes_explored = 0
    sampled_traversal = []
    last_payload = {}

    while steps_executed < max_steps:
        if max_duration_ms is not None:
            elapsed_ms_so_far = (time.perf_counter() - started) * 1000
            if elapsed_ms_so_far >= max_duration_ms:
                break
        payload = engine.step()
        last_payload = payload
        steps_executed += 1
        frontier_peak = max(frontier_peak, int(payload.get("frontier_size", 0)))
        nodes_explored = int(payload.get("nodes_explored", nodes_explored))
        current_state = payload.get("current_state")
        _reservoir_append_sample(sampled_traversal, current_state, steps_executed, sample_limit)

        if payload.get("finished"):
            finished = True
            success = bool(payload.get("success"))
            break

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    final_path = last_payload.get("final_path", []) or []
    final_path_length = len(final_path)
    path_found = bool(success and final_path_length > 0)
    total_path_cost = (final_path_length - 1) if path_found else None
    frontier_remaining = int(last_payload.get("frontier_size", 0) or 0)

    final_snap = last_payload.get("current_state")
    if final_snap:
        fs = list(final_snap)
        if sampled_traversal:
            if sampled_traversal[-1] != fs:
                sampled_traversal[-1] = fs
        else:
            sampled_traversal.append(fs)

    stopped_by_limit = bool((not finished) and steps_executed >= max_steps)
    stopped_by_timeout = bool((not finished) and (max_duration_ms is not None) and (not stopped_by_limit))

    return {
        "algo": algo_key,
        "supported": True,
        "finished": finished,
        "success": success,
        "steps_executed": steps_executed,
        "max_steps": max_steps,
        "stopped_by_limit": stopped_by_limit,
        "max_duration_ms": max_duration_ms,
        "stopped_by_timeout": stopped_by_timeout,
        "nodes_explored": nodes_explored,
        "frontier_peak": frontier_peak,
        "frontier_remaining": frontier_remaining,
        "elapsed_ms": elapsed_ms,
        "processing_time_ms": elapsed_ms,
        "path_found": path_found,
        "total_path_cost": total_path_cost,
        "final_path": [list(s) for s in final_path],
        "final_path_length": final_path_length,
        "sampled_traversal": [list(s) for s in sampled_traversal],
        "final_state": last_payload.get("current_state"),
    }

@app.route('/step', methods=['GET'])
def step():
    try:
        algo_key = request.args.get("algo", DEFAULT_ALGO)
        engine = get_engine(algo_key)
        if engine is None:
            return jsonify({"error": f"Unsupported algorithm: {algo_key}"}), 400
        return jsonify(engine.step())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    try:
        algo_key = request.args.get("algo", DEFAULT_ALGO)
        engine = get_engine(algo_key)
        if engine is None:
            return jsonify({"error": f"Unsupported algorithm: {algo_key}"}), 400
        return jsonify(engine.reset())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/random-state', methods=['POST'])
def random_state():
    try:
        algo_key = request.args.get("algo", DEFAULT_ALGO)
        engine = get_engine(algo_key)
        if engine is None:
            return jsonify({"error": f"Unsupported algorithm: {algo_key}"}), 400
        return jsonify(engine.random_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/source/bfs', methods=['GET'])
def source_bfs():
    try:
        engine = get_engine("bfs")
        return jsonify({
            "ok": True,
            "language": "python",
            "filename": engine.source_filename,
            "title": engine.source_title,
            "source": engine.algorithm_source()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/source/<algo_key>', methods=['GET'])
def source_algorithm(algo_key):
    try:
        engine = get_engine(algo_key)
        if engine is None:
            return jsonify({"error": f"Unsupported algorithm: {algo_key}"}), 400
        return jsonify({
            "ok": True,
            "language": "python",
            "filename": engine.source_filename,
            "title": engine.source_title,
            "source": engine.algorithm_source()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/compare', methods=['POST'])
def compare_algorithms():
    try:
        body = request.get_json(silent=True) or {}
        algo_a = (body.get("algo_a") or "bfs").lower()
        algo_b = (body.get("algo_b") or "dfs").lower()
        max_steps = int(body.get("max_steps", 400000))
        # sample_limit = int(body.get("sample_limit", 500))
        _md = body.get("max_duration_ms", None)
        if _md in (None, "", False):
            max_duration_ms = None
        else:
            max_duration_ms = int(_md)
            if max_duration_ms <= 0:
                max_duration_ms = None

        result_a = simulate_algorithm(
            algo_a,
            max_steps=max_steps,
            # sample_limit=sample_limit,
            max_duration_ms=max_duration_ms,
        )
        result_b = simulate_algorithm(
            algo_b,
            max_steps=max_steps,
            # sample_limit=sample_limit,
            max_duration_ms=max_duration_ms,
        )

        winner = "none"
        if result_a.get("supported") and result_b.get("supported"):
            if result_a.get("success") and result_b.get("success"):
                time_a = result_a.get("elapsed_ms", 10**9)
                time_b = result_b.get("elapsed_ms", 10**9)
                if time_a < time_b:
                    winner = "algo_a"
                elif time_b < time_a:
                    winner = "algo_b"
            elif result_a.get("success") and not result_b.get("success"):
                winner = "algo_a"
            elif result_b.get("success") and not result_a.get("success"):
                winner = "algo_b"

        return jsonify({
            "ok": True,
            "algo_a": result_a,
            "algo_b": result_b,
            "winner": winner,
            "max_steps": max_steps,
            # "sample_limit": sample_limit,
            "max_duration_ms": max_duration_ms,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/plan', methods=['POST'])
def plan_algorithm():
    try:
        body = request.get_json(silent=True) or {}
        algo_key = (body.get("algo") or request.args.get("algo") or DEFAULT_ALGO).lower()
        initial_state = body.get("initial_state")
        max_steps = int(body.get("max_steps", 50000))
        max_duration_ms = int(body.get("max_duration_ms", 2500))

        planned = simulate_algorithm(
            algo_key,
            max_steps=max_steps,
            sample_limit=0,
            initial_state=initial_state,
            max_duration_ms=max_duration_ms,
        )

        if not planned.get("supported"):
            return jsonify({"ok": False, "error": planned.get("error", "Unsupported algorithm")}), 400

        return jsonify({
            "ok": True,
            "algo": algo_key,
            "path_found": planned.get("path_found", False),
            "total_path_cost": planned.get("total_path_cost"),
            "final_path_length": planned.get("final_path_length", 0),
            "finished": planned.get("finished", False),
            "success": planned.get("success", False),
            "nodes_explored": planned.get("nodes_explored", 0),
            "processing_time_ms": planned.get("processing_time_ms", planned.get("elapsed_ms", 0)),
            "stopped_by_timeout": planned.get("stopped_by_timeout", False),
            "max_duration_ms": planned.get("max_duration_ms", max_duration_ms),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/solve', methods=['GET'])
def solve():
    try:
        algo_key = request.args.get("algo", DEFAULT_ALGO)
        max_steps = int(request.args.get("max_steps", 200000))

        engine = get_engine(algo_key)  # ← dùng engine đang có, không tạo mới
        if engine is None:
            return jsonify({"error": f"Unsupported algorithm: {algo_key}"}), 400

        engine.reset()  # reset về initial_state hiện tại (đã random rồi)
        started = time.perf_counter()
        nodes_explored = 0
        final_path = []
        success = False

        for _ in range(max_steps):
            payload = engine.step()
            nodes_explored = int(payload.get("nodes_explored", nodes_explored))
            if payload.get("finished"):
                success = bool(payload.get("success"))
                final_path = payload.get("final_path", [])
                break

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return jsonify({
            "ok": True,
            "success": success,
            "nodes_explored": nodes_explored,
            "elapsed_ms": elapsed_ms,
            "path_length": len(final_path),
            "final_path": final_path,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Chạy Flask ở cổng 5000
    app.run(host='127.0.0.1', port=5000, debug=True)