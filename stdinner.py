
import sys

import eventio


def main():

    poller = eventio.Poller()
    stdin = eventio.StdioLineHandler()
    poller.add_handler(stdin)

    poller.run()


if __name__ == '__main__':
    sys.exit(main())
