from __future__ import annotations
from typing import Optional

import ftplib
import json
import io

from HelpersPackage import Log


class FTP:
    g_ftp: FTP=None      # A single FTP link for all instances of the class
    _localroot: str=""
    _siteroot: str=""
    _cwd: str=""


    def OpenConnection(self, cre: str) -> bool:
        with open(cre) as f:
            d=json.loads(f.read())
        FTP.g_ftp=ftplib.FTP(host=d["host"], user=d["ID"], passwd=d["PW"])


    def SetRoots(self, local="", site=""):
        FTP._localroot=local
        FTP._siteroot=site


    #-------------------------------
    def SetDirectory(self, newdir: str) -> None:
        Log("SetDirectory: "+newdir)
        Log("pwd(): "+FTP.g_ftp.pwd())
        if FTP.g_ftp.pwd()+"/"+newdir == FTP._cwd:
            Log("no set directory needed")
            return  # No cwd needed

        # Does the directory exist?
        if newdir not in FTP.g_ftp.nlst():
            # If not, create it.
            Log("mkd: "+newdir)
            Log(FTP.g_ftp.mkd(newdir))

        # Now cwd to it.
        Log("cwd() -> "+FTP.g_ftp.pwd())
        Log(FTP.g_ftp.cwd(newdir))
        Log("pwd(): "+FTP.g_ftp.pwd())

        FTP._cwd=FTP.g_ftp.pwd()


    #-------------------------------
    # Move a string to the Conventions FTP site or get a string from it
    # We map the local directory  ./Convention publications  to fanac.org/Cons
    # These two functions rely on the global g_ftp being defined and open
    def PutFTPAF(self, fname: str) -> bool:
        if FTP.g_ftp is None:
            return False

        localfname=FTP._localroot+"/"+fname
        Log("STOR "+fname+"  from "+localfname)
        with open(localfname, "rb") as f:
            Log(FTP.g_ftp.storbinary("STOR "+fname, f))


    def GetFTPA(self, fname: str) -> Optional[str]:
        if FTP.g_ftp is None:
            return None

        global out
        out=""
        def my_function(data):
            global out
            out+=data
        status=FTP.g_ftp.retrlines('RETR '+fname, callback=my_function)
        Log('RETR '+fname+" -> "+status)
        Log(out)
        return out


