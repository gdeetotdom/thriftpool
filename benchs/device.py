from base import factory
from setproctitle import setproctitle


def main():
    device = factory.Device()
    device.start()


if __name__ == '__main__':
    setproctitle('[device]')
    main()
    #import cProfile
    #cProfile.runctx("main()", globals(), locals(), "device.prof")
