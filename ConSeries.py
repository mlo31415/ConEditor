from __future__ import annotations
from typing import Optional, Union
import json

from WxDataGrid import GridDataSource
from HelpersPackage import RemoveAccents
from FanzineIssueSpecPackage import FanzineDateRange


####################################################################################
class Con:
    def __init__(self):
        self._name: str=""                  # Name including number designation
        self._locale: str=""                # Name of locale where the con was held
        self._dates: Optional[FanzineDateRange]=None      # Date range of the con
        self._gohs: str=""                  # A list of the con's GoHs
        self._URL: str=""                   # The URL of the individual con page, if any

    def Signature(self) -> int:
        sum=hash(self._name.strip()+self._locale.strip()+self._gohs.strip()+self._URL.strip())
        return sum+hash(self._dates)

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 3,
           "_name": self._name,
           "_locale": self._locale,
           "_dates": str(self._dates),
           "_URL": self._URL,
           "_gohs": self._gohs}
        return json.dumps(d)

    def FromJson(self, val: str) -> Con:
        d=json.loads(val)
        self._name=RemoveAccents(d["_name"])
        self._locale=d["_locale"]
        self._gohs=d["_gohs"]
        self._dates=FanzineDateRange().Match(d["_dates"])
        if "_URL" in d.keys():
            self._URL=d["_URL"]
        else:
            self._URL=""
        return self


    @property
    def Name(self) -> str:
        return self._name
    @Name.setter
    def Name(self, val: str):
        self._name=RemoveAccents(val)

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
    def URL(self, val: str) -> None:
        self._URL=val

    @property
    def IsText(self) -> bool:
        return False
    @property
    def IsLink(self) -> bool:
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
    _colheaders: list[str]=["Name", "Dates", "Locale", "GoHs"]
    _coldatatypes: list[str]=["url", "date range", "str", "str"]
    _colminwidths: list[int]=[30, 30, 30, 30]
    _coleditable=["maybe", "yes", "yes", "yes"]
    _element=Con

    def __init__(self):
        GridDataSource.__init__(self)
        self._name: str=""
        self._series: list[Con]=[]
        self._stuff: str=""

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
        self._name=RemoveAccents(d["_name"])    # Clean out old accented entries
        self._stuff=d["_stuff"]
        self._series=[]
        i=0
        while str(i) in d.keys():       # This is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._series.append(Con().FromJson(d[str(i)]))
            i+=1

        return self

    # Inherited from GridDataSource
    @property
    def ColHeaders(self) -> list[str]:
        return ConSeries._colheaders

    @property
    def ColDataTypes(self) -> list[str]:
        return ConSeries._coldatatypes

    @property
    def ColMinWidths(self) -> list[int]:
        return ConSeries._colminwidths

    @property
    def ColEditable(self) -> list[str]:
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
    def Rows(self) -> list:
        return self._series

    @Rows.setter
    def Rows(self, rows: list) -> None:
        self._series=rows

    def SetDataVal(self, irow: int, icol: int, val: Union[int, str, FanzineDateRange]) -> None:
        if self._coldatatypes[icol] == "date range":
            val=FanzineDateRange().Match(val)
            if val.IsEmpty():
                return
        self._series[irow].SetVal(icol, val)

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
