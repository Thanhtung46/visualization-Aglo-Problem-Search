const API_BASE = "http://127.0.0.1:5000";

const state = {
    currentAlgorithm: "bfs",
    currentInitialState: [1, 2, 3, 4, 0, 5, 7, 8, 6],
    isRunning: false,
    isPaused: false,
    autoRun: false,
    isFetchingStep: false,
    traversalHistory: [],
    selectedHistoryIndex: -1,
    selectedSolutionIndex: -1,
    traceProgram: [],
    traceHistory: [],
    bfsSourceCache: "",
    frontendSourceCache: "",
    currentSourceLanguage: "python",
    compareMode: false,
    compareAnimationTimer: null,
    compareLoadingBoardsTimer: null,
    compareIsRunning: false,
    planIsRunning: false,
    precomputedTotalCost: null,
    precomputedExploreSteps: null,
    planRequestId: 0,
    solutionPath: [],
    compareSelectedPathIndexA: -1,
    compareSelectedPathIndexB: -1,
    lastRenderedBoard: null,
};
// Rút ngắn thời lượng flash để animation compare chạy nhanh hơn.
const FLASH_ANIM_MS = 180;

function getById(id) {
    return document.getElementById(id);
}

function getDelayMs() {
    const delayInput = getById("delay-input");
    const parsed = Number(delayInput.value);
    if (!Number.isFinite(parsed)) return 600;
    const clamped = Math.min(5000, Math.max(0, parsed));
    delayInput.value = String(clamped);
    return clamped;
}

function clampNumberInputValue(inputEl, fallbackValue = null) {
    if (!inputEl) return fallbackValue;
    const parsed = Number(inputEl.value);
    const min = Number(inputEl.min);
    const max = Number(inputEl.max);
    const safeMin = Number.isFinite(min) ? min : -Infinity;
    const safeMax = Number.isFinite(max) ? max : Infinity;
    const fallback = fallbackValue ?? (Number.isFinite(safeMin) ? safeMin : 0);
    const base = Number.isFinite(parsed) ? parsed : fallback;
    const clamped = Math.min(safeMax, Math.max(safeMin, base));
    inputEl.value = String(clamped);
    return clamped;
}

/** Chỉ số các ô có giá trị khác so với bước trước (kể cả nhảy xa trên graph tìm kiếm). */
function getChangedCellIndices(prev, next) {
    if (!Array.isArray(prev) || !Array.isArray(next) || prev.length !== 9 || next.length !== 9) {
        return [];
    }
    const out = [];
    for (let k = 0; k < 9; k += 1) {
        if (prev[k] !== next[k]) out.push(k);
    }
    return out;
}

function clearMainTileFlashClasses(container) {
    if (!container) return;
    container.querySelectorAll(".tile-changed-flash").forEach(el => {
        el.classList.remove("tile-changed-flash");
    });
}

function scheduleMainTileFlashClear(container) {
    if (!container) return;
    window.setTimeout(() => clearMainTileFlashClasses(container), FLASH_ANIM_MS);
}

let _prevBoard = null; // thêm dòng này ở top-level, cạnh const state = {...}

function render(boardState, movedNum = null) {
  const container = getById("puzzle-container");
  if (!boardState) return;
  const changedIndices = _prevBoard ? getChangedCellIndices(_prevBoard, boardState) : [];

  // Bước FIRST: đo vị trí cũ
  const oldPositions = {};
  if (_prevBoard) {
    _prevBoard.forEach((num, i) => {
      const el = container.children[i];
      if (el) oldPositions[num] = el.getBoundingClientRect();
    });
  }

  // Xóa và vẽ lại (LAST)
  container.innerHTML = "";
  boardState.forEach(num => {
    const div = document.createElement("div");
    div.className = "tile" + (num === 0 ? " empty" : "");
    div.innerText = num !== 0 ? num : "";
    container.appendChild(div);
  });

  // Bước INVERT + PLAY
  boardState.forEach((num, i) => {
    const el = container.children[i];
    if (!oldPositions[num]) return;
    const newPos = el.getBoundingClientRect();
    const dx = oldPositions[num].left - newPos.left;
    const dy = oldPositions[num].top - newPos.top;
    if (dx === 0 && dy === 0) return;

    el.style.setProperty("--tile-order", String(changedIndices.indexOf(i)));
    el.style.transform = `translate(${dx}px, ${dy}px)`;
    el.offsetHeight; // force reflow
    el.classList.add("animating");
    if (num === movedNum) el.classList.add("moved");
    el.style.transform = "";

    el.addEventListener("transitionend", () => {
      el.classList.remove("animating");
      setTimeout(() => el.classList.remove("moved"), 180);
    }, { once: true });
  });

  if (changedIndices.length > 0) {
    changedIndices.forEach((idx, order) => {
      const el = container.children[idx];
      if (!el) return;
      el.style.setProperty("--tile-order", String(order));
      el.classList.remove("tile-changed-flash");
      el.offsetHeight;
      el.classList.add("tile-changed-flash");
    });
    scheduleMainTileFlashClear(container);
  }

  _prevBoard = [...boardState];
}

function fillMiniGrid(grid, nodeState, prevState) {
    const changed = prevState ? getChangedCellIndices(prevState, nodeState) : [];
    nodeState.forEach((num, ti) => {
        const flash = changed.length > 0 && changed.includes(ti) ? " mini-tile-changed-flash" : "";
        const tile = document.createElement("div");
        tile.className = "mini-tile" + (num === 0 ? " empty" : "") + flash;
        tile.innerText = num === 0 ? "" : String(num);
        grid.appendChild(tile);
    });
    if (changed.length > 0) {
        window.setTimeout(() => {
            grid.querySelectorAll(".mini-tile-changed-flash").forEach(el => {
                el.classList.remove("mini-tile-changed-flash");
            });
        }, FLASH_ANIM_MS);
    }
}

