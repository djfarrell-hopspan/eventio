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

import bisect
import functools
import fcntl
import os
import select
import time


log =  functools.partial(print, 'info   :')
logw = functools.partial(print, 'warning:')
loge = functools.partial(print, 'error  :')
logd = functools.partial(print, 'debug  :')


def set_logfns(i, w, e, d):

    global log
    global logw
    global loge
    global logd

    log = i
    logw = w
    loge = e
    logd = d


class Handler(object):

    def __init__(self, name, fds=tuple()):

        self.name = name

        if not hasattr(self, 'fds'):
            self.fds = set()

        if isinstance(fds, int):
            fds = (fds,)
        self.fds.update(fds)
        self.poller = None
        self.set_fds_nonblock()

    def on_closed_fd(self, fd):

        log(f'handler[{self.name}]: on closed fd: {fd}')
        if fd in self.fds:
            self.on_flush_fd(fd)
            self.fds.discard(fd)
            self.poller.pop_fd(fd)

    def on_flush_fd(self, fd):

        log(f'handler[{self.name}]: on flush fd: {fd}')

    def check_closed_fds(self):

        for fd in self.fds:
            logd(f'{self.name}: checking fd: {fd}')
            fcntl_ret = fcntl.fcntl(fd, fcntl.F_GETFD)
            if fcntl_ret == -1:
                log(f'{self.name}: bad fd: {fd}')
                self.poller.pop_fd(fd)

    def set_fds_nonblock(self):

        for fd in self.fds:
            flag = fcntl.fcntl(fd, fcntl.F_GETFL)
            if not flag & os.O_NONBLOCK:
                log(f'{self.name}: setting fd nonblock: {fd}')
                fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    def set_poller(self, poller):

        self.poller = poller

    def on_readable(self, fd):

        logd(f'handler[{self.name}]: on readable')

    def on_writeable(self, fd):

        logd(f'handler[{self.name}]: on writeable')

    def on_errorable(self, fd):

        loge(f'handler[{self.name}]: on error')

    def on_hupable(self, fd):

        loge(f'handler[{self.name}]: on hup')
        self.on_closed_fd(fd)

    @classmethod
    def get_all_bases(cls, all_bases=set()):

        all_bases.update(cls.__bases__)
        for c in cls.__bases__:
            if hasattr(c, 'get_all_bases'):
                c.get_all_bases(all_bases=all_bases)

        return all_bases

    @classmethod
    def is_overriden(cls, fn_name):

        bases = cls.get_all_bases({cls})
        impls = set()
        for b in bases:
            if b is Handler:
                continue

            impl = b.__dict__.get(fn_name)
            if impl is not None:
                impls.add(impl)

        return bool(impls)

    def wants_readable(self):

        logd(f'handler[{self.name}]: check readable')

        return self.is_overriden('on_readable')

    def wants_writeable(self):

        return False

    def wants_errorable(self):

        logd(f'handler[{self.name}]: check errorable')

        return True

    def wants_hupable(self):

        logd(f'handler[{self.name}]: check hupable')

        return True

    def on_run(self):

        log(f'handler[{self.name}]: on run')


class Poller(object):

    sizehint = 100
    ein = select.EPOLLIN
    eout = select.EPOLLOUT
    eerr = select.EPOLLERR
    ehup = select.EPOLLHUP

    def __init__(self):

        self.epoll = select.epoll(self.sizehint)
        self.handler_fds = {}
        self.timeouts = []

    def add_handler(self, handler):

        log(f'poller: add handler: {handler.name}')

        events = 0
        if handler.wants_readable():
            log(f'poller: {handler.name}: wants readable')
            events |= self.ein
        if handler.wants_writeable():
            log(f'poller: {handler.name}: wants writeable')
            events |= self.eout
        if handler.wants_errorable():
            log(f'poller: {handler.name}: wants errorable')
            events |= self.eerr

        for fd in handler.fds:
            self.handler_fds[fd] = handler
            self.epoll.register(fd, events)

        handler.set_poller(self)

    def pop_handler(self, handler):

        log(f'poller: pop handler: {handler.name}')

        for fd in set(self.handler_fds):
            self.handler_fds.pop(fd)

        if not len(self.handler_fds):
            logw(f'poller: no more handlers')
            raise SystemExit(0)

    def pop_fd(self, fd):

        log(f'poller: pop fd: {fd}')

        if fd not in self.handler_fds:
            logw(f'poller: missing handler for fd: {fd}')
        for fd in set(self.handler_fds):
            handler = self.handler_fds.pop(fd)
            log(f'poller: pop fd -> {handler.name}')

        if not len(self.handler_fds):
            logw(f'poller: no more handlers')
            raise SystemExit(0)

    def run_one(self, timeout=None):

        if self.timeouts:
            now = time.monotonic()
            if timeout is None:
                timeout = 1.
            timeout_deadline = timeout + now
            soonest_deadline, _, _, _ = self.timeouts[0]
            deadline = min(soonest_deadline, timeout_deadline)
            timeout = deadline - now

        polls = self.epoll.poll(timeout=timeout)
        used_handlers = set()
        for fd, events in polls:
            handler = self.handler_fds.get(fd)
            used_handlers.add(handler)
            done_events = 0
            if handler:
                if events & self.ein:
                    logd(f'poller: {handler.name}: in: {self.ein}')
                    handler.on_readable(fd)
                    done_events += self.ein
                if events & self.eout:
                    logd(f'poller: {handler.name}: out: {self.eout}')
                    handler.on_writeable(fd)
                    done_events += self.eout
                if events & self.eerr:
                    logd(f'poller: {handler.name}: err: {self.eerr}')
                    handler.on_errorable(fd)
                    done_events += self.eerr
                if events & self.ehup:
                    logd(f'poller: {handler.name}: hup: {self.ehup}')
                    handler.on_hupable(fd)
                    done_events += self.ehup
                if events & ~done_events:
                    loge(f'poller: {handler.name}: {fd}: {events}: {done_events}: left over events: 0x{events & ~done_events:08x}')
                    handler.on_closed_fd(fd)
        for handler in used_handlers:
            handler.check_closed_fds()

        now = time.monotonic()
        num_timeouts = 0
        for deadline, fn, args, kwargs, in self.timeouts:
            if deadline > now:
                break
            num_timeouts += 1
            fn(now, *args, **kwargs)

        if num_timeouts:
            self.timeouts = self.timeouts[num_timeouts:]

    def run(self):

        log(f'poller: running...')
        handlers = set()
        for fd, handler in self.handler_fds.items():
            handlers.add(handler)

        for handler in handlers:
            handler.on_run()

        try:
            while True:
                self.run_one()
        except KeyboardInterrupt:
            pass
        except SystemExit:
            pass

        log(f'poller: ... finished')

    def add_timeout(self, fn, from_now, args=tuple(), kwargs=dict()):

        deadline = time.monotonic() + from_now
        bisect.insort(self.timeouts, (deadline, fn, args, kwargs))
