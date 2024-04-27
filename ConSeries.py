from __future__ import annotations

from WxDataGrid import GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from HelpersPackage import RemoveAccents
from FanzineIssueSpecPackage import FanzineDateRange
from Log import Log


####################################################################################
class Con(GridDataRowClass):
    def __init__(self, Name="", Link="", Extra="", Locale="", Dates=None, GoHs="", URL=""):
        self._name: str=Name                  # Name including number designation
        self._link: str=Link
        self._extra: str=Extra
        self._locale: str=Locale                # Name of locale where the con was held
        self._dates: FanzineDateRange|None =Dates      # Date range of the con
        self._gohs: str=GoHs                  # A list of the con's GoHs
        self._URL: str=URL                   # The URL of the individual con page, if any

    def Signature(self) -> int:        
        return hash(self._name)+hash(self._locale)+hash(self._dates)+hash(self._gohs)+hash(self._URL)


    @property
    def Name(self) -> str:        
        return self._name
    @Name.setter
    def Name(self, val: str):
        self._name=RemoveAccents(val)


    @property
    def Extra(self) -> str:
        return self._extra
    @Extra.setter
    def Extra(self, val: str):
        self._extra=RemoveAccents(val)

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
        if index == "URL" or index == 1:
            return self.URL
        if index == "Extra" or index == 2:
            return self.Extra
        if index == "Dates" or index == 3:
            return self.Dates
        if index == "Locale" or index == 4:
            return self.Locale
        if index == "GoHs" or index == 5:
            return self.GoHs
        if index != 6:  # Index == 4 is normal, being the terminator of an iteration through the columns
            Log(f"Con(GridDataRowClass).__getitem__({index}) does not exist")
        raise IndexError


    def __setitem__(self, index: str|int|slice, value: str|int|FanzineDateRange) -> None:        
        # (Could use return eval("self."+name))
        if index == "Name" or index == 0:
            self.Name=value
            return
        if index == "URL" or index == 1:
            self.URL=value
            return
        if index == "Extra" or index == 2:
            self.Extra=value
            return
        if index == "Dates" or index == 3:
            self.Dates=FanzineDateRange().Match(value)
            return
        if index == "Locale" or index == 4:
            self.Locale=value
            return
        if index == "GoHs" or index == 5:
            self.GoHs=value
            return
        Log(f"Con(GridDataRowClass).__putitem__('{index}') does not exist")
        raise IndexError

    # def IsEmptyRow(self) -> bool:  
    #     return self._name != "" or self._locale != "" or self._dates.IsEmpty() != "" or self._gohs != "" or self._URL != ""

    @property
    def IsEmptyRow(self) -> bool:        
        return ((self._name or self._name == "") and (self._link or self._link == "") and (self._extra or self._extra == "") and
                 (self._locale or self._locale == "") and (self._dates is None or type(self._dates) is str  or self._dates.IsEmpty()) and
                (self._gohs or self._gohs == "") and (self._URL or self._URL == ""))


####################################################################################
class ConSeries(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList=ColDefinitionsList([
            ColDefinition("Name", Type="text", Width=30, IsEditable=IsEditable.Maybe),
            ColDefinition("Link", Type="url", Width=30, IsEditable=IsEditable.Yes),
            ColDefinition("Extra",Type="text", Width=30, IsEditable=IsEditable.Yes),
            ColDefinition("Dates", Type="date range", Width=30),
            ColDefinition("Locale", Width=30),
            ColDefinition("GoHs", Width=30),
        ])
        self._element=Con
        self._series: list[Con]=[]  # This supplies the Rows property that GridDataSource needs
        self._name: str=""


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

