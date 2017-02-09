import unittest

import os
import sys
import inspect
import re

import lrmq

class TestSource(unittest.TestCase):

    def test_logs_enum(self):
        vals = set()
        logtypes = {}
        # call all messages
        for ltname, _ in inspect.getmembers(lrmq.logs.LogTypes):
            if ltname.startswith(("AGENT_", "HUB_", "MARK")):
                lt = getattr(lrmq.logs.LogTypes, ltname)
                logtypes[ltname] = lt
                print(ltname, "=", lrmq.logs.LogTypes.get(lt))

        # detect id without message
        for ltname, lt in logtypes.items():
            self.assertIn(lt, lrmq.logs.LogTypes.text, 
                "Message for %s (%d) not found" % (ltname, lt))

        loggers = ("debug", "info", "warning", "error", "critical")
        ptrn = re.compile("LogTypes\.(?P<name>.*?)[,\)]")
        def scan_file(fn, lineno):
            with open(fn, "r") as f:
                # lineno - from 1, we use
                lines = [line.rstrip() for line in f.readlines()][lineno:]
                # skip empty
                while True:
                    if len(lines) > 0:
                        if lines[0] == "":
                            lines = lines[1:]
                            lineno += 1
                        else:
                            break
                    else:
                        break
                # search self.logger.{facility}
                if len(lines) > 0:
                    intend = 0
                    for ch in lines[0]:
                        if ch != " ": break
                        intend += 1
                    idx = 0
                    while idx < len(lines):
                        line = lines[idx]
                        idx += 1
                        if line[:intend] != lines[0][:intend]: 
                            if line != "": break
                            continue
                        #print("F", line)
                        pos = line.find("self.logger.")
                        if pos < 0: continue
                        cl = line[pos + 12:]
                        if not cl.startswith(loggers): 
                            continue
                        pos = cl.find("(")
                        if pos < 0: continue
                        cl = cl[pos + 1:]
                        m = ptrn.match(cl)
                        if m:
                            self.assertIn(m.group("name"), logtypes)
                        elif False:
                            raise Exception(
                                "Logging not formatted %s:%d, %s" % (
                                (fn, lineno + idx, line.strip())))
                        else:
                            print("Logging not formatted %s:%d, %s" % (
                                (fn, lineno + idx, line.strip())))

                    #print(lines[:10])
                
        # scan source for loggers without id
        done = set()
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        def scan_all(obj, indend = ""):
            if not inspect.isclass(obj) and not inspect.ismodule(obj):
                return []
            if obj in done: return []
            done.add(obj)
            #print(indend, "Scan ", obj)
            items = []
            for sname, tp in inspect.getmembers(obj):
                if sname[:2] == sname[-2:] == "__":
                    continue
                try:
                    sobj = getattr(obj, sname)
                except:
                    continue
                if inspect.isclass(sobj):
                    items += scan_all(sobj, indend = indend + "  ")
                elif inspect.isfunction(sobj):
                    if sobj.__code__.co_filename.startswith(base):
                        scan_file(sobj.__code__.co_filename, 
                            sobj.__code__.co_firstlineno)
            return items
            
        items = scan_all(lrmq.agent) + scan_all(lrmq.hub)
            

if __name__ == '__main__':
    unittest.main()
