# -*- coding: utf8 -*-

# Low-resource message queue framework
# Log helpers and types
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

import logging

class LogTypesFilter(logging.Filter):
    "Filter translate id to text representation"

    def filter(self, record):
        try:
            value = record.msg
            record.msg = LogTypes.text[value]
            record.log_id = value
        except Exception as e:
            pass
        return True
        
class LogTypes():
    MARK = 10

    # hub 100 - 1000
    HUB_LOAD_MODE = 100
    HUB_START = 101
    HUB_FINISH = 102
    HUB_LOAD_AGENTS = 103
    HUB_LOAD_AGENT = 104
    HUB_AGENT_COUNT = 105
    HUB_LOOP_END = 106

    HUB_SET_EXIT_CODE = 125

    HUB_MESSAGE = 150
    HUB_MESSAGE_NORET = 151
    HUB_MESSAGE_BADCALL = 152
    HUB_MESSAGE_REMOVED = 153
    
    # agent 1000 -
    AGENT_PREPARE = 1003
    AGENT_SELECT_PROTO = 1005
    AGENT_LOST_CHAN = 1006
    AGENT_RUN = 1007
    AGENT_SUBSCRIBE = 1008
    AGENT_READ = 1009
    AGENT_WRITE = 1010
    AGENT_STREAM_END = 1011
    AGENT_READ_ERROR = 1012
    AGENT_GOT_SIGNAL = 1013
    AGENT_REQ_NOT_DICT = 1014
    AGENT_REQ_CMD_ERR = 1015
    AGENT_LOST = 1016
    AGENT_LOST_SEND = 1017
    AGENT_FINISH = 1018
    AGENT_UNSUBSCRIBE = 1019
    AGENT_START = 1020
    AGENT_PROC_CREATED = 1021
    AGENT_MSG_LOST = 1022
    AGENT_MSG_UNPROCESSED = 1023
    
    AGENT_EXC_PREPARE = 1100
    AGENT_EXC_NEGOTIATE = 1101
    AGENT_EXC_LOOP = 1102
    AGENT_EXC_SEND = 1103
    
    
    text = {
        MARK: "=" * 25,
        
        HUB_LOAD_MODE: "Load mode '%s'",
        HUB_START: "Start hub",
        HUB_FINISH: "Finish",
        HUB_LOAD_AGENTS: "Load agents config files from '%s'",
        HUB_LOAD_AGENT: "Load agent '%s'",
        HUB_AGENT_COUNT: "Agents in config: %d",
        HUB_LOOP_END: "End loop: done=%d, pending=%d",

        HUB_SET_EXIT_CODE: "Agent '%s' set exit code '%s'",
        
        HUB_MESSAGE: "Message: '%s', msg=%s, opts=%s",
        HUB_MESSAGE_NORET: "Message '%s' no one is listening for answer",
        HUB_MESSAGE_BADCALL: "Message '%s' unknown call check type",
        HUB_MESSAGE_REMOVED: "Message '%s' was removed, msg=%s, opts=%s",
        
        #AGENT_: "Bulk message",
        AGENT_PREPARE: "Prepare agent '%s'",
        AGENT_SELECT_PROTO: "Agent '%s' select protocol '%s'",
        AGENT_LOST_CHAN: "Agent '%s' lost channel",
        AGENT_RUN: "Agent '%s' run",
        AGENT_SUBSCRIBE: "Agent '%s' subscribe to '%s'",
        AGENT_READ: "Read: %s",
        AGENT_WRITE: "Write: %s",
        AGENT_STREAM_END: "Agent '%s' end of stream",
        AGENT_READ_ERROR: "Agent '%s' read error '%s'",
        AGENT_GOT_SIGNAL: "Agent '%s' got signal",
        AGENT_REQ_NOT_DICT: "Request error: not a dictionary",
        AGENT_REQ_CMD_ERR: "Request error: command is not string",
        AGENT_LOST: "Agent '%s' lost",
        AGENT_LOST_SEND: "Agent '%s' lost while sending answer",
        AGENT_FINISH: "Agent '%s' finished",
        AGENT_UNSUBSCRIBE: "Agent '%s' unsubscribe from '%s'",
        AGENT_START: "Start process '%s'",
        AGENT_PROC_CREATED: "Process created",
        AGENT_MSG_LOST: "System message lost: '%s', msg=%s, opts=%s",
        AGENT_MSG_UNPROCESSED: "Message not processed: '%s', msg=%s, opts=%s",
        
        AGENT_EXC_PREPARE: "while preparing",
        AGENT_EXC_NEGOTIATE: "while negotiating",
        AGENT_EXC_LOOP: "in command loop",
        AGENT_EXC_SEND: "sending answer",
    
    }
    @classmethod
    def get(cls, msg_id):
        return cls.text.get(msg_id) or  "No text for '%d'" % msg_id
