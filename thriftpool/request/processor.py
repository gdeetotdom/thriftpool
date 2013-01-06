"""Contains patched processor."""
from __future__ import absolute_import

from thrift.Thrift import TApplicationException, TMessageType


class ProcessorMixin(object):
    """Process application error if there is one."""

    def process(self, iprot, oprot):
        name, type, seqid = iprot.readMessageBegin()

        try:
            try:
                fn = self._processMap[name]
            except KeyError:
                msg = 'Unknown function %s' % (name)
                code = TApplicationException.UNKNOWN_METHOD
                raise TApplicationException(code, msg)
            else:
                fn(self, seqid, iprot, oprot)

        except TApplicationException as exc:
            oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
            exc.write(oprot)
            oprot.writeMessageEnd()
            oprot.trans.flush()

        return name