function renderPath(pathStates = []) {
    const pathContainer = getById("path-container");
    pathContainer.innerHTML = "";
    getById("history-count").innerText = String(pathStates.length);
    if (!pathStates.length) return;

    pathStates.forEach((nodeState, idx) => {
        const node = document.createElement("div");
        const isCurrent = idx === pathStates.length - 1;
        const isSelected = idx === state.selectedHistoryIndex;
        node.className = "path-node" + (isCurrent ? " current" : "") + (isSelected ? " selected" : "");
        const grid = document.createElement("div");
        grid.className = "mini-grid";

        const prevState = idx > 0 ? pathStates[idx - 1] : null;
        fillMiniGrid(grid, nodeState, prevState);

        const step = document.createElement("div");
        step.className = "path-step";
        step.innerText = `Bước ${idx}`;

        node.appendChild(grid);
        node.appendChild(step);
        node.addEventListener("click", () => {
            if (state.compareMode) return;
            // Cho phép xem lại trạng thái đã duyệt mà không can thiệp logic thuật toán.
            const prev = idx > 0 ? pathStates[idx - 1] : null;
            const movedNum = prev ? nodeState[prev.indexOf(0)] : null;
            state.selectedHistoryIndex = idx;
            render(nodeState, movedNum);
            renderPath(pathStates);
            setStatus(`Đang xem lại: Bước ${idx}`);
        });
        pathContainer.appendChild(node);
    });

    pathContainer.scrollLeft = pathContainer.scrollWidth;
}

function renderSolutionPath(pathStates = []) {
    const container = getById("solution-path-container");
    if (!container) return;
    container.innerHTML = "";
    if (!Array.isArray(pathStates) || !pathStates.length) return;

    pathStates.forEach((nodeState, idx) => {
        const node = document.createElement("div");
        const isCurrent = idx === pathStates.length - 1;
        const isSelected = idx === state.selectedSolutionIndex;
        node.className = "path-node" + (isCurrent ? " current" : "") + (isSelected ? " selected" : "");
        const grid = document.createElement("div");
        grid.className = "mini-grid";

        const prevState = idx > 0 ? pathStates[idx - 1] : null;
        fillMiniGrid(grid, nodeState, prevState);

        const step = document.createElement("div");
        step.className = "path-step";
        step.innerText = idx === 0 ? "Start" : (idx === pathStates.length - 1 ? "Goal" : `Buoc di ${idx}`);

        node.appendChild(grid);
        node.appendChild(step);
        node.addEventListener("click", () => {
            if (state.compareMode) return;
            const prev = idx > 0 ? pathStates[idx - 1] : null;
            const movedNum = prev ? nodeState[prev.indexOf(0)] : null;
            state.selectedSolutionIndex = idx;
            render(nodeState, movedNum);
            renderSolutionPath(pathStates);
            setStatus(idx === pathStates.length - 1 ? "Đang xem lại: Goal" : `Đang xem lại đường đi: bước ${idx}`);
        });
        container.appendChild(node);
    });

    container.scrollLeft = container.scrollWidth;
}

function renderTraceProgram(activeLine = -1) {
    const container = getById("trace-program");
    container.innerHTML = "";
    if (!state.traceProgram.length) return;

    state.traceProgram.forEach((lineText, idx) => {
        const lineEl = document.createElement("div");
        lineEl.className = "trace-line" + (idx === activeLine ? " active" : "");
        lineEl.innerText = `${idx}. ${lineText}`;
        container.appendChild(lineEl);
    });
}

function renderTraceLog() {
    const log = getById("trace-log");
    log.innerHTML = "";
    const tail = state.traceHistory.slice(-40);
    tail.forEach(item => {
        const row = document.createElement("div");
        row.className = "trace-log-item";
        row.innerText = `[line ${item.line}] ${item.message}`;
        log.appendChild(row);
    });
    log.scrollTop = log.scrollHeight;
}

function updateTraceFromResponse(data) {
    if (Array.isArray(data.trace_program)) {
        state.traceProgram = data.trace_program;
    }
    if (Array.isArray(data.trace_history)) {
        state.traceHistory = data.trace_history;
    }
    const activeLine = state.traceHistory.length
        ? state.traceHistory[state.traceHistory.length - 1].line
        : -1;
    renderTraceProgram(activeLine);
    renderTraceLog();
}

function isSameState(a, b) {
    if (!a || !b || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
        if (a[i] !== b[i]) return false;
    }
    return true;
}

function pushHistoryStep(stepState) {
    if (!Array.isArray(stepState) || !stepState.length) return;
    const last = state.traversalHistory[state.traversalHistory.length - 1];
    if (isSameState(last, stepState)) return;

    state.traversalHistory.push(stepState);
    state.selectedHistoryIndex = state.traversalHistory.length - 1;
    renderPath(state.traversalHistory);
}

function resetHistory(initialState) {
    // Timeline traversal chỉ hiển thị các node đã thực sự được engine duyệt.
    // Trạng thái ban đầu vẫn hiển thị ở board chính, nhưng không tính là "đã duyệt".
    state.traversalHistory = [];
    state.selectedHistoryIndex = -1;
    renderPath(state.traversalHistory);
}

function setStatus(message) {
    getById("status").innerText = message;
}

function setRemainingSteps(value) {
    getById("remaining-steps").innerText = value == null ? "-" : String(value);
}

function updateRemainingEstimate(explored, finished, success) {
    if (finished && success) {
        setRemainingSteps(0);
        return;
    }
    if (typeof state.precomputedExploreSteps === "number") {
        const remaining = state.precomputedExploreSteps - explored;
        setRemainingSteps(Math.max(remaining, 0));
        return;
    }
    setRemainingSteps("-");
}

function setButtonClass(btn, className, on) {
    if (!btn) return;
    if (on) btn.classList.add(className);
    else btn.classList.remove(className);
}

