from __future__ import annotations
from typing import Optional, List

from FanzineIssueSpecPackage import FanzineDateRange


####################################################################################
class Con:
    def __init__(self):
        self._seq: Optional[int]=None       # Sequence number starting from from 1 or 0
        self._name: str=""                  # Name including number designation
        self._locale: str=""                # Name of locale where the con was held
        self._dates: Optional[FanzineDateRange]=None      # Date range of the con
        self._gohs: str=""                  # A list of the con's GoHs

    @property
    def Seq(self) ->Optional[int]:
        return self._seq

    @Seq.setter
    def Seq(self, val: int):
        self._seq=val

    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str):
        self._name=val

    @property
    def GoHs(self) -> str:
        return self._gohs

    @GoHs.setter
    def GoHs(self, val: str):
        self._gohs=val

    @property
    def Locale(self) -> str:
        return self._locale

    @Locale.setter
    def Locale(self, val: str):
        self._locale=val

    @property
    def Dates(self) -> Optional[FanzineDateRange]:
        return self._dates

    @Dates.setter
    def Dates(self, val: FanzineDateRange):
        self._dates=val

    def Val(self, name: str) -> str:
        # (Could use return eval("self."+name))
        if name == "Seq":
            return str(self.Seq)
        if name == "Name":
            return self.Name
        if name == "Dates":
            return str(self.Dates)
        if name == "Locale":
            return self.Locale
        if name == "GoHs":
            return self.GoHs
        return "Can't interpret '"+name+"'"


####################################################################################
class ConSeries:
    def __init__(self):
        self._name: str=""
        self._series: List[Con]=[]
        self._text: str=""
        self._colheaders: List[str]=["Seq", "Name", "Dates", "Locale", "GoHs"]

    #------------
    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    #------------
    @property
    def Text(self) -> str:
        return self._text

    @Text.setter
    def Text(self, val: str) -> None:
        self._text=val

    #------------
    @property
    def Colheaders(self) -> List[str]:
        return self._colheaders

    @Colheaders.setter
    def Colheaders(self, val: List[str]) -> None:
        self._colheaders=val

    #------------
    @property
    def Rows(self) -> List[Con]:
        return self._series

    @Rows.setter
    def Rows(self, val: List[Con]) -> None:
        self._series=val

    #------------------------------
    @property
    def NumRows(self) -> int:
        return len(self._series)


    def IdentifyColumnHeaders(self):
        assert(False)
    def Save(self, name: str) -> None:
        assert(False)





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