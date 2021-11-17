from __future__ import annotations
from typing import Optional, Union
import json

from WxDataGrid import GridDataSource, GridDataRowClass, ColDefinition
from HelpersPackage import RemoveAccents
from FanzineIssueSpecPackage import FanzineDateRange


####################################################################################
class Con(GridDataRowClass):
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
    #def GetVal(self, name: Union[str, int]) -> Union[str, int, FanzineDateRange]:
    def __getitem__(self, index: Union[str, int, slice]) -> Union[str, int, FanzineDateRange]:
        # (Could use return eval("self."+name))
        if index == "Name" or index == 0:
            return self.Name
        if index == "Dates" or index == 1:
            return self.Dates
        if index == "Locale" or index == 2:
            return self.Locale
        if index == "GoHs" or index == 3:
            return self.GoHs
        return "Val can't interpret '"+str(index)+"'"

    #def SetVal(self, nameOrCol: Union[str, int], val: Union[str, int, FanzineDateRange]) -> None:
    def __setitem__(self, index: Union[str, int, slice], value: Union[str, int, FanzineDateRange]) -> None:
        # (Could use return eval("self."+name))
        if index == "Name" or index == 0:
            self.Name=value
            return
        if index == "Dates" or index == 1:
            self.Dates=value
            return
        if index == "Locale" or index == 2:
            self.Locale=value
            return
        if index == "GoHs" or index == 3:
            self.GoHs=value
            return
        print("SetVal can't interpret '"+str(index)+"'")





####################################################################################
class ConSeries(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: list[ColDefinition]=[
            ColDefinition("Name", Type="url", Width=30, IsEditable="maybe"),
            ColDefinition("Dates", Type="date range", Width=30),
            ColDefinition("Locale", Width=30),
            ColDefinition("GoHs", Width=30),
        ]
        self._element=Con
        self._series: list[Con]=[]  # This supplies the Rows property that GridDataSource needs
        self._name: str=""

    # Serialize and deserialize
    def ToJson(self) -> str:
        d={"ver": 5,
           "_name": self._name}
        for i, s in enumerate(self._series):
            d[i]=s.ToJson()
        return json.dumps(d)

    def FromJson(self, val: str) -> ConSeries:
        d=json.loads(val)
        self._name=RemoveAccents(d["_name"])    # Clean out old accented entries
        self._series=[]
        i=0
        while str(i) in d.keys():       # This is because json merges 1 and "1" as the same. (It appears to be a bug.)
            self._series.append(Con().FromJson(d[str(i)]))
            i+=1

        return self

    def __getitem__(self, index) -> Con:
        assert index != -1
        return self._series[index]

    def __setitem__(self, index: int, val: Con):
        self._series[index]=val

    def Signature(self) -> int:        #  ConSeries(GridDataSource)
        return hash(self._name)+sum([hash(x)*(i+1) for i, x in enumerate(self.Rows)])

    @property
    def NumRows(self) -> int:
        return len(self._series)

    @property
    def Rows(self) -> list[Con]:
        return self._series

    @Rows.setter
    def Rows(self, rows: list[Con]) -> None:
        self._series=rows


    @property
    def ColDefs(self) -> list[ColDefinition]:
        return self._colDefs

    #------------
    @property
    def Name(self) -> str:
        return self._name

    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val