function setButtonDisabled(btn, disabled) {
    if (!btn) return;
    btn.disabled = disabled;
    if (disabled) btn.classList.add("btn-dim");
    else btn.classList.remove("btn-dim");
}

function syncTopbarButtons() {
    const solveBtn = getById("solve-btn");
    const autoRunBtn = getById("auto-run-btn");
    const nextStepBtn = getById("next-step-btn");
    const pauseBtn = getById("pause-btn");
    const resetBtn = getById("reset-btn");
    const randomBtn = getById("random-btn");
    const compareModeBtn = getById("compare-mode-btn");
    const compareBtn = getById("compare-btn");

    // Clear state classes
    [solveBtn, autoRunBtn, nextStepBtn, pauseBtn, resetBtn, randomBtn, compareBtn, compareModeBtn].forEach(btn => {
        if (!btn) return;
        btn.classList.remove("btn-running", "btn-paused", "btn-busy");
    });

    if (state.compareIsRunning) {
        setButtonDisabled(solveBtn, true);
        setButtonDisabled(autoRunBtn, true);
        setButtonDisabled(nextStepBtn, true);
        setButtonDisabled(pauseBtn, true);
        setButtonDisabled(resetBtn, true);
        setButtonDisabled(randomBtn, true);
        if (compareBtn) {
            setButtonDisabled(compareBtn, true);
            compareBtn.classList.add("btn-busy");
            // Đảm bảo text không bị reset trong lúc compare đang chạy.
            compareBtn.innerText = "Comparing...";
        }
        return;
    }

    // Compare Mode: tắt các nút vận hành thuật toán thường
    if (state.compareMode) {
        setButtonDisabled(solveBtn, true);
        setButtonDisabled(autoRunBtn, true);
        setButtonDisabled(nextStepBtn, true);
        setButtonDisabled(pauseBtn, true);
        setButtonDisabled(resetBtn, false);
        setButtonDisabled(randomBtn, false);
        setButtonDisabled(compareBtn, false);
        setButtonClass(compareModeBtn, "btn-running", true);
        setButtonClass(compareModeBtn, "btn-paused", false);
        return;
    }

    if (state.planIsRunning) {
        setButtonDisabled(solveBtn, true);
        setButtonDisabled(autoRunBtn, true);
        setButtonDisabled(nextStepBtn, true);
        setButtonDisabled(pauseBtn, true);
        setButtonDisabled(resetBtn, false);
        setButtonDisabled(randomBtn, false);
        setButtonDisabled(compareBtn, false);
        return;
    }

    // Running/paused chế độ bình thường
    const isSearchActive = Boolean(state.autoRun || state.isRunning);
    setButtonDisabled(solveBtn, isSearchActive);
    setButtonDisabled(autoRunBtn, Boolean(state.autoRun));
    setButtonDisabled(nextStepBtn, Boolean(state.autoRun));
    setButtonDisabled(pauseBtn, !Boolean(state.autoRun));
    setButtonDisabled(resetBtn, false);
    setButtonDisabled(randomBtn, isSearchActive);
    setButtonDisabled(compareBtn, false);
    setButtonClass(compareModeBtn, "btn-running", false);

    setButtonClass(autoRunBtn, "btn-running", Boolean(state.autoRun));
    setButtonClass(pauseBtn, "btn-paused", Boolean(state.autoRun && state.isPaused));
    setButtonClass(pauseBtn, "btn-running", Boolean(state.autoRun && !state.isPaused));
}

async function precomputeGoalPlan() { // xem lại
    const requestId = ++state.planRequestId;
    state.planIsRunning = true;
    state.precomputedTotalCost = null;
    state.precomputedExploreSteps = null;
    setRemainingSteps("Dang tinh...");
    syncTopbarButtons();
    const planMaxSteps = 500000;
    try {
        const res = await fetch(`${API_BASE}/plan`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algo: state.currentAlgorithm,
                initial_state: state.currentInitialState,
                max_steps: planMaxSteps,
            }),
        });
        const data = await res.json();
        if (requestId !== state.planRequestId) return;
        if (!res.ok || !data.ok) {
            setRemainingSteps("-");
            return;
        }
        if (data.finished && data.success && typeof data.nodes_explored === "number" && data.nodes_explored > 0) {
            state.precomputedExploreSteps = data.nodes_explored;
            setRemainingSteps(state.precomputedExploreSteps);
            return;
        }
        if (data.stopped_by_timeout) {
            setRemainingSteps("Timeout plan");
            return;
        }
        setRemainingSteps(data.finished ? "Khong tim thay" : "Vuot gioi han");
    } catch (err) {
        if (requestId !== state.planRequestId) return;
        state.precomputedTotalCost = null;
        state.precomputedExploreSteps = null;
        setRemainingSteps("-");
    } finally {
        if (requestId !== state.planRequestId) return;
        state.planIsRunning = false;
        syncTopbarButtons();
    }
}

