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

from . import poller, proccer, stdio, liner
from .poller import Handler, Poller
from .proccer import PopenHandler
from .stdio import StdioHandler, StdioLineHandler
from .liner import LineMixin


log =  functools.partial(print, 'info   :', flush=True)
logw = functools.partial(print, 'warning:', flush=True)
loge = functools.partial(print, 'error  :', flush=True)
logd = functools.partial(print, 'debug  :', flush=True)


def set_logfns(i, w, e, d):

    log(f'setting log functions: {__name__}, {i}, {w}, {e}, {d}')

    modules = {
        poller,
        proccer,
        stdio,
        liner,
    }

    for m in modules:
        m.set_logfns(i, w, e, d)
