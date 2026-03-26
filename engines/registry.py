from typing import Dict

from engines.base_engine import BaseAlgorithmEngine
from engines.bfs_engine import BFS8PuzzleEngine
from engines.dfs_engine import DFS8PuzzleEngine
from engines.ucs_engine import UCS8PuzzleEngine
from engines.iddfs_engine import IDDFS8PuzzleEngine

def build_default_engines() -> Dict[str, BaseAlgorithmEngine]:
    # BFS and DFS are active.
    return {
        BFS8PuzzleEngine.key: BFS8PuzzleEngine(),
        DFS8PuzzleEngine.key: DFS8PuzzleEngine(),
        UCS8PuzzleEngine.key: UCS8PuzzleEngine(),
        IDDFS8PuzzleEngine.key: IDDFS8PuzzleEngine(),
    }