function renderCompareResult(result) {
    const summary = getById("compare-summary");
    const metrics = getById("compare-metrics");
    const traversal = getById("compare-traversal");
    metrics.innerHTML = "";
    traversal.innerHTML = "";

    if (!result || !result.ok) {
        summary.innerText = "Khong co du lieu so sanh.";
        return;
    }

    const winnerMap = {
        algo_a: "A",
        algo_b: "B",
        none: "Khong ro",
    };
    const timeoutNote = (result.algo_a?.stopped_by_timeout || result.algo_b?.stopped_by_timeout)
        ? " | Có thuật toán bị dừng do timeout backend"
        : "";
    summary.innerText = `Ket qua compare (winner: ${winnerMap[result.winner] || "Khong ro"})${timeoutNote}`;

    function updateCompareBoardFromPath(side, boardState) {
        if (!Array.isArray(boardState) || boardState.length !== 9) return;
        const targetId = side === "A" ? "compare-side-a-board" : "compare-side-b-board";
        renderMiniBoard(targetId, boardState);
    }

    function createMetricCard(label, data) {
        const card = document.createElement("div");
        card.className = "compare-card";
        const title = document.createElement("div");
        title.className = "compare-title";
        title.innerText = `${label}: ${data.algo?.toUpperCase() || "N/A"}`;
        card.appendChild(title);

        const pathFound = typeof data.path_found === "boolean"
            ? data.path_found
            : Boolean(data.success && (data.final_path_length ?? 0) > 0);
        const pathLength = data.final_path_length ?? (pathFound ? "-" : 0);
        const totalPathCost = typeof data.total_path_cost !== "undefined"
            ? data.total_path_cost
            : (pathFound && typeof pathLength === "number" ? Math.max(pathLength - 1, 0) : "-");

        const lines = [
            // `Supported: ${data.supported ? "Yes" : "No"}`,
            `Finished: ${data.finished ? "Yes" : "No"}`,
            `Success: ${data.success ? "Yes" : "No"}`,
            `Stopped by timeout: ${data.stopped_by_timeout ? "Yes" : "No"}`,
            // `Stopped by max steps: ${data.stopped_by_limit ? "Yes" : "No"}`,
            `Time budget (ms): ${data.max_duration_ms ?? "-"}`,
            // `Max steps: ${data.max_steps ?? "-"}`,
            `Node explore limit: ${data.max_nodes_explored ?? "-"}`,
            `Stopped by node limit: ${data.stopped_by_node_limit ? "Yes" : "No"}`,
            `Path found: ${pathFound ? "Yes" : "No"}`,
            `Path length: ${pathLength ?? "-"}`,
            `Total path cost: ${totalPathCost ?? "-"}`,
            `Nodes explored: ${data.nodes_explored ?? "-"}`,
            `Steps executed: ${data.steps_executed ?? "-"}`,
            `Peak frontier: ${data.frontier_peak ?? "-"}`,
            // `Frontier remaining: ${data.frontier_remaining ?? "-"}`,
            // `Processing time (ms): ${data.processing_time_ms ?? data.elapsed_ms ?? "-"}`,
            data.error ? `Error: ${data.error}` : "",
        ].filter(Boolean);

        lines.forEach(text => {
            const line = document.createElement("div");
            line.className = "compare-line";
            line.innerText = text;
            card.appendChild(line);
        });
        return card;
    }

    function createPathStrip(label, data, side) {
        const wrap = document.createElement("div");
        wrap.className = "compare-traversal-block";
        const title = document.createElement("div");
        title.className = "compare-title";
        title.innerText = `${label} path (Start → Goal)`;
        wrap.appendChild(title);

        const strip = document.createElement("div");
        strip.className = "compare-strip compare-path-strip";
        const path = Array.isArray(data.final_path) ? data.final_path : [];
        const pathFound = typeof data.path_found === "boolean"
            ? data.path_found
            : Boolean(data.success && (data.final_path_length ?? 0) > 0);

        if (!pathFound || !path.length) {
            if (side === "A") state.compareSelectedPathIndexA = -1;
            if (side === "B") state.compareSelectedPathIndexB = -1;
            const empty = document.createElement("div");
            empty.className = "compare-line";
            empty.innerText = "Chưa tìm được đường đi đến goal.";
            strip.appendChild(empty);
        } else {
            const selectedIndex = side === "A" ? state.compareSelectedPathIndexA : state.compareSelectedPathIndexB;
            const activeIndex = selectedIndex >= 0 && selectedIndex < path.length ? selectedIndex : path.length - 1;
            if (side === "A") state.compareSelectedPathIndexA = activeIndex;
            if (side === "B") state.compareSelectedPathIndexB = activeIndex;
            updateCompareBoardFromPath(side, path[activeIndex]);

            function appendState(boardState, idx) {
                const stateBox = document.createElement("div");
                const isSelected = idx === activeIndex;
                stateBox.className = "compare-state" + (isSelected ? " selected" : "");
                const grid = document.createElement("div");
                grid.className = "compare-grid";
                boardState.forEach(num => {
                    const tile = document.createElement("div");
                    tile.className = "compare-tile" + (num === 0 ? " empty" : "");
                    tile.innerText = num === 0 ? "" : String(num);
                    grid.appendChild(tile);
                });
                const step = document.createElement("div");
                step.className = "compare-step-label";
                if (idx === 0) step.innerText = "Start";
                else if (idx === path.length - 1) step.innerText = "Goal";
                else step.innerText = `Bước ${idx}`;
                stateBox.appendChild(grid);
                stateBox.appendChild(step);
                stateBox.addEventListener("click", () => {
                    if (side === "A") state.compareSelectedPathIndexA = idx;
                    if (side === "B") state.compareSelectedPathIndexB = idx;
                    updateCompareBoardFromPath(side, boardState);
                    renderCompareResult(result);
                });
                strip.appendChild(stateBox);
            }

            path.forEach((s, i) => appendState(s, i));
        }

        wrap.appendChild(strip);
        return wrap;
    }

    metrics.appendChild(createMetricCard("Algo A", result.algo_a || {}));
    metrics.appendChild(createMetricCard("Algo B", result.algo_b || {}));
    traversal.appendChild(createPathStrip("Algo A", result.algo_a || {}, "A"));
    traversal.appendChild(createPathStrip("Algo B", result.algo_b || {}, "B"));
}

function getBoardNeighbors(boardState) {
    if (!Array.isArray(boardState) || boardState.length !== 9) return [];
    const zeroIdx = boardState.indexOf(0);
    if (zeroIdx < 0) return [];
    const row = Math.floor(zeroIdx / 3);
    const col = zeroIdx % 3;
    const dirs = [
        [row - 1, col],
        [row + 1, col],
        [row, col - 1],
        [row, col + 1],
    ];
    const out = [];
    dirs.forEach(([nr, nc]) => {
        if (nr < 0 || nr > 2 || nc < 0 || nc > 2) return;
        const nextIdx = nr * 3 + nc;
        const next = [...boardState];
        [next[zeroIdx], next[nextIdx]] = [next[nextIdx], next[zeroIdx]];
        out.push(next);
    });
    return out;
}

