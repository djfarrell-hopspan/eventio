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

from . import poller
from . import stdio


log =  functools.partial(print, 'info   :', flush=True)
logw = functools.partial(print, 'warning:', flush=True)
loge = functools.partial(print, 'error  :', flush=True)
logd = functools.partial(print, 'debug  :', flush=True)


def set_logfns(i, w, e, d):

    global log
    global logw
    global loge
    global logd

    log = i
    logw = w
    loge = e
    logd = d


class PopenHandler(poller.Handler):

    def __init__(self, name, *popen_args, **popen_kwargs):

        popen_kwargs['stdin'] = subprocess.PIPE
        popen_kwargs['stdout'] = subprocess.PIPE
        popen_kwargs['stderr'] = subprocess.PIPE

        self.popen = subprocess.Popen(*popen_args, **popen_kwargs)

        self.stdin = self.popen.stdin
        self.stdout = self.popen.stdout
        self.stderr = self.popen.stderr

        fds = {
            self.stdin.fileno(),
            self.stdout.fileno(),
            self.stderr.fileno(),
        }

        poller.Handler.__init__(self, name, fds=fds)

    def on_stdin(self, data):

        log(f'{self.name}: stdin: {data}')

        ret = self.stdin.write(data)
        if ret:
            logd(f'{self.name}: stdin: ret: {ret}')
            self.stdin.flush()
        return ret

    def on_stdout(self, data):

        log(f'popen[{self.name}]: stdout: {data}')

    def on_stderr(self, data):

        log(f'popen[{self.name}]: stderr: {data}')

    def on_stdout_event(self):

        data = self.stdout.read(2**16)
        if not len(data):
            self.poller.pop_fd(self.stdout.fileno())
        else:
            self.on_stdout(data)

    def on_stderr_event(self):

        data = self.stderr.read(2**16)
        if not len(data):
            self.poller.pop_fd(self.stderr.fileno())
        else:
            self.on_stderr(data)

    def on_readable(self, fd):

        if fd == self.stdout.fileno():
            self.on_stdout_event()
        elif fd == self.stderr.fileno():
            self.on_stderr_event()
        else:
            loge('popen[{self.name}]: unknown fd readable: {fd}')
