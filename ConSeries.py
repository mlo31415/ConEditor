from __future__ import annotations

import re
from urllib.parse import unquote

from WxDataGrid import GridDataSource, GridDataRowClass, ColDefinition, ColDefinitionsList, IsEditable
from FanzineDateTime import FanzineDateRange
from Log import Log


# The CSP "Extra" string (everything rendered after the linked Display Name) is split, for editing,
# into a Special Text -- a leading "(alternate name)" -- and free-form Notes/Other. SplitExtra and
# JoinExtra are EXACT inverses: JoinExtra(*SplitExtra(x)) == x for any string. That is what keeps the
# html round-trip byte-identical (verified across all 2274 Convention cells on conpubs).
def SplitExtra(extra: str) -> tuple[str, str]:
    m=re.match(r"^\((.*?)\)(?: (.*))?$", extra)      # a clean leading "(yyy)" optionally + " rest"
    return (m.group(1), m.group(2) or "") if m else ("", extra)

def JoinExtra(specialText: str, notes: str) -> str:
    parts=[]
    if specialText:
        parts.append(f"({specialText})")
    if notes:
        parts.append(notes)
    return " ".join(parts)


####################################################################################
# Note that the order of the cells in the row for a ConSeries row is fixed.
class Con(GridDataRowClass):
    def __init__(self, Name="", Link="", Extra="", Locale="", Dates=None, GoHs="", URL="") -> None:
        self._name: str=Name                  # Name including number designation
        self._link: str=Link
        self._specialText, self._notes=SplitExtra(Extra)   # the single "Extra" string -> (Special Text, Notes)
        self._locale: str=Locale                # Name of locale where the con was held
        self._dates: FanzineDateRange|None =Dates      # Date range of the con
        self._gohs: str=GoHs                  # A list of the con's GoHs
        self._URL: str=URL                   # The URL of the individual con page, if any

    def __hash__(self) -> int:
        return hash(self._name)+hash(self._locale)+hash(self._dates)+hash(self._gohs)+hash(self._URL)
    def Signature(self) -> int:
        return self.__hash__()

    @property
    def Name(self) -> str:        
        return self._name.strip()
    @Name.setter
    def Name(self, val: str) -> None:
        self._name=val


    # Extra is the legacy single string rendered after the linked Display Name. It is now COMPUTED from
    # the two editable fields (Special Text, Notes), so every existing caller and the html round-trip are
    # unchanged; only the internal storage moved.
    @property
    def Extra(self) -> str:
        return JoinExtra(self._specialText, self._notes)
    @Extra.setter
    def Extra(self, val: str) -> None:
        self._specialText, self._notes=SplitExtra(val)

    # The two fields the Extras dialog edits. Special Text is stored bare (no parentheses); it is what
    # renders inside the "(...)" right after the Display Name. For a cross-link row (see IsCrossLink),
    # Special Text is by convention the *target* convention's name on the far end of the link -- it must
    # be set from the link target, not from free-form input (cf. ConSeriesFrame.OnPopupLinkToAnotherConInstance).
    @property
    def SpecialText(self) -> str:
        return self._specialText
    @SpecialText.setter
    def SpecialText(self, val: str) -> None:
        self._specialText=val

    @property
    def Notes(self) -> str:
        return self._notes
    @Notes.setter
    def Notes(self, val: str) -> None:
        self._notes=val

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

    # A cross-link points at a con instance stored under a *different* con series (DSC-style
    # "../OtherSeries/Con/index.html"). Its files are owned and edited only from that other series.
    # For such a row, the parenthesized Extra (SpecialText) holds the target con's name on the far end.
    @property
    def IsCrossLink(self) -> bool:
        return self._URL.strip().startswith("../")

    # For a cross-link, return (owningSeriesName, conName); otherwise None.
    def CrossLinkTarget(self) -> tuple[str, str] | None:
        u=unquote(self._URL.strip())
        if not u.startswith("../"):
            return None
        parts=[p for p in u[len("../"):].split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None

    # What the read-only "Extras" grid cell shows: bare "SpecialText Notes", capped at 20 characters.
    @property
    def ExtrasDisplay(self) -> str:
        s=f"{self._specialText} {self._notes}".strip()
        return s if len(s) <= 20 else s[:17]+"..."

    # Get or set a value by name or column number.
    # Grid columns are now: 0=Display Name, 1=Extras (display-only), 2=Dates, 3=Locale, 4=GoHs.
    # URL / Extra / SpecialText / Notes remain accessible by name (they are not their own columns).
    def __getitem__(self, index: str|int) -> str|int|FanzineDateRange:
        if index == "Name" or index == "Display Name" or index == 0:
            return self.Name
        if index == "Extras" or index == 1:
            return self.ExtrasDisplay
        if index == "Dates" or index == 2:
            return self.Dates
        if index == "Locale" or index == 3:
            return self.Locale
        if index == "GoHs" or index == 4:
            return self.GoHs
        if index == "URL":
            return self.URL
        if index == "Extra":
            return self.Extra
        if index == "SpecialText":
            return self.SpecialText
        if index == "Notes":
            return self.Notes
        if index != 5:  # 5 is the normal terminator of an iteration through the 5 columns
            Log(f"Con(GridDataRowClass).__getitem__({index}) does not exist")
        raise IndexError


    def __setitem__(self, index: str|int, value: str|int|FanzineDateRange) -> None:
        if index == "Name" or index == "Display Name" or index == 0:
            self.Name=value
            return
        if index == "Extras" or index == 1:
            return      # display-only column; the Extras dialog edits SpecialText/Notes directly
        if index == "Dates" or index == 2:
            if isinstance(value, FanzineDateRange):
                self.Dates=FanzineDateRange()
                self.Dates.Copy(value)
                return
            self.Dates=FanzineDateRange().Match(value)
            return
        if index == "Locale" or index == 3:
            self.Locale=value
            return
        if index == "GoHs" or index == 4:
            self.GoHs=value
            return
        if index == "URL":
            self.URL=value
            return
        if index == "Extra":
            self.Extra=value
            return
        if index == "SpecialText":
            self.SpecialText=value
            return
        if index == "Notes":
            self.Notes=value
            return
        Log(f"Con(GridDataRowClass).__putitem__('{index}') does not exist")
        raise IndexError


    @property
    def IsEmptyRow(self) -> bool:        
        return (self._name == "" and self._link == "" and self._specialText == "" and self._notes == "" and
                self._locale == "" and (self._dates is None or self._dates.IsEmpty()) and
                self._gohs == "" and self._URL == "")


####################################################################################
class ConSeries(GridDataSource):

    def __init__(self):
        GridDataSource.__init__(self)
        self._colDefs: ColDefinitionsList=ColDefinitionsList([
            ColDefinition("Display Name", Type="text", Width=30, IsEditable=IsEditable.Yes),   # editable when unlinked; locked when linked (via OnGridEditorShown)
            ColDefinition("Extras", Type="text", Width=30, IsEditable=IsEditable.No),   # display-only; edited via the Extras dialog
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

    def __hash__(self) -> int:
        return hash(self._name)+sum([x.Signature()*(i+1) for i, x in enumerate(self.Rows)])
    def Signature(self) -> int:
        return self.__hash__()

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
        self.Rows=self.Rows[:index]+[Con() for i in range(num)]+self.Rows[index:]   # Insert num empty Con() objects