function stopCompareLoadingBoards() {
    if (state.compareLoadingBoardsTimer) {
        clearInterval(state.compareLoadingBoardsTimer);
        state.compareLoadingBoardsTimer = null;
    }
}

function startCompareLoadingBoards() {
    stopCompareLoadingBoards();
    let boardA = [...state.currentInitialState];
    let boardB = [...state.currentInitialState];
    let prevA = null;
    let prevB = null;
    const statsA = getById("compare-side-a-stats");
    const statsB = getById("compare-side-b-stats");
    renderMiniBoard("compare-side-a-board", boardA, prevA);
    renderMiniBoard("compare-side-b-board", boardB, prevB);
    if (statsA) statsA.innerText = "Đang duyệt node...";
    if (statsB) statsB.innerText = "Đang duyệt node...";

    state.compareLoadingBoardsTimer = setInterval(() => {
        const nextA = getBoardNeighbors(boardA);
        const nextB = getBoardNeighbors(boardB);
        prevA = boardA;
        prevB = boardB;
        boardA = nextA[Math.floor(Math.random() * nextA.length)] || boardA;
        boardB = nextB[Math.floor(Math.random() * nextB.length)] || boardB;
        renderMiniBoard("compare-side-a-board", boardA, prevA);
        renderMiniBoard("compare-side-b-board", boardB, prevB);
    }, 140);
}

function renderMiniBoard(targetId, boardState, prevBoardState = null) {
    const board = getById(targetId);
    board.innerHTML = "";
    if (!Array.isArray(boardState) || !boardState.length) return;

    const changed = prevBoardState ? getChangedCellIndices(prevBoardState, boardState) : [];
    boardState.forEach((num, idx) => {
        const flash = changed.length > 0 && changed.includes(idx) ? " compare-main-tile-changed-flash" : "";
        const tile = document.createElement("div");
        tile.className = "compare-main-tile" + (num === 0 ? " empty" : "") + flash;
        tile.innerText = num === 0 ? "" : String(num);
        board.appendChild(tile);
    });

    if (changed.length > 0) {
        window.setTimeout(() => {
            board.querySelectorAll(".compare-main-tile-changed-flash").forEach(el => {
                el.classList.remove("compare-main-tile-changed-flash");
            });
        }, FLASH_ANIM_MS);
    }
}

function renderCompareSplit(result) {
    return new Promise(resolve => {
    const panel = getById("compare-split-panel");
    const statsA = getById("compare-side-a-stats");
    const statsB = getById("compare-side-b-stats");
    if (!state.compareMode) {
        panel.classList.add("hidden");
        resolve();
        return;
    }
    panel.classList.remove("hidden");

    if (!result || !result.ok) {
        state.compareSelectedPathIndexA = -1;
        state.compareSelectedPathIndexB = -1;
        const algoA = getById("compare-a")?.value || "bfs";
        const algoB = getById("compare-b")?.value || "dfs";
        getById("compare-side-a-title").innerText = `Algo A: ${algoA.toUpperCase()}`;
        getById("compare-side-b-title").innerText = `Algo B: ${algoB.toUpperCase()}`;
        if (statsA) statsA.innerText = "Chưa có dữ liệu";
        if (statsB) statsB.innerText = "Chưa có dữ liệu";
        renderMiniBoard("compare-side-a-board", state.currentInitialState);
        renderMiniBoard("compare-side-b-board", state.currentInitialState);
        resolve();
        return;
    }

    stopCompareLoadingBoards();
    state.compareSelectedPathIndexA = -1;
    state.compareSelectedPathIndexB = -1;
    const a = result.algo_a || {};
    const b = result.algo_b || {};
    const pathFoundA = typeof a.path_found === "boolean" ? a.path_found : Boolean(a.success && (a.final_path_length ?? 0) > 0);
    const pathFoundB = typeof b.path_found === "boolean" ? b.path_found : Boolean(b.success && (b.final_path_length ?? 0) > 0);
    const aSolvedBoard = pathFoundA && Array.isArray(a.final_path) && a.final_path.length
        ? a.final_path[a.final_path.length - 1]
        : null;
    const bSolvedBoard = pathFoundB && Array.isArray(b.final_path) && b.final_path.length
        ? b.final_path[b.final_path.length - 1]
        : null;
    const aFinal = aSolvedBoard || (Array.isArray(a.final_state) && a.final_state.length ? a.final_state : state.currentInitialState);
    const bFinal = bSolvedBoard || (Array.isArray(b.final_state) && b.final_state.length ? b.final_state : state.currentInitialState);

    getById("compare-side-a-title").innerText = `Algo A: ${(a.algo || "N/A").toUpperCase()}`;
    getById("compare-side-b-title").innerText = `Algo B: ${(b.algo || "N/A").toUpperCase()}`;
    renderMiniBoard("compare-side-a-board", aFinal);
    renderMiniBoard("compare-side-b-board", bFinal);
    if (statsA) statsA.innerText = `nodes=${a.nodes_explored ?? "-"}, ms=${a.elapsed_ms ?? "-"}, success=${a.success ? "yes" : "no"}, goal=${pathFoundA ? "yes" : "no"}, timeout=${a.stopped_by_timeout ? "yes" : "no"}`;
    if (statsB) statsB.innerText = `nodes=${b.nodes_explored ?? "-"}, ms=${b.elapsed_ms ?? "-"}, success=${b.success ? "yes" : "no"}, goal=${pathFoundB ? "yes" : "no"}, timeout=${b.stopped_by_timeout ? "yes" : "no"}`;
    resolve();
    });
}

function handleUnsupportedAlgo() {
    setStatus("Thuật toán này chưa được backend hỗ trợ");
    alert(`Thuật toán ${state.currentAlgorithm.toUpperCase()} chưa được backend hỗ trợ.`);
}

