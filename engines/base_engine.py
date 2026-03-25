from abc import ABC, abstractmethod


class BaseAlgorithmEngine(ABC):
    key = "base"
    display_name = "Base Engine"
    source_filename = "algorithm.py"
    source_title = "Algorithm Source"

    @abstractmethod
    def step(self):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError

    @abstractmethod
    def random_state(self):
        raise NotImplementedError

    @abstractmethod
    def algorithm_source(self):
        raise NotImplementedError
