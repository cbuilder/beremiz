#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import Pyro.core as pyro
from threading import Timer
import ctypes, os, commands

if os.name in ("nt", "ce"):
    from _ctypes import LoadLibrary as dlopen
    from _ctypes import FreeLibrary as dlclose
elif os.name == "posix":
    from _ctypes import dlopen, dlclose

import os,sys,traceback

lib_ext ={
     "linux2":".so",
     "win32":".dll",
     }.get(sys.platform, "")

class PLCObject(pyro.ObjBase):
    _Idxs = []
    def __init__(self, workingdir, daemon, argv):
        pyro.ObjBase.__init__(self)
        self.argv = [workingdir] + argv # force argv[0] to be "path" to exec...
        self.workingdir = workingdir
        self.PLCStatus = "Stopped"
        self.PLClibraryHandle = None
        # Creates fake C funcs proxies
        self._FreePLC()
        self.daemon = daemon
        
        # Get the last transfered PLC if connector must be restart
        try:
            self.CurrentPLCFilename=open(
                             self._GetMD5FileName(),
                             "r").read().strip() + lib_ext
        except Exception, e:
            self.PLCStatus = "Empty"
            self.CurrentPLCFilename=None

    def _GetMD5FileName(self):
        return os.path.join(self.workingdir, "lasttransferedPLC.md5")

    def _GetLibFileName(self):
        return os.path.join(self.workingdir,self.CurrentPLCFilename)


    def _LoadNewPLC(self):
        """
        Load PLC library
        Declare all functions, arguments and return values
        """
        print "Load PLC"
        try:
            self._PLClibraryHandle = dlopen(self._GetLibFileName())
            self.PLClibraryHandle = ctypes.CDLL(self.CurrentPLCFilename, handle=self._PLClibraryHandle)
    
            self._startPLC = self.PLClibraryHandle.startPLC
            self._startPLC.restype = ctypes.c_int
            self._startPLC.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
            
            self._stopPLC = self.PLClibraryHandle.stopPLC
            self._stopPLC.restype = None
    
            self._ResetDebugVariables = self.PLClibraryHandle.ResetDebugVariables
            self._ResetDebugVariables.restype = None
    
            self._RegisterDebugVariable = self.PLClibraryHandle.RegisterDebugVariable
            self._RegisterDebugVariable.restype = None
            self._RegisterDebugVariable.argtypes = [ctypes.c_int]
    
            self._IterDebugData = self.PLClibraryHandle.IterDebugData
            self._IterDebugData.restype = ctypes.c_void_p
            self._IterDebugData.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_char_p)]
    
            self._FreeDebugData = self.PLClibraryHandle.FreeDebugData
            self._FreeDebugData.restype = None
            
            self._WaitDebugData = self.PLClibraryHandle.WaitDebugData
            self._WaitDebugData.restype = ctypes.c_int  

            self._suspendDebug = self.PLClibraryHandle.suspendDebug
            self._suspendDebug.restype = None

            self._resumeDebug = self.PLClibraryHandle.resumeDebug
            self._resumeDebug.restype = None
            
            return True
        except:
            print traceback.format_exc()
            return False

    def _FreePLC(self):
        """
        Unload PLC library.
        This is also called by __init__ to create dummy C func proxies
        """
        # Forget all refs to library
        self._startPLC = lambda:None
        self._stopPLC = lambda:None
        self._ResetDebugVariables = lambda:None
        self._RegisterDebugVariable = lambda x:None
        self._IterDebugData = lambda x,y:None
        self._FreeDebugData = lambda:None
        self._WaitDebugData = lambda:-1
        self._suspendDebug = lambda:None
        self._resumeDebug = lambda:None
        self.PLClibraryHandle = None
        # Unload library explicitely
        if getattr(self,"_PLClibraryHandle",None) is not None:
            print "Unload PLC"
            dlclose(self._PLClibraryHandle)
            res = self._DetectDirtyLibs()
        else:
            res = False

        self._PLClibraryHandle = None

        return res

    def _DetectDirtyLibs(self):
        # Detect dirty libs
        # Get lib dependencies (for dirty lib detection)
        if os.name == "posix":
            # parasiting libs listed with ldd
            badlibs = [ toks.split()[0] for toks in commands.getoutput(
                            "ldd "+self._GetLibFileName()).splitlines() ]
            for badlib in badlibs:
                if badlib[:6] in ["libwx_",
                                  "libwxs",
                                  "libgtk",
                                  "libgdk",
                                  "libatk",
                                  "libpan",
                                  "libX11",
                                  ]:
                    #badhandle = dlopen(badlib, dl.RTLD_NOLOAD)
                    print "Dirty lib detected :" + badlib
                    #dlclose(badhandle)
                    return True
        return False

    
    def StartPLC(self, debug=False):
        print "StartPLC"
        if self.CurrentPLCFilename is not None and self.PLCStatus == "Stopped":
            c_argv = ctypes.c_char_p * len(self.argv)
            if self._LoadNewPLC() and self._startPLC(len(self.argv),c_argv(*self.argv)) == 0:
                if debug:
                    self._resumeDebug()
                self.PLCStatus = "Started"
                return True
            else:
                print "_StartPLC did not return 0 !"
                self._DoStopPLC()
        return False

    def _DoStopPLC(self):
        self._stopPLC()
        self.PLCStatus = "Stopped"
        if self._FreePLC():
            self.PLCStatus = "Dirty"
        return True

    def StopPLC(self):
        if self.PLCStatus == "Started":
            self._DoStopPLC()
            return True
        return False

    def _Reload(self):
        self.daemon.shutdown(True)
        self.daemon.sock.close()
        os.execv(sys.executable,[sys.executable]+sys.argv[:])
        # never reached
        return 0

    def ForceReload(self):
        # respawn python interpreter
        Timer(0.1,self._Reload).start()
        return True

    def GetPLCstatus(self):
        return self.PLCStatus
    
    def NewPLC(self, md5sum, data, extrafiles):
        print "NewPLC (%s)"%md5sum
        if self.PLCStatus in ["Stopped", "Empty", "Dirty"]:
            NewFileName = md5sum + lib_ext
            extra_files_log = os.path.join(self.workingdir,"extra_files.txt")
            try:
                os.remove(os.path.join(self.workingdir,
                                       self.CurrentPLCFilename))
                for filename in file(extra_files_log, "r").readlines() + extra_files_log:
                    try:
                        os.remove(os.path.join(self.workingdir, filename))
                    except:
                        pass
            except:
                pass
                        
            try:
                # Create new PLC file
                open(os.path.join(self.workingdir,NewFileName),
                     'wb').write(data)
        
                # Store new PLC filename based on md5 key
                open(self._GetMD5FileName(), "w").write(md5sum)
        
                # Then write the files
                log = file(extra_files_log, "w")
                for fname,fdata in extrafiles:
                    fpath = os.path.join(self.workingdir,fname)
                    open(fpath, "wb").write(fdata)
                    log.write(fname+'\n')

                # Store new PLC filename
                self.CurrentPLCFilename = NewFileName
            except:
                print traceback.format_exc()
                return False
            if self.PLCStatus == "Empty":
                self.PLCStatus = "Stopped"
            return True
        return False

    def MatchMD5(self, MD5):
        try:
            last_md5 = open(self._GetMD5FileName(), "r").read()
            return last_md5 == MD5
        except:
            return False
    
    def SetTraceVariablesList(self, idxs):
        """
        Call ctype imported function to append 
        these indexes to registred variables in PLC debugger
        """
        self._suspendDebug()
        # keep a copy of requested idx
        self._Idxs = idxs[:]
        self._ResetDebugVariables()
        for idx in idxs:
            self._RegisterDebugVariable(idx)
        self._resumeDebug()
    
    TypeTranslator = {"BOOL" :       ctypes.c_uint8,
                      "STEP" :       ctypes.c_uint8,
                      "TRANSITION" : ctypes.c_uint8,
                      "ACTION" :     ctypes.c_uint8,
                      "SINT" :       ctypes.c_int8,
                      "USINT" :      ctypes.c_uint8,
                      "BYTE" :       ctypes.c_uint8,
                      "STRING" :     None, #TODO
                      "INT" :        ctypes.c_int16,
                      "UINT" :       ctypes.c_uint16,
                      "WORD" :       ctypes.c_uint16,
                      "WSTRING" :    None, #TODO
                      "DINT" :       ctypes.c_int32,
                      "UDINT" :      ctypes.c_uint32,
                      "DWORD" :      ctypes.c_uint32,
                      "LINT" :       ctypes.c_int64,
                      "ULINT" :      ctypes.c_uint64,
                      "LWORD" :      ctypes.c_uint64,
                      "REAL" :       ctypes.c_float,
                      "LREAL" :      ctypes.c_double,
                      } 
                           
    def GetTraceVariables(self):
        """
        Return a list of variables, corresponding to the list of requiered idx
        """
        tick = self._WaitDebugData()
        if tick == -1:
            return -1,None
        idx = ctypes.c_int()
        typename = ctypes.c_char_p()
        res = []

        for given_idx in self._Idxs:
            buffer=self._IterDebugData(ctypes.byref(idx), ctypes.byref(typename))
            c_type = self.TypeTranslator.get(typename.value, None)
            if c_type is not None and given_idx == idx.value:
                res.append(ctypes.cast(buffer, 
                                       ctypes.POINTER(c_type)).contents.value)
            else:
                print "Debug error idx : %d, expected_idx %d, type : %s"%(idx.value, given_idx,typename.value)
                res.append(None)
        self._FreeDebugData()
        return tick, res
        

