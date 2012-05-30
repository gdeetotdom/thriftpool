import time
import sys
import multiprocessing
import gc
import gevent
from gevent import pool
from gevent_zeromq import zmq


if sys.platform == 'win32':
    _timer = time.clock
else:
    _timer = time.time

delta = 1

#### TEST_PIPESPEED


def pipe_func(c, cond, iterations):
    a = '0' * 256
    cond.acquire()
    cond.notify()
    cond.release()

    for i in xrange(iterations):
        c.send(a)

    c.send('STOP')


def test_pipespeed():
    c, d = multiprocessing.Pipe()
    cond = multiprocessing.Condition()
    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        p = multiprocessing.Process(target=pipe_func,
                                    args=(d, cond, iterations))
        cond.acquire()
        p.start()
        cond.wait()
        cond.release()

        result = None
        t = _timer()

        while result != 'STOP':
            result = c.recv()

        elapsed = _timer() - t
        p.join()

    print iterations, 'objects passed through connection in', elapsed, 'seconds'
    print 'average number/sec:', iterations / elapsed


def test_gevent_zeromq():
    ctx = zmq.Context()

    rep = ctx.socket(zmq.REP)
    rep.bind("inproc://bench")

    req = ctx.socket(zmq.REQ)
    req.connect ("inproc://bench")

    def consumer(socket):

        result = None
        t = _timer()

        while result != 'STOP':
            result = socket.recv()
            socket.send('')

        elapsed = _timer() - t

        return elapsed

    def producer(socket, iterations):
        a = '0' * 256

        for i in xrange(iterations):
            socket.send(a)
            socket.recv()

        socket.send('STOP')
        socket.recv()

    elapsed = 0
    iterations = 1

    while elapsed < delta:
        iterations *= 2

        consumer_greenlet = gevent.spawn(consumer, rep)
        producer_greenlet = gevent.spawn(producer, req, iterations)

        group = pool.Group()
        group.add(consumer_greenlet)
        group.add(producer_greenlet)

        elapsed = consumer_greenlet.get()

        group.join()

    print iterations, 'objects passed through connection in', elapsed, 'seconds'
    print 'average number/sec:', iterations / elapsed


def test():

    gc.disable()

    print '\n\t######## testing multiprocessing.Pipe\n'
    test_pipespeed()

    print

    print '\n\t######## testing gevent_zeromq\n'
    test_gevent_zeromq()

    print

    gc.enable()

if __name__ == '__main__':
    multiprocessing.freeze_support()
    test()
