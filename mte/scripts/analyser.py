import abc
from pathlib import Path
from typing import List


class Analyser(abc.ABC):

    @property
    @abc.abstractmethod
    def executables(self) -> List[str]:
        pass

    @abc.abstractmethod
    def analyse(self, executable: str, root: Path) -> None:
        pass


class ExampleAnaylser(Analyser):

    @property
    def executables(self) -> List[str]:
        return ["ycsb_exampledb_O0", "ycsb_exampledb_O3"]

    def analyse(self, executable: str, root: Path) -> None:
        pass


def map_analyser(datastructure: str) -> Analyser:
    datastructure = datastructure.lower()

    return {"exampledb": ExampleAnaylser()}[datastructure]
