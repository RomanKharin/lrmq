# -*- coding: utf8 -*-

# Low-resource message queue framework
# Message hub
# Copyright (c) 2016 Roman Kharin <romiq.kh@gmail.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import re
import asyncio
import time
import json
import pickle
import struct
import traceback
import logging
import datetime

from .agent import AgentSystem, agent_factory
from .logs import LogTypes, LogTypesFilter

# Agent work scheme:
#  propose protocols line
#  agent select one
#  request-answer, agent make request, we answer
#  if event subscription requested it uses long polling
#    in case of cancel event subscription cancel message emitted

class Hub:
    "Processing hub"

    def __init__(self):
        # subscribers
        self.subs = {}
        self.subsmasks = []
        self.subscnt = 0
        self.loop = asyncio.get_event_loop()
        self.log_formatter = \
            logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        self.log_filter = LogTypesFilter()
        self.logger = logging.getLogger("<hub>")
        self.logger.addFilter(self.log_filter)
        self.log_handlers = set()

        # current agent list
        self.sysagent = AgentSystem(self)
        self.pending_agents = [self.sysagent]
        self.working_agents = []
        self.stopped_agents = []
        self.id_cnt = 0 # numerate objects
        self.exit_code = 0
        self.clean_cnt = 0
        
        # checks
        self.call_wait = {}

        self.main_s = None
        self.is_active = True

    def load_config(self, cfg):
        self.cfg = cfg
        # debug logger
        if __debug__:
            debuglogger = self.cfg.get("debuglogger", "INFO")
            if debuglogger:
                rootlogger = logging.getLogger("")
                self.debughandler = DebugLoggerHandler(filename = debuglogger, 
                    mode = "wb")
                self.debughandler.setLevel(logging.DEBUG)
                rootlogger.addHandler(self.debughandler)
                self.log_handlers.add((rootlogger, self.debughandler))
        
        loglevel = self.cfg.get("loglevel", "INFO")
        self.logger.setLevel(loglevel)
        logfn = self.cfg.get("log")
        if logfn:
            hdlr = logging.FileHandler(logfn)
        else:
            hdlr = logging.StreamHandler(sys.stdout)
        if hdlr:
            hdlr.setFormatter(self.log_formatter)
            self.logger.addHandler(hdlr)
            self.log_handlers.add((self.logger, hdlr))

        self.logger.debug(LogTypes.MARK)
        loadmode = cfg.get("load_mode", "config")
        self.logger.debug(LogTypes.HUB_LOAD_MODE, loadmode)
        if loadmode == "config_folder":
            base = os.path.abspath(cfg.get("agents"))
            self.logger.debug(LogTypes.HUB_LOAD_AGENTS, base)
            for item in os.listdir(base):
                self.logger.debug(LogTypes.HUB_LOAD_AGENT, item)
                if item.startswith("agent-") and item.endswith(".json"):
                    a = agent_factory(self, os.path.join(base, item))
                    self.pending_agents.append(a)
        elif loadmode == "config":
            a = cfg.get("agents", [])
            self.logger.debug(LogTypes.HUB_AGENT_COUNT, len(a))
            for acfg in a:
                self.logger.debug(LogTypes.HUB_LOAD_AGENT, str(acfg))
                a = agent_factory(self, acfg)
                self.pending_agents.append(a)

    def genid(self, prefix):
        oid = self.id_cnt
        self.id_cnt += 1
        return "%s%d" % (prefix, oid)

    def subscribe(self, mask, subscriber):
        "Subscribe to message by mask"

        subid = self.subscnt
        self.subscnt += 1
        self.subs[subid] = subscriber
        self.subsmasks.append((mask, subid))
        return subid

    def unsubscribe(self, subid):
        "Unsubscribe by subid"

        oldsubid = subid
        self.subsmasks = [(mask, subid) for (mask, subid) in self.subsmasks
            if subid != oldsubid]
        del self.subs[oldsubid]

    async def main_loop(self):
        self.logger.info(LogTypes.HUB_START)
        self.main_s = self.loop.create_future()
        pending = [self.main_s]
        def process_agents(pending):
            pending += [a.run() for a in self.pending_agents]
            self.working_agents += self.pending_agents
            self.pending_agents = []
            cnt = 0
            for a in self.working_agents:
                if not a.isloop:
                    self.working_agents.remove(a)
                    self.stopped_agents.append(a)
            for a in pending:
                if a is not self.main_s:
                    cnt += 1
            return cnt, pending
        if len(self.pending_agents) > 1:
            cnt, pending = process_agents(pending)
        else:
            cnt = 0
            pending = []
        while pending:
            done, pending = await asyncio.wait(
                pending, timeout = 3,
                return_when = asyncio.FIRST_COMPLETED)
            # check reason
            self.logger.info(LogTypes.HUB_LOOP_END, len(done), len(pending))
            pending = list(pending)
            if self.main_s.done():
                # signal received
                self.main_s = self.loop.create_future()
                pending = pending + [self.main_s]
            # check if new agents
            cnt, pending = process_agents(pending)
            if cnt <= 1: break
        self.logger.info(LogTypes.HUB_FINISH)
        # cleanup
        self.sysagent.isloop = False
        self.sysagent.signal()
        self.signal()
        await asyncio.wait(pending + [self.main_s])

    def signal(self):
        if self.main_s:
            self.main_s.set_result(True)

    def push_msg(self, name, msg = None, opts = None):
        "Push message to all queues"

        # check variants
        check = opts.get("check") if opts else None
        if check:
            assert isinstance(check, str), "Check must be string or None"

        self.logger.debug(LogTypes.HUB_MESSAGE, name, str(msg), str(opts),
            extra = {"msg_name": name, "msg_msg": msg, "msg_opts": opts})

        msg_processed = False
        msg_rpc = False
        for mask, subid in self.subsmasks:
            try:
                if mask.match(name):
                    nopts = {} if not opts else {k: v for k, v in opts.items()}
                    nopts["subid"] = subid
                    self.subs[subid].push_msg(name, msg, nopts)
                    msg_processed = True
                    if self.subs[subid].isrpc:
                        msg_rpc = True
            except Exception as e:
                traceback.print_exc()

        if check == "call":
            opts = opts or {}
            sender = opts.get("from")
            if not sender:
                raise Exception("Sender must be specified")
            reqid = opts.get("reqid")
            # call or return
            if name.endswith("/call"):
                if not msg_rpc:
                    raise Exception("RPC server not found")
                # start tracing by (caller, reqid) pair
                self.call_wait[(sender, reqid)] = \
                    (sender, reqid, name[:-5], datetime.datetime.now())
            elif name.endswith("/ret"):
                waiter = self.call_wait.pop((sender, reqid), None)
                if waiter is None:
                    # TODO: send events
                    self.logger.debug(LogTypes.HUB_MESSAGE_NORET, name)
            else:
                # TODO: send events
                self.logger.debug(LogTypes.HUB_MESSAGE_BADCALL, name)
        else:
            if msg_processed:
                # TODO: send events
                self.logger.debug(LogTypes.AGENT_MSG_UNPROCESSED, name, 
                    str(msg), str(opts))
                
        
    def push_pulse(self):
        "Push broadcast pulse message. Update internal structures"

        # send alive notifications
        for a in self.working_agents:
            a.push_msg("*/pulse", opts = {"ttl": 30})

        # cleanup old messages from queues
        self.clean_cnt += 1
        if self.clean_cnt >= 12:
            self.clean_cnt = 0
            for a in self.working_agents:
                a.check_msg_expiration()

    def removed_msg(self, a, name, msg, opts):
        self.logger.debug(LogTypes.HUB_MESSAGE_REMOVED, name, 
            str(msg), str(opts))
        if name != "*/pulse" and not name.starts_with("system/msg_lost/"):
            self.push_msg("system/msg_lost/" + a.name, {"name": name,
                "msg": msg, "opts": opts, "agentid": a.getid()})

    def cleanup(self):
        # free used resources
        for logger, hdlr in self.log_handlers:
            try:
                hdlr.flush()
                hdlr.close()
                logger.removeHandler(hdlr)
            except:
                traceback.print_exc()

class DebugLoggerHandler(logging.FileHandler):
    "Special debug logger"

    def emit(self, record):
        if self.stream is None:
            self.stream = self._open()
        fields = ("name", "asctime", "created", "levelname", "msg", 
            "log_id", "args")
        try:
            data = {k: getattr(record, k) 
                for k in fields if hasattr(record, k)}
            if record.exc_info:
                data["exc_info"] = repr(record.exc_info)
            s = pickle.dumps(data)
            slen = struct.pack(">L", len(s))
            self.stream.write(slen + s)
        except Exception:
            self.handleError(record)

    
    

