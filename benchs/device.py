from base import factory
from setproctitle import setproctitle


def main():
    device = factory.Device()
    device.start()
    device.join()


if __name__ == '__main__':
    setproctitle('[device]')
    main()
