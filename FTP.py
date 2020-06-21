from __future__ import annotations
from typing import Optional, Dict

import ftplib
import json
import os

from Log import Log, LogFlush


class FTP:
    g_ftp: FTP=None      # A single FTP link for all instances of the class
    g_curdirpath: str="/"
    g_credentials: Dict={}      # Saves the credentials for reconnection if the server times out

    # ---------------------------------------------
    def OpenConnection(self, cre: str) -> bool:
        with open(cre) as f:
            FTP.g_credentials=json.loads(f.read())
        return self.Reconnect()

    # ---------------------------------------------
    def Reconnect(self) -> bool:
        if len(FTP.g_credentials) == 0:
            return False
        FTP.g_ftp=ftplib.FTP(host=FTP.g_credentials["host"], user=FTP.g_credentials["ID"], passwd=FTP.g_credentials["PW"])
        # Now we need to restore the current working directory
        predir=FTP.g_curdirpath
        FTP().SetDirectory("/")
        if not FTP().SetDirectory(predir):
            Log("Reconnect failed")
            return False
        return True

    # ---------------------------------------------
    # Update the saved current working directory path
    # If the input is an absolute path, just use if (removing any trailing filename)
    # If it's a relative move, compute the new wd path
    def UpdateCurpath(self, newdir: str) -> None:
        if newdir[0] == "/":    # Absolute directory move
            FTP.g_curdirpath=newdir
        elif newdir == "..":    # Relative move up one directory
            #TODO: Note that we don't handle things like "../.." yet
            if FTP.g_curdirpath != "/":     # If we're already at the top, we stay put.
                head, _=os.path.split(self.g_curdirpath)    # But we're not, so we slice off the last directory in the saved wd path
                FTP.g_curdirpath=head
        else:
            # What's left is a CD downwards
            if FTP.g_curdirpath == "/":
                FTP.g_curdirpath+=newdir
            else:
                FTP.g_curdirpath+="/"+newdir


    #---------------------------------------------
    def CWD(self, newdir: str) -> bool:
        wd=self.PWD()
        Log("**cwd from '"+wd+"' to '"+newdir+"'")
        if wd == newdir:
            Log("  Already there!")
            return True

        try:
            msg=self.g_ftp.cwd(newdir)
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            msg=self.g_ftp.cwd(newdir)

        Log(msg)
        ret=msg.startswith("250 OK.")
        if ret:
            self.UpdateCurpath(newdir)
        self.PWD()
        return ret

    # ---------------------------------------------
    def MKD(self, newdir: str) -> bool:
        Log("**make directory: '"+newdir+"'")
        try:
            msg=self.g_ftp.mkd(newdir)
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            msg=self.g_ftp.mkd(newdir)
        Log(msg+"\n")
        return msg == newdir or msg.startswith("250 ") or msg.startswith("257 ")     # Web doc shows all three as possible.

    # ---------------------------------------------
    def DeleteFile(self, fname: str) -> bool:
        Log("**delete file: '"+fname+"'")
        if len(fname.strip()) == 0:
            Log("FTP.DeleteFile: filename not supplied.")
            LogFlush()
            assert False

        if not self.Exists(fname):
            Log("FTP.DeleteFile: '"+fname+"' does not exist.")
            return True

        try:
            msg=self.g_ftp.delete(fname)
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            msg=self.g_ftp.delete(fname)
        Log(msg+"\n")
        return msg.startswith("250 ")

    # ---------------------------------------------
    def Rename(self, oldname: str, newname: str) -> bool:
        Log("**rename file: '"+oldname+"'  as  '"+newname+"'")
        if len(oldname.strip()) == 0 or len(newname.strip()) == 0:
            Log("FTP.Rename: oldname or newname not supplied.")
            LogFlush()
            assert False

        if not self.Exists(oldname):
            Log("FTP.Rename: '"+oldname+"' does not exist.")
            return False

        try:
            msg=self.g_ftp.rename(oldname, newname)
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            msg=self.g_ftp.rename(oldname, newname)
        Log(msg+"\n")
        return msg.startswith("250 ")

    # ---------------------------------------------
    def DeleteDir(self, dirname: str) -> bool:
        Log("**delete directory: '"+dirname+"'")
        if len(dirname.strip()) == 0:
            Log("FTP.DeleteDir: dirname not supplied.")
            LogFlush()
            assert False
        if dirname == "/":
            Log("FTP.DeleteDir: Attempt to delete root -- forbidden")
            assert False

        if not self.Exists(dirname):
            Log("FTP.DeleteDir: '"+dirname+"' does not exist.")
            return True

