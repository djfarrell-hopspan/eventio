
import bisect
import functools
import select
import time


log =  functools.partial(print, 'info   :')
logw = functools.partial(print, 'warning:')
loge = functools.partial(print, 'error  :')
logd = functools.partial(print, 'debug  :')


class Handler(object):

    def __init__(self, name, fds=tuple()):

        self.name = name

        if not hasattr(self, 'fds'):
            self.fds = set()

        if isinstance(fds, int):
            fds = (fds,)
        self.fds.update(fds)
        self.poller = None

    def set_poller(self, poller):

        self.poller = poller

    def on_readable(self, fd):

        pass

    def on_writeable(self, fd):

        pass

    def on_errorable(self, fd):

        pass

    def wants_readable(self):

        logd(f'handler[{self.name}]: check readable')
        self_readable = self.__class__.__dict__.get('on_readable')
        base_readable = Handler.__dict__.get('on_readable')
        return self_readable is not None or \
                self_readable != base_readable

    def wants_writeable(self):

        return False

    def wants_errorable(self):

        logd(f'handler[{self.name}]: check errorable')
        return self.__class__.__dict__.get('on_errorable') is not None

    def on_run(self):

        log(f'handler[{self.name}]: on run')


class Poller(object):

    sizehint = 100
    ein = select.EPOLLIN
    eout = select.EPOLLOUT
    eerr = select.EPOLLERR

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
        for fd, events in polls:
            handler = self.handler_fds.get(fd)
            if handler:
                if events & self.ein:
                    handler.on_readable(fd)
                if events & self.eout:
                    handler.on_writeable(fd)
                if events & self.eerr:
                    handler.on_errorable(fd)

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

        log(f'poller: ... finished')

    def add_timeout(self, fn, from_now, args=tuple(), kwargs=dict()):

        deadline = time.monotonic() + from_now
        bisect.insort(self.timeouts, (deadline, fn, args, kwargs))
