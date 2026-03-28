from typing import Dict

from engines.base_engine import BaseAlgorithmEngine
from engines.bfs_engine import BFS8PuzzleEngine
from engines.dfs_engine import DFS8PuzzleEngine
from engines.ucs_engine import UCS8PuzzleEngine
from engines.iddfs_engine import IDDFS8PuzzleEngine
from engines.bidirectional_engine import Bidirectional8PuzzleEngine
from engines.beam_engine import BeamSearch8PuzzleEngine
from engines.astar_engine import AStar8PuzzleEngine
from engines.idastar_engine import IDAStar8PuzzleEngine

def build_default_engines() -> Dict[str, BaseAlgorithmEngine]:
    return {
        BFS8PuzzleEngine.key: BFS8PuzzleEngine(),
        DFS8PuzzleEngine.key: DFS8PuzzleEngine(),
        UCS8PuzzleEngine.key: UCS8PuzzleEngine(),
        IDDFS8PuzzleEngine.key: IDDFS8PuzzleEngine(),
        Bidirectional8PuzzleEngine.key: Bidirectional8PuzzleEngine(),
        BeamSearch8PuzzleEngine.key: BeamSearch8PuzzleEngine(beam_width=3),
        AStar8PuzzleEngine.key: AStar8PuzzleEngine(),
        IDAStar8PuzzleEngine.key: IDAStar8PuzzleEngine(),
    }