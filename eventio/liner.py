# Copyright 2021 "Dan Farrell <djfarrell@hopspan.com>"
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import functools
import subprocess
import sys


log =  functools.partial(print, 'info   :', flush=True)
logw = functools.partial(print, 'warning:', flush=True)
loge = functools.partial(print, 'error  :', flush=True)
logd = functools.partial(print, 'debug  :', flush=True)


class LineMixin(object):

    def __init__(self):

        self.__partial = []
    
    def on_line(self, line):

        log(f'line[{self.name}]: {line}')

    def on_flush_line(self):
        
        self.on_line(b''.join(self.__partial))

    def on_line_data(self, data):

        logd(f'{self.name}: on line data: {data}')

        if isinstance(data, str):
            data = data.encode()

        if b'\n' not in data:
            logd(f'{self.name}: no new line')
            self.__partial.append(data)
        else:
            line_end_idx = data.find(b'\n')
            logd(f'{self.name}: line end idx: {line_end_idx}')
            prev_line_end_idx=0
            while line_end_idx != -1:
                self.on_line(b''.join(self.__partial + [data[prev_line_end_idx:line_end_idx],]))
                self.__partial.clear()
                prev_line_end_idx = line_end_idx + 1
                line_end_idx = data.find(b'\n', prev_line_end_idx)
            if line_end_idx == -1:
                self.__partial.append(data[prev_line_end_idx:])
