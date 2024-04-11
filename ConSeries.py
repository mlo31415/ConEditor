from __future__ import annotations
import json

from WxDataGrid import GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from HelpersPackage import RemoveAccents
from FanzineIssueSpecPackage import FanzineDateRange
from Log import Log


####################################################################################
class Con(GridDataRowClass):
    def __init__(self):
        self._name: str=""                  # Name including number designation
        self._locale: str=""                # Name of locale where the con was held
        self._dates: FanzineDateRange|None =None      # Date range of the con
        self._gohs: str=""                  # A list of the con's GoHs
        self._URL: str=""                   # The URL of the individual con page, if any

    def Signature(self) -> int:        
        return hash(self._name)+hash(self._locale)+hash(self._dates)+hash(self._gohs)+hash(self._URL)

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
    def Dates(self) -> FanzineDateRange|None:        
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

    # Get or set a value by name or column number
    #def GetVal(self, name: Union[str, int]) -> Union[str, int, FanzineDateRange]:
    def __getitem__(self, index: str|int|slice) -> str|int|FanzineDateRange:        
        # (Could use return eval("self."+name))
        if index == "Name" or index == 0:
            return self.Name
        if index == "Dates" or index == 1:
            return self.Dates
        if index == "Locale" or index == 2:
            return self.Locale
        if index == "GoHs" or index == 3:
            return self.GoHs
        if index != 4:  # Index == 4 is normal, being the terminator of an iteration through the columns
            Log(f"Con(GridDataRowClass).__getitem__({index}) does not exist")
        raise IndexError


    def __setitem__(self, index: str|int|slice, value: str|int|FanzineDateRange) -> None:        
        # (Could use return eval("self."+name))
        if index == "Name" or index == 0:
            self.Name=value
            return
        if index == "Dates" or index == 1:
            self.Dates=FanzineDateRange().Match(value)
            return
        if index == "Locale" or index == 2:
            self.Locale=value
            return
        if index == "GoHs" or index == 3:
            self.GoHs=value
            return
        Log(f"Con(GridDataRowClass).__putitem__({index}) does not exist")
        raise IndexError

    # def IsEmptyRow(self) -> bool:  
    #     return self._name != "" or self._locale != "" or self._dates.IsEmpty() != "" or self._gohs != "" or self._URL != ""

    @property
    def IsEmptyRow(self) -> bool:        
        return (self._name or self._name == "") and (self._locale or self._locale == "") and (self._dates is None or type(self._dates) is str  or self._dates.IsEmpty())  and (self._gohs or self._gohs == "") and (self._URL or self._URL == "")

####################################################################################
class ConSeries(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList=ColDefinitionsList([
            ColDefinition("Name", Type="url", Width=30, IsEditable=IsEditable.Maybe),
            ColDefinition("Dates", Type="date range", Width=30),
            ColDefinition("Locale", Width=30),
            ColDefinition("GoHs", Width=30),
        ])
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

    def Signature(self) -> int:        
        return hash(self._name)+sum([x.Signature()*(i+1) for i, x in enumerate(self.Rows)])

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
    def ColDefs(self) -> ColDefinitionsList:        
        return self._colDefs

    #------------
    @property
    def Name(self) -> str:        
        return self._name
    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val


    def InsertEmptyRows(self, index: int, num: int=1) -> None:        
        if num <= 0:
            return
        if index > len(self.Rows):
            index=len(self.Rows)
        self.Rows=self.Rows[:index]+[Con() for i in range(num)]+self.Rows[index:]