function buildApiUrl(path) {
    const algo = encodeURIComponent(state.currentAlgorithm);
    const separator = path.includes("?") ? "&" : "?";
    return `${API_BASE}${path}${separator}algo=${algo}`;
}

function setCompareRunningVisual(isRunning) {
    const compareSplit = getById("compare-split-panel");
    const comparePanel = getById("compare-panel");
    const btn = getById("compare-btn");
    [compareSplit, comparePanel].forEach(el => {
        if (!el) return;
        el.classList.toggle("compare-running", Boolean(isRunning));
    });
    if (btn) {
        if (isRunning) {
            btn.classList.add("btn-busy");
            btn.innerText = "Comparing...";
        } else {
            btn.classList.remove("btn-busy");
            btn.innerText = "Compare";
        }
    }
}

async function randomizeInput() {
    if (state.isRunning) return alert("Hãy Pause hoặc chờ thuật toán kết thúc.");

    try {
        const res = await fetch(buildApiUrl("/random-state"), { method: "POST" });
        const data = await res.json();
        if (!res.ok) return handleUnsupportedAlgo();
        if (!data.current_state) return alert("Không tạo được input ngẫu nhiên.");

        state.currentInitialState = data.current_state;
        getById("nodes").innerText = "0";
        getById("frontier").innerText = "0";
        getById("time").innerText = "-";
        setRemainingSteps("-");
        setStatus("Đã tạo input ngẫu nhiên mới");
        render(state.currentInitialState, false);
        resetHistory(state.currentInitialState);
        state.solutionPath = [];
        state.selectedSolutionIndex = -1;
        renderSolutionPath(state.solutionPath);
        updateTraceFromResponse(data);
        await precomputeGoalPlan();
        if (state.compareMode) {
            renderCompareSplit(null);
        }
        syncTopbarButtons();
    } catch (err) {
        alert("Không thể kết nối Backend.");
    }
}

async function resetSearch() {
    // Cho phép reset khi đang chạy: dừng vòng auto-run trước.
    if (state.isRunning || state.autoRun) {
        state.autoRun = false;
        state.isRunning = false;
        state.isPaused = false;
        const pauseBtn = getById("pause-btn");
        pauseBtn.disabled = true;
        pauseBtn.innerText = "Pause";
        syncTopbarButtons();
    }
    state.isFetchingStep = false;

    try {
        const res = await fetch(buildApiUrl("/reset"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                initial_state: state.currentInitialState,
            }),
        });
        const data = await res.json();
        if (!res.ok) return handleUnsupportedAlgo();

        getById("nodes").innerText = "0";
        getById("frontier").innerText = "0";
        getById("time").innerText = "-";
        setRemainingSteps("-");
        setStatus("Đã reset");
        if (data.current_state) state.currentInitialState = data.current_state;
        render(state.currentInitialState, false);
        resetHistory(state.currentInitialState);
        state.solutionPath = [];
        state.selectedSolutionIndex = -1;
        renderSolutionPath(state.solutionPath);
        updateTraceFromResponse(data);
        await precomputeGoalPlan();
        if (state.compareMode) {
            renderCompareSplit(null);
        }
        syncTopbarButtons();
    } catch (err) {
        alert("Không thể kết nối Backend.");
    }
}

async function compareAlgorithms() {
    if (state.isRunning) return alert("Hay dung thuat toan hien tai truoc khi compare.");
    const algoA = getById("compare-a")?.value || "";
    const algoB = getById("compare-b")?.value || "";
    const nodeLimitEl = getById("compare-node-limit");
    const maxNodesExplored = clampNumberInputValue(nodeLimitEl, 5000);
    const summary = getById("compare-summary");
    const metrics = getById("compare-metrics");
    const traversal = getById("compare-traversal");
    if (summary) summary.innerText = `Đang chạy compare theo node limit = ${maxNodesExplored}…`;
    if (metrics) metrics.innerHTML = "";
    if (traversal) traversal.innerHTML = "";

    state.compareIsRunning = true;
    setCompareRunningVisual(true);
    startCompareLoadingBoards();
    syncTopbarButtons();

    try {
        const startedUi = performance.now();
        const res = await fetch(`${API_BASE}/compare`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algo_a: algoA,
                algo_b: algoB,
                initial_state: state.currentInitialState,
                max_steps: 400000,
                max_nodes_explored: maxNodesExplored,
                // sample_limit: 500,
            }),
        });
        const data = await res.json();
        if (!res.ok || !data?.ok) {
            throw new Error(data?.error || `HTTP ${res.status}`);
        }
        const minMs = 520;
        const elapsed = performance.now() - startedUi;
        if (elapsed < minMs) await new Promise(r => setTimeout(r, minMs - elapsed));
        if (state.compareMode) {
            await renderCompareSplit(data);
        }
        renderCompareResult(data);
    } catch (err) {
        await new Promise(r => setTimeout(r, 250));
        const msg = `Compare lỗi: ${err?.message || "Không thể kết nối backend."}`;
        stopCompareLoadingBoards();
        if (summary) summary.innerText = msg;
        if (metrics) {
            metrics.innerHTML = `<div class="compare-card"><div class="compare-title">Lỗi</div><div class="compare-line">${msg}</div></div>`;
        }
        if (traversal) traversal.innerHTML = "";
        setStatus(msg);
    } finally {
        state.compareIsRunning = false;
        setCompareRunningVisual(false);
        syncTopbarButtons();
    }
}

