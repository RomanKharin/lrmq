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
import struct
import traceback
import logging

from .agent import AgentSystem, agent_factory

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
        self.logger = logging.getLogger("<hub>")

        # current agent list
        self.sysagent = AgentSystem(self)
        self.pending_agents = [self.sysagent]
        self.working_agents = []
        self.stopped_agents = []
        self.id_cnt = 0 # numerate objects
        self.exit_code = 0

        self.main_s = None
        self.is_active = True

    def load_config(self, cfg):
        self.cfg = cfg
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
        self.logger.debug("=" * 25)

        loadmode = cfg.get("load_mode", "config")
        self.logger.debug("Load mode: " + str(loadmode))
        if loadmode == "config_folder":
            base = os.path.abspath(cfg.get("agents"))
            self.logger.debug("Load agents config files from: " + str(base))
            for item in os.listdir(base):
                self.logger.debug("Load agent: " + str(item))
                if item.startswith("agent-") and item.endswith(".json"):
                    a = agent_factory(self, os.path.join(base, item))
                    self.pending_agents.append(a)
        elif loadmode == "config":
            a = cfg.get("agents", [])
            self.logger.debug("Agents in config: " + str(len(a)))
            for acfg in a:
                self.logger.debug("Load agent: " + str(acfg))
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
        self.logger.info("Start hub")
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
            self.logger.debug("Done loop done=" + str(len(done)) + \
                " pending=" + str(len(pending)))
            pending = list(pending)
            if self.main_s.done():
                # signal received
                self.main_s = self.loop.create_future()
                pending = pending + [self.main_s]
            # check if new agents
            cnt, pending = process_agents(pending)
            if cnt <= 1: break
        self.logger.info("Finish")
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

        for mask, subid in self.subsmasks:
            try:
                if mask.match(name):
                    nopts = {}
                    if opts:
                        nopts.update(opts)
                    nopts["subid"] = subid
                    self.subs[subid].push_msg(name, msg, opts)
            except Exception as e:
                traceback.print_exc()
        self.logger.debug("Message " + str(name) + " " + str(msg))

    def push_pulse(self):
        "Push broadcast pulse message"

        for a in self.working_agents:
            a.push_msg("*/pulse", opts = {"ttl": 30})

    def removed_msg(self, name, msg, opts):
        # TODO: send events
        pass

