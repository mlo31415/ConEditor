from __future__ import annotations
from typing import Optional, List, Union, Tuple
import json

from DataGrid import GridDataSource

from FanzineIssueSpecPackage import FanzineDateRange


####################################################################################
class Con:
    def __init__(self):
        self._seq: Optional[int]=None       # Sequence number starting from from 1 or 0
        self._name: str=""                  # Name including number designation
        self._locale: str=""                # Name of locale where the con was held
        self._dates: Optional[FanzineDateRange]=None      # Date range of the con
        self._gohs: str=""                  # A list of the con's GoHs
        self._URL: str=""                   # The URL of the individual con page, if any

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 2,
           "_seq": self._seq,
           "_name": self._name,
           "_locale": self._locale,
           "_dates": str(self._dates),
           "_URL": self._URL,
           "_gohs": self._gohs}
        return json.dumps(d)

    def FromJson(self, val: str) -> Con:
        d=json.loads(val)
        self._seq=d["_seq"]
        self._name=d["_name"]
        self._locale=d["_locale"]
        self._gohs=d["_gohs"]
        self._dates=FanzineDateRange().Match(d["_dates"])
        if "_URL" in d.keys():
            self._URL=d["_URL"]
        else:
            self._URL=""
        return self


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

    @property
    def URL(self) -> str:
        return self._URL
    @URL.setter
    def URL(self, val: str):
        self._URL=val

    @property
    def IsText(self) -> bool:
        return False

    # Get or set a value by name or column number
    def GetVal(self, name: Union[str, int]) -> Union[str, int, FanzineDateRange]:
        # (Could use return eval("self."+name))
        if name == "Name" or name == 0:
            return self.Name
        if name == "Dates" or name == 1:
            return self.Dates
        if name == "Locale" or name == 2:
            return self.Locale
        if name == "GoHs" or name == 3:
            return self.GoHs
        return "Val can't interpret '"+str(name)+"'"

    def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int, FanzineDateRange]) -> None:
        # (Could use return eval("self."+name))
        if nameOrCol == "Name" or nameOrCol == 0:
            self.Name=val
            return
        if nameOrCol == "Dates" or nameOrCol == 1:
            self.Dates=val
            return
        if nameOrCol == "Locale" or nameOrCol == 2:
            self.Locale=val
            return
        if nameOrCol == "GoHs" or nameOrCol == 3:
            self.GoHs=val
            return
        print("SetVal can't interpret '"+str(nameOrCol)+"'")



####################################################################################
class ConSeries(GridDataSource):
    # Fixed information shared by all instances
    _colheaders: List[str]=["Name", "Dates", "Locale", "GoHs"]
    _coldatatypes: List[str]=["url", "date range", "str", "str"]
    _colminwidths: List[int]=[30, 30, 30, 30]
    _coleditable=["maybe", "yes", "yes", "yes"]
    _element=Con

    def __init__(self):
        GridDataSource.__init__(self)
        self._name: str=""
        self._series: List[Con]=[]
        self._stuff: str=""
        self._updated: bool=False

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 3,
           "_colheaders": self._colheaders,
           "_coldatatypes": self._coldatatypes,
           "_colminwidths": self._colminwidths,
           "_coleditable": self._coleditable,
           "_name": self._name,
           "_stuff": self._stuff}
        for i, s in enumerate(self._series):
            d[i]=s.ToJson()
        return json.dumps(d)

    def FromJson(self, val: str) -> ConSeries:
        d=json.loads(val)
        # self._colheaders=d["_colheaders"]
        # self._coldatatypes=d["_coldatatypes"]
        # self._colminwidths=d["_colminwidths"]
        self._name=d["_name"]
        self._stuff=d["_stuff"]
        self._series=[]
        i=0
        while str(i) in d.keys():       # This is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._series.append(Con().FromJson(d[str(i)]))
            i+=1

        self.MakeTextLinesEditable()

        return self

    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> List[str]:
        return ConSeries._colheaders

    @property
    def ColDataTypes(self) -> List[str]:
        return ConSeries._coldatatypes

    @property
    def ColMinWidths(self) -> List[int]:
        return ConSeries._colminwidths

    @property
    def ColEditable(self) -> List[str]:
        return ConSeries._coleditable


    @property
    def NumRows(self) -> int:
        return len(self._series)

    def GetData(self, iRow: int, iCol: int) -> str:
        if iRow == -1:  # Handle logical coordinate of column headers
            return self.ColHeaders[iCol]

        r=self.Rows[iRow]
        return r.GetVal(iCol)

    @property
    def Rows(self) -> List:
        return self._series

    @Rows.setter
    def Rows(self, rows: List) -> None:
        self._series=rows
        self._updated=True

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str, FanzineDateRange]) -> None:
        self._series[irow].SetVal(icol, val)
        self._updated=True

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

    # ------------
    @property
    def Updated(self) -> bool:
        return self._updated

    @Updated.setter
    def Updated(self, val: bool) -> None:
        self._updated=val