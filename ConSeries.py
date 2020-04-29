from __future__ import annotations
from typing import Union, Tuple, Optional, List


class Con:
    def __init__(self):
        self._seq: Optional[int]=None       # Sequence number starting from from 1 or 0
        self._name: str=""                  # Name including number designation
        self._locale: Optional[str]=None    # Name of locale where the con was held
        self._date: Optional[str]=None      # Date of con   #TODO: Change to a date range



class ConSeries:
    def __init__(self):
        self._name: Optional[str]=None
        self._series: List[Con]=[]
        self._colheaders: List[str]=[]

    #------------
    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    #------------
    @property
    def Colheaders(self) -> List[str]:
        return self._colheaders

    @Colheaders.setter
    def Colheaders(self, val: List[str]) -> None:
        self._colheaders=val

    #------------
    @property
    def Series(self) -> Optional[List[Con]]:
        return self._series

    @Series.setter
    def Series(self, val: Optional[List[Con]]) -> None:
        self._series=val

    #?????????????
    @property
    def TopTextLines(self):
        return None
    @TopTextLines.setter
    def TopTextLines(self, val):
        pass
    @property
    def BottomTextLines(self):
        return None
    @BottomTextLines.setter
    def BottomTextLines(self, val):
        pass
    @property
    def FirstLine(self):
        return None
    @FirstLine.setter
    def FirstLine(self, val):
        pass
    @property
    def Rows(self):
        return None

    def IdentifyColumnHeaders(self):
        return None
    def Save(self):
        return None

# ---------------------------------
# Look through the data and determine the likely column we're sorted on.
# The column will be (mostly) filled and will be in ascending order.
# This is necessarily based on heuristics and is inexact.
# TODO: For the moment we're going to ignore whether the selected column is in fact sorted. We need to fix this later.
def MeasureSortColumns(self) -> None:
    # A sort column must either be the title or have a type code
    # Start by looking through the columns that have a type code and seeing which are mostly or completely filled.  Do it in order of perceived importance.
    fW=self.CountFilledCells("Whole")
    fV=self.CountFilledCells("Volume")
    fN=self.CountFilledCells("Number")
    fY=self.CountFilledCells("Year")
    fM=self.CountFilledCells("Month")

    self.SortColumn={"Whole": fW, "Vol+Num": fV*fN, "Year&Month": fY*fM}


# ---------------------------------
# Count the number of filled cells in the column with the specified type code
# Returns a floating point fraction between 0 and 1
def CountFilledCells(self, colType: str) -> float:
    try:
        index=self.ColumnHeaderTypes.index(colType)
    except:
        return 0

    # Count the number of filled-in values for this type
    num=0
    for row in self.Rows:
        if index < len(row) and row[index] is not None and len(row[index]) > 0:
            num+=1
    return num/len(self.Rows)