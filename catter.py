
import sys

import eventio


def main():

    poller = eventio.Poller()
    cat = eventio.PopenHandler('__cat__', ['cat'])
    stdin = eventio.StdioHandler()
    stdin.on_stdin = cat.on_stdin
    poller.add_handler(cat)
    poller.add_handler(stdin)

    poller.run()


if __name__ == '__main__':
    sys.exit(main())
