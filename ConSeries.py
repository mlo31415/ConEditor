from __future__ import annotations
from typing import Optional, List, Union

from Grid import GridDataSource

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

    # Get or set a value by name or column number
    def GetVal(self, name: Union[str, int]) -> str:
        # (Could use return eval("self."+name))
        if name == "Seq" or name == 0:
            return self.Seq
        if name == "Name" or name == 1:
            return self.Name
        if name == "Dates" or name == 2:
            return self.Dates
        if name == "Locale" or name == 3:
            return self.Locale
        if name == "GoHs" or name == 4:
            return self.GoHs
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, name: Union[str, int], val: str):
        # (Could use return eval("self."+name))
        if name == "Seq" or name == 0:
            self.Seq=val
            return
        if name == "Name" or name == 1:
            self.Name=val
            return
        if name == "Dates" or name == 2:
            self.Dates=val
            return
        if name == "Locale" or name == 3:
            self.Locale=val
            return
        if name == "GoHs" or name == 4:
            self.GoHs=val
            return
        return "SetVal can't interpret '"+str(name)+"'"

####################################################################################
class ConSeries(GridDataSource):
    _colheaders: List[str]=["Seq", "Name", "Dates", "Locale", "GoHs"]
    _coltypes: List[str]=["int", "str", "date range", "str", "str"]
    _colminwidths: List[str]=[30, 30, 30, 30, 30]

    def __init__(self):
        self._name: str=""
        self._series: List[Con]=[]
        self._stuff: str=""

    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> List[str]:
        return ConSeries._colheaders

    @property
    def ColTypes(self) -> List[str]:
        return ConSeries._coltypes

    @property
    def ColMinWidths(self) -> List[str]:
        return ConSeries._colminwidths

    @property
    def NumRows(self) -> int:
        return len(self._series)

    def Data(self, iRow: int, iCol: int) -> str:
        return self.Rows[iRow].GetVal(self.ColHeaders[iCol])

    @property
    def Rows(self) -> List:
        return self._series

    @Rows.setter
    def Rows(self, rows: List) -> None:
        self._series=rows

    #------------
    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val

    #------------
    @property
    def Stuff(self) -> str:
        return self._stuff

    @Stuff.setter
    def Stuff(self, val: str) -> None:
        self._stuff=val

    #------------
    @property
    def Rows(self) -> List[Con]:
        return self._series

    @Rows.setter
    def Rows(self, val: List[Con]) -> None:
        self._series=val

    def IdentifyColumnHeaders(self):
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