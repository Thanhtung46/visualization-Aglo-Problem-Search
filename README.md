# AI Algorithm Visualizer (8-Puzzle)

Project mo phong thuat toan tim kiem tren bai toan 8-puzzle.
Hien tai backend da implement day du cho `BFS`, cac engine khac dang de placeholder.

---

## 1) Chay nhanh du an

### Yeu cau
- Python 3.10+
- Packages:
  - `flask`
  - `flask-cors`

### Cai dat
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask-cors
```

### Chay backend
```bash
python3 app.py

sau đó ấn vào IP hiện lên
```
Backend mac dinh: `http://127.0.0.1:5000`

### Mo frontend
- Cach 1: mo truc tiep `index.html`
- Cach 2 (khuyen nghi):
```bash
python3 -m http.server 8080
```
Sau do vao: `http://127.0.0.1:8080`

---

## 2) Kien truc thu muc

```text

├── app.py                      # File chạy chính (Backend Flask)
├── .gitignore                  # Cấu hình bỏ qua các file khi dùng Git
├── README.md                   # Tài liệu hướng dẫn dự án
├── engines/                    # Thư mục chứa các thuật toán tìm kiếm
│   ├── __init__.py
│   ├── __pycache__/            # File biên dịch Python (tự động sinh ra)
│   ├── base_engine.py          # Interface/Lớp trừu tượng chung
│   ├── puzzle_common.py        # Các hàm bổ trợ cho 8-puzzle
│   ├── registry.py             # Quản lý việc đăng ký các engine
│   ├── bfs_engine.py           # Thuật toán Breadth-First Search
│   ├── dfs_engine.py           # Thuật toán Depth-First Search
│   ├── ucs_engine.py           # Thuật toán Uniform Cost Search
│   ├── astar_engine.py         # Thuật toán A* Search
│   ├── iddfs_engine.py         # Thuật toán Iterative Deepening DFS
│   ├── bidirectional_engine.py # Thuật toán Tìm kiếm 2 chiều
│   ├── beam_engine.py          # Thuật toán Beam Search
│   └── idastar_engine.py       # Thuật toán IDA* Search
└── UI/                         # Thư mục chứa giao diện người dùng
    ├── static/                 # Chứa các tài nguyên tĩnh
    │   ├── app.js              # Xử lý logic Frontend (gọi API)
    │   └── styles.css          # Định dạng giao diện
    └── templates/              # Chứa các tệp giao diện HTML
        └── index.html          # Trang web chính   
```

---

## 3) API contract de UI hien thi dung

Frontend dang doc du lieu theo contract sau. Khi viet engine moi, can giu dung format nay.

### `GET /step?algo=<key>`
Payload toi thieu:
- `finished: bool`
- `success: bool` (chi can khi `finished = true`)
- `current_state: number[9]`
- `nodes_explored: number`
- `frontier_size: number`

Payload cho trace:
- `trace_program: string[]`
- `trace_history: { line, message, nodes_explored }[]`
- `trace_step: { line, message, nodes_explored }[]`

Neu tim thay dich:
- `processing_time: string` (vi du `"0.0231s"`)
- `final_path: number[9][]`

### `POST /reset?algo=<key>`
- `ok: true`
- `current_state: number[9]`
- `trace_program`, `trace_history`

### `POST /random-state?algo=<key>`
- `ok: true`
- `current_state: number[9]`
- `trace_program`, `trace_history`

### `GET /source/<key>`
- `ok: true`
- `filename`, `title`, `source`

Neu algo chua dang ky:
```json
{"error": "Unsupported algorithm: <algo_key>"}
```

---

## 4) Huong dan viet logic thuat toan moi

Vi du them `UCS`.

### Buoc A - Tao file engine
Tao file: `engines/ucs_engine.py`

Template:
```python
from engines.base_engine import BaseAlgorithmEngine

class UCS8PuzzleEngine(BaseAlgorithmEngine):
    key = "ucs"
    display_name = "Uniform Cost Search (UCS)"
    source_filename = "ucs_algorithm.py"
    source_title = "UCS Algorithm Source"

    def __init__(self):
        # khoi tao state noi bo
        pass

    def step(self):
        # tra payload theo API contract (section 3)
        pass

    def reset(self):
        # reset state + tra current_state + trace
        pass

    def random_state(self):
        # random initial state + reset state
        pass

    def algorithm_source(self):
        # tra source code de hien thi tren UI
        return "def ucs_8puzzle(...):\\n    ..."
```

### Buoc B - Dang ky engine trong registry
Sua `engines/registry.py`:
```python
from engines.ucs_engine import UCS8PuzzleEngine

def build_default_engines():
    return {
        BFS8PuzzleEngine.key: BFS8PuzzleEngine(),
        UCS8PuzzleEngine.key: UCS8PuzzleEngine(),
    }
```

### Buoc C - Kiem tra key phu hop voi FE
Trong `index.html`, menu sidebar da co `data-algo`.
Dam bao `data-algo` trung voi `key` trong engine (vi du: `ucs`).

### Buoc D - Test local
```bash
curl -s -X POST "http://127.0.0.1:5000/reset?algo=ucs"
curl -s "http://127.0.0.1:5000/step?algo=ucs"
curl -s "http://127.0.0.1:5000/source/ucs"
```

Neu 3 API tren tra dung format => UI se hien thi duoc.

---

## 5) Frontend can chinh sua o dau khi them algorithm

Frontend da support chon algo dong theo `data-algo`, nhung ban can check:

1. `index.html`
   - Sidebar co button:
   ```html
   <button class="algo-item" data-algo="ucs">Uniform Cost Search (UCS)</button>
   ```
   - Dropdown compare co option tuong ung:
   ```html
   <option value="ucs">UCS</option>
   ```

2. `app.js`
   - Khong can sua logic core neu API contract giu nguyen.
   - Cac ham se tu dong goi:
     - `/step?algo=<key>`
     - `/reset?algo=<key>`
     - `/random-state?algo=<key>`
     - `/source/<key>`
     - `/compare` (neu dung panel so sanh)

3. `styles.css`
   - Thuong khong can sua, chi sua neu ban muon style rieng cho algo moi.

---

## 6) Checklist de engine ket noi duoc UI

- [ ] File engine moi da tao trong `engines/`
- [ ] Class ke thua `BaseAlgorithmEngine`
- [ ] Co `key` duy nhat (vd `ucs`)
- [ ] Da dang ky trong `engines/registry.py`
- [ ] `step/reset/random_state/source` tra dung contract
- [ ] Sidebar + compare dropdown co `data-algo`/`value` khop key
- [ ] Test bang curl thanh cong truoc khi test UI

---

## 7) Trang thai hien tai

- Active backend: `BFS`
- Placeholder files: `DFS`, `UCS`, `A*`, `IDDFS`, `Bidirectional`, `Beam`, `IDA*`, `Advanced`

Ban co the implement dan tung engine, dang ky vao registry, va UI se dung duoc ngay neu contract dung.
