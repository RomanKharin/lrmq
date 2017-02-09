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
            record.msg = LogTypes.text[record.msg]
        except Exception as e:
            print(e)
            pass
        return True
        
class LogTypes():
    MARK = 10

    # hub 100 - 1000
    HUB_LOAD_MODE = 100
    HUB_START = 101
    HUB_FINISH = 102
    
    # agent 1000 -
    AGENT_ = 1000
    
    
    text = {
        MARK: "=" * 25,
        
        HUB_LOAD_MODE: "Load mode %s",
        HUB_START: "Start hub",
        HUB_FINISH: "Finish",
        
        AGENT_: "Bulk message",
    
    }
    @classmethod
    def get(cls, msg_id):
        return cls.text.get(msg_id) or  "No text for '%d'" % msg_id
