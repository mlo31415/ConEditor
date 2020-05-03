from __future__ import annotations
from typing import List


class ConFile:
    def __init__(self):
        self._title: str=""
        self._pathname: str=""


class ConPage:
    def __init__(self):
        self._conFileList: List[ConFile]+[]


