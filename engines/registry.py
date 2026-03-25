from typing import Dict

from engines.base_engine import BaseAlgorithmEngine
from engines.bfs_engine import BFS8PuzzleEngine
from engines.dfs_engine import DFS8PuzzleEngine


def build_default_engines() -> Dict[str, BaseAlgorithmEngine]:
    # BFS and DFS are active.
    return {
        BFS8PuzzleEngine.key: BFS8PuzzleEngine(),
        DFS8PuzzleEngine.key: DFS8PuzzleEngine(),
    }
