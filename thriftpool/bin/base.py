from __future__ import absolute_import

import sys
import os
import argparse
import traceback

import thriftpool
from thriftpool.utils.platforms import EX_FAILURE, EX_OK
from thriftpool.utils.term import colored, isatty


class Option(object):
    """Describe an option for parser."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def apply(self, parser):
        parser.add_argument(*self.args, **self.kwargs)


class Error(Exception):

    def __init__(self, reason, status=EX_FAILURE):
        self.reason = reason
        self.status = status
        super(Error, self).__init__(reason, status)

    def __str__(self):
        return self.reason


class BaseCommand(object):
    """Abstract command. Other commands should be subclass of this."""

    #: Specify parser class.
    Parser = argparse.ArgumentParser

    #: Specify options for this command.
    options = ()

    #: Argument list used in help.
    args = ''

    #: Application version.
    version = thriftpool.__version__

    def __init__(self, app=None, stdout=sys.stdout, stderr=sys.stderr):
        self.app = thriftpool.thriftpool if app is None else app
        self.colored = colored(enabled=all([isatty(out) for out
                                            in (sys.stderr, sys.stdout)]))
        self.stdout = stdout
        self.stderr = stderr

    def out(self, msg, fh=None):
        """Print some output to text."""
        (fh or self.stdout).write(msg + '\n')

    def error(self, msg):
        """Print given error."""
        self.out(self.colored.red(msg), fh=self.stderr)

    def die(self, msg, status=EX_FAILURE):
        """Print message and exit with given status."""
        self.error(msg)
        sys.exit(status)

    def run(self, *args, **options):
        """This is the body of the command called by :meth:`handle_argv`."""
        raise NotImplementedError('subclass responsibility')

    def __call__(self, *args, **kwargs):
        """Dispatch given call."""
        try:
            ret = self.run(*args, **kwargs)
        except Error as exc:
            self.error(self.colored.red('Error: {0!r}'.format(exc)))
            return exc.status
        except Exception as exc:
            self.error(self.colored.red('Unhandled exception: {0!r}'
                                        .format(exc)))
            traceback.print_tb(sys.exc_info()[2], file=self.stderr)
            return EX_FAILURE

        return ret if ret is not None else EX_OK

    @property
    def description(self):
        """Shortcut for class doc-string."""
        return self.__doc__

    @property
    def usage(self):
        """Returns the command-line usage string for this app."""
        return '%(prog)s [options] {0.args}'.format(self)

    def parser_options(self):
        """Additional parser options."""
        return {}

    def create_parser(self, prog_name):
        """Create new parser."""
        return self.Parser(description=self.description,
                           usage=self.usage,
                           prog=prog_name,
                           **self.parser_options())

    def prepare_parser(self, parser):
        """Prepare parser for work."""
        parser.add_argument('-v', '--version', action='version',
                            version=self.version)
        for option in self.options:
            option.apply(parser)
        return parser

    def parse_options(self, prog_name, arguments):
        """Parse the available options."""
        parser = self.create_parser(prog_name)
        parser = self.prepare_parser(parser)
        return parser.parse_args(arguments)

    def handle_argv(self, prog_name, argv):
        """Parses command line arguments from ``argv`` and dispatches
        to :meth:`__call__`.

        """
        args = self.parse_options(prog_name, argv)
        options = vars(args)
        return self(*argv, **options)

    def execute(self, argv=None):
        """Execute application from command line."""
        if argv is None:
            argv = list(sys.argv)

        prog_name = os.path.basename(argv[0])
        try:
            sys.exit(self.handle_argv(prog_name, argv[1:]))
        except KeyboardInterrupt:
            sys.exit(EX_FAILURE)