function toggleCompareMode() {
    if (!state.compareMode && state.autoRun) {
        state.autoRun = false;
        state.isRunning = false;
        state.isPaused = false;
        const pauseBtn = getById("pause-btn");
        pauseBtn.disabled = true;
        pauseBtn.innerText = "Pause";
    }
    state.compareMode = !state.compareMode;
    const btn = getById("compare-mode-btn");
    const main = document.querySelector(".main");
    btn.innerText = state.compareMode ? "Compare Mode: On" : "Compare Mode: Off";
    if (main) {
        main.classList.toggle("compare-active", state.compareMode);
    }
    getById("compare-controls").classList.toggle("hidden", !state.compareMode);
    getById("compare-split-panel").classList.toggle("hidden", !state.compareMode);
    getById("compare-panel").classList.toggle("hidden", !state.compareMode);
    getById("source-column").classList.toggle("hidden", state.compareMode);
    getById("main-board-panel").classList.toggle("hidden", state.compareMode);
    getById("main-stats-panel").classList.toggle("hidden", state.compareMode);
    getById("path-panel").classList.toggle("hidden", state.compareMode);

    if (!state.compareMode && state.compareAnimationTimer) {
        clearInterval(state.compareAnimationTimer);
        state.compareAnimationTimer = null;
    }
    if (!state.compareMode) {
        stopCompareLoadingBoards();
    }
    renderCompareSplit(null);
    if (!state.compareMode) {
        render(state.currentInitialState, false);
    }
    syncTopbarButtons();
}

function togglePause() {
    if (state.compareMode) return alert("Dang o Compare Mode. Vui long dung nut Compare.");
    if (!state.autoRun) return;
    state.isPaused = !state.isPaused;
    const pauseBtn = getById("pause-btn");
    pauseBtn.innerText = state.isPaused ? "Resume" : "Pause";
    setStatus(state.isPaused ? "Đã tạm dừng Auto Run" : "Đang Auto Run");
    syncTopbarButtons();
}

async function fetchOneStep() {
    if (state.isFetchingStep) return { done: false };
    state.isFetchingStep = true;

    try {
        const res = await fetch(buildApiUrl("/step"));
        const data = await res.json();
        if (!res.ok) {
            handleUnsupportedAlgo();
            return { done: true };
        }

        if (data.current_state) {
            const prev = _prevBoard;
            const next = data.current_state;
            const movedNum = prev ? next[prev.indexOf(0)] : null;
            render(next, movedNum);
        }
        if (data.current_state) pushHistoryStep(data.current_state);
        if (typeof data.nodes_explored !== "undefined") {
            getById("nodes").innerText = data.nodes_explored;
        }
        if (typeof data.frontier_size !== "undefined") {
            getById("frontier").innerText = data.frontier_size;
        }
        const explored = typeof data.nodes_explored === "number" ? data.nodes_explored : 0;
        updateRemainingEstimate(explored, Boolean(data.finished), Boolean(data.success));
        if (Array.isArray(data.final_path) && data.final_path.length) {
            state.solutionPath = data.final_path;
            state.selectedSolutionIndex = state.solutionPath.length - 1;
            renderSolutionPath(state.solutionPath);
        }
        updateTraceFromResponse(data);

        if (data.finished) {
            if (data.success) {
                getById("time").innerText = data.processing_time || "-";
                setStatus("Đã tìm thấy goal");
            } else {
                setStatus("Không tìm thấy lời giải");
            }
            return { done: true };
        }
        return { done: false };
    } catch (e) {
        setStatus("Lỗi kết nối backend");
        return { done: true };
    } finally {
        state.isFetchingStep = false;
    }
}

async function nextStep() {
    if (state.compareMode) return alert("Dang o Compare Mode. Vui long dung nut Compare.");
    if (state.autoRun) return alert("Đang Auto Run. Hãy pause trước khi đi từng bước.");
    await fetchOneStep();
}

async function startSearch() {
    if (state.compareMode) return alert("Dang o Compare Mode. Vui long dung nut Compare.");
    if (state.autoRun) return;
    if (state.isRunning) return;

    state.isRunning = true;
    state.autoRun = true;
    state.isPaused = false;

    const pauseBtn = getById("pause-btn");
    pauseBtn.disabled = false;
    pauseBtn.innerText = "Pause";
    setStatus(`Đang Auto Run ${state.currentAlgorithm.toUpperCase()}...`);
    syncTopbarButtons();

    let done = false;
    while (state.autoRun && !done) {
        if (state.isPaused) {
            await new Promise(r => setTimeout(r, 120));
            continue;
        }
        const result = await fetchOneStep();
        done = result.done;
        if (!done) await new Promise(r => setTimeout(r, getDelayMs()));
    }

    state.autoRun = false;
    state.isRunning = false;
    state.isPaused = false;
    pauseBtn.disabled = true;
    pauseBtn.innerText = "Pause";
    syncTopbarButtons();
}

async function loadSourceCode() {
    try {
        const res = await fetch(`${API_BASE}/source/${encodeURIComponent(state.currentAlgorithm)}`);
        const data = await res.json();
        state.bfsSourceCache = res.ok && data.source ? data.source : "Không tải được mã nguồn thuật toán.";
        state.currentSourceLanguage = res.ok && data.language ? String(data.language).toLowerCase() : "python";
    } catch (err) {
        state.bfsSourceCache = "Không thể kết nối backend để lấy mã nguồn thuật toán.";
        state.currentSourceLanguage = "python";
    }

    try {
        const frontendRes = await fetch("./app.js");
        state.frontendSourceCache = await frontendRes.text();
    } catch (err) {
        state.frontendSourceCache = "Không đọc được mã frontend từ file app.js.";
    }

    showBfsSource();
}

function showBfsSource() {
    getById("source-title").innerText = `Thuật toán ${state.currentAlgorithm.toUpperCase()} (Python)`;
    renderHighlightedSource(state.bfsSourceCache || "Đang tải...", state.currentSourceLanguage);
}

function showFrontendSource() {
    getById("source-title").innerText = "Frontend (JavaScript)";
    renderHighlightedSource(state.frontendSourceCache || "Không có dữ liệu.", "javascript");
}