#TODO: Do not recursively delete, but do note to user when subdirectories exists
        try:
            msg=self.g_ftp.rmd(dirname)
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            msg=self.g_ftp.rmd(dirname)
        Log(msg+"\n")
        return msg.startswith("250 ")

    # ---------------------------------------------
    def PWD(self) -> str:
        try:
            dir=self.g_ftp.pwd()
        except Exception as e:
            Log("FTP connection failure. Exception="+str(e))
            if not self.Reconnect():
                return False
            dir=self.g_ftp.pwd()
        Log("pwd is '"+dir+"'")

        # Check to see if this matches what self._curdirpath thinks it ought to
        _, tail=os.path.split(self.g_curdirpath)
        if self.g_curdirpath != dir and tail != dir:
            Log("PWD: error detected -- self._curdirpath='"+self.g_curdirpath+"' and pwd returns '"+dir+"'")
            assert False
        return dir

    # ---------------------------------------------
    def Exists(self, filedir: str) -> bool:
        Log("Does '"+filedir+"' exist?")
        if filedir == "/":
            return True     # "/" always exists
        try:
            if filedir in self.g_ftp.nlst():
                Log("'"+filedir+"' exists")
                return True
            Log("'"+filedir+"' does not exist")
            return False
        except:
            if not self.Reconnect():
                return False
            return self.Exists(str)


    #-------------------------------
    # Setting create=True allows the creation of new directories as needed
    # Newdir can be a whole path starting with "/" or a path relative to the current directory if it doesn't starts with a "/"
    def SetDirectory(self, newdir: str, create: bool=False) -> bool:
        Log("**SetDirectory: "+newdir)

        # Split newdir into components
        if newdir is None or len(newdir) == 0:
            return True

        components=[]
        if newdir[0] == "/":
            components.append("/")
            newdir=newdir[1:]
        components.extend(newdir.split("/"))
        components=[c.strip() for c in components if len(c) > 0]

        # Now walk the component list
        for component in components:
            # Does the directory exist?
            if not self.Exists(component):
                # If not, are we allowed to create it"
                if not create:
                    Log("SetDirectory was called for a non-existant directory with create=False")
                    return False
                if not self.MKD(component):
                    Log("mkd failed...bailing out...")
                    return False

            # Now cwd to it.
            if not self.CWD(component):
                Log("cwd failed...bailing out...")
                return False

        return True


    #-------------------------------
    # Copy the local file fname to fanac.org in the current directory and with the same name
    def PutString(self, fname: str, s: str) -> bool:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return False

        if not os.path.exists("temp") or not os.path.isdir("temp"):     # If necessary, create the temp directory
            os.mkdir("temp")
        localfname="temp/"+fname

        # Save the string as a local file
        with open(localfname, "w+") as f:
            f.write(s)

        Log("STOR "+fname+"  from "+localfname)
        with open(localfname, "rb") as f:
            try:
                Log(self.g_ftp.storbinary("STOR "+fname, f))
            except Exception as e:
                Log("FTP connection failure. Exception="+str(e))
                if not self.Reconnect():
                    return False
                Log(self.g_ftp.storbinary("STOR "+fname, f))
        return True


    #-------------------------------
    def PutFileAsString(self, directory: str, fname: str, s: str, create: bool=False) -> bool:
        if not FTP().SetDirectory(directory, create=create):
            Log("PutFieAsString: Bailing out...")
            return False
        return FTP().PutString(fname, s)


    #-------------------------------
    # Copy the local file fname to fanac.org in the current directory and with the same name
    def PutFile(self, pathname: str, toname: str) -> bool:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return False

        Log("STOR "+toname+"  from "+pathname)
        try:
            with open(pathname, "rb") as f:
                try:
                    Log(self.g_ftp.storbinary("STOR "+toname, f))
                except Exception as e:
                    Log("FTP connection failure. Exception="+str(e))
                    if not self.Reconnect():
                        return False
                    Log(self.g_ftp.storbinary("STOR "+toname, f))
        except Exception as e:
            Log("FTP.PutFile: Exception on Open("+pathname+" 'rb') ")
            Log(str(e))
        return True


    #-------------------------------
    # Download the ascii file named fname in the current directory on fanac.org into a string
    def GetAsString(self, fname: str) -> Optional[str]:
        if self.g_ftp is None:
            Log("FTP not initialized")
            return None

        if not os.path.exists("temp") or not os.path.isdir("temp"):
            os.mkdir("temp")

        localfname="temp/"+fname
        Log("RETR "+fname+"  to "+localfname)
        if not self.Exists(fname):
            Log(fname+" does not exist.")
            return None
        with open(localfname, "wb+") as f:
            try:
                msg=self.g_ftp.retrbinary("RETR "+fname, f.write)
            except Exception as e:
                Log("FTP connection failure. Exception="+str(e))
                if not self.Reconnect():
                    return None
                msg=self.g_ftp.retrbinary("RETR "+fname, f.write)
            Log(msg)
            if not msg.startswith("226-File successfully transferred"):
                Log("GetAsString failed")
                return None

        with open(localfname, "r") as f:
            out=f.readlines()
        out="/n".join(out)
        return out


    #-------------------------------
    def GetFileAsString(self, directory: str, fname: str) -> Optional[str]:
        if not self.SetDirectory(directory):
            Log("GetFileAsString: Bailing out...")
            return None
        s=FTP().GetAsString(fname)
        if s is None:
            Log("Could not load "+directory+"/"+fname)
        return s