async function showAlgorithmSource() {
    try {
        // Lấy tên thuật toán hiện tại từ state
        const currentAlgo = state.currentAlgorithm || "bfs";
        const res = await fetch(`${API_BASE}/source/${currentAlgo}`);
        const data = await res.json();
        
        if (data.ok) {
            document.getElementById("source-title").innerText = data.title;
            document.getElementById("source-code").innerText = data.source;
        } else {
            document.getElementById("source-code").innerText = "Lỗi: " + data.error;
        }
    } catch (err) {
        document.getElementById("source-code").innerText = "Lỗi kết nối backend để tải mã nguồn.";
    }
}


function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function renderHighlightedSource(sourceText, language) {
    const target = getById("source-code");
    const escaped = escapeHtml(sourceText);
    let html = escaped;

    if (language === "python") {
        const kw = /\b(def|class|if|elif|else|for|while|return|in|not|and|or|import|from|as|try|except|raise|with|pass|break|continue|True|False|None)\b/g;
        html = html.replace(kw, '<span class="tok-kw">$1</span>');
        html = html.replace(/\b(\d+)\b/g, '<span class="tok-num">$1</span>');
    } else {
        const kw = /\b(const|let|var|function|if|else|for|while|return|async|await|try|catch|throw|class|new|import|from|export|true|false|null|undefined)\b/g;
        html = html.replace(kw, '<span class="tok-kw">$1</span>');
        html = html.replace(/\b(\d+)\b/g, '<span class="tok-num">$1</span>');
    }

    target.innerHTML = html;
}

function setupAlgorithmMenu() {
    document.querySelectorAll(".algo-item").forEach(btn => {
        btn.addEventListener("click", async () => {
            if (state.isRunning) return alert("Hãy dừng thuật toán trước khi đổi thuật toán khác.");
            document.querySelectorAll(".algo-item").forEach(x => x.classList.remove("active"));
            btn.classList.add("active");
            state.currentAlgorithm = btn.dataset.algo;
            const name = btn.innerText.trim();
            setStatus(`${name} đã được chọn`);
            // Reset cả backend engine của thuật toán mới để tránh giữ trạng thái finished/solved cũ.
            await resetSearch();
            showAlgorithmSource();
            loadSourceCode();
            syncTopbarButtons();
            
        });
    });
}

function setupCompareControls() {
    const nodeLimitEl = getById("compare-node-limit");
    const compareAEl = getById("compare-a");
    const compareBEl = getById("compare-b");

    if (nodeLimitEl) {
        const clampNodeLimit = () => clampNumberInputValue(nodeLimitEl, 5000);
        ["change", "blur"].forEach(eventName => {
            nodeLimitEl.addEventListener(eventName, clampNodeLimit);
        });
    }

    const refreshCompareSelectionPreview = () => {
        if (!state.compareMode || state.compareIsRunning) return;
        const summary = getById("compare-summary");
        const metrics = getById("compare-metrics");
        const traversal = getById("compare-traversal");
        if (summary) summary.innerText = "Chọn 2 thuật toán và bấm Compare.";
        if (metrics) metrics.innerHTML = "";
        if (traversal) traversal.innerHTML = "";
        renderCompareSplit(null);
    };

    [compareAEl, compareBEl].forEach(selectEl => {
        if (!selectEl) return;
        selectEl.addEventListener("change", refreshCompareSelectionPreview);
    });
}

async function solveInstant() {
    if (state.isRunning) return alert("Hãy dừng thuật toán trước.");

    setStatus(`Đang giải ${state.currentAlgorithm.toUpperCase()}...`);
    state.isRunning = true;
    state.autoRun = false;
    state.isPaused = false;
    const pauseBtn = getById("pause-btn");
    pauseBtn.disabled = true;
    pauseBtn.innerText = "Pause";
    syncTopbarButtons();
    try {
        const res = await fetch(`${API_BASE}/solve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                algo: state.currentAlgorithm,
                initial_state: state.currentInitialState,
                max_steps: 200000,
            }),
        });
        const data = await res.json();
        if (!res.ok) return handleUnsupportedAlgo();

        if (!data.success || !data.final_path?.length) {
            setStatus("Không tìm thấy lời giải.");
            return;
        }

        getById("nodes").innerText = data.nodes_explored;
        getById("time").innerText = data.elapsed_ms + "ms";

        // Replay từng bước có delay
        state.isRunning = true;
        state.traversalHistory = [];

        for (let i = 0; i < data.final_path.length; i++) {
            if (!state.isRunning) break; // cho phép Reset dừng giữa chừng

            const stepState = data.final_path[i];
            const prev = i > 0 ? data.final_path[i - 1] : null;
            const movedNum = prev ? stepState[prev.indexOf(0)] : null;

            pushHistoryStep(stepState);
            render(stepState, movedNum);
            setStatus(`Bước ${i + 1} / ${data.final_path.length}`);

            if (i < data.final_path.length - 1) {
                await new Promise(r => setTimeout(r, getDelayMs()));
            }
        }

        state.isRunning = false;
        setStatus(`Hoàn thành — ${data.path_length} bước, ${data.nodes_explored} nút đã duyệt`);
        syncTopbarButtons();

    } catch (err) {
        state.isRunning = false;
        setStatus("Lỗi kết nối backend.");
        syncTopbarButtons();
    }
}

window.startSearch = startSearch;
window.nextStep = nextStep;
window.togglePause = togglePause;
window.resetSearch = resetSearch;
window.randomizeInput = randomizeInput;
window.showBfsSource = showBfsSource;
// window.showFrontendSource = showFrontendSource;
window.compareAlgorithms = compareAlgorithms;
window.toggleCompareMode = toggleCompareMode;
window.showAlgorithmSource = showAlgorithmSource;

render(state.currentInitialState, false);
resetHistory(state.currentInitialState);
setupAlgorithmMenu();
setupCompareControls();
loadSourceCode();
syncTopbarButtons();
resetSearch();
