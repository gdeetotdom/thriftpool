from __future__ import absolute_import

import argparse

from six import with_metaclass, iteritems

from thriftworker.utils.decorators import cached_property

from thriftpool.bin.base import BaseCommand
from thriftpool.bin.thriftpoold import ManagerCommand
from thriftpool.utils.text import indent
from thriftpool.utils.mixin import SubclassMixin


class Formatter(argparse.HelpFormatter):
    """Print list of commands with help."""

    umbrella = None

    def _metavar_formatter(self, action, default_metavar):
        if action.choices is None:
            return super(Formatter, self)._metavar_formatter(action,
                                                             default_metavar)

        white = self.umbrella.colored.white
        parts = []
        for name, parser in iteritems(action.choices):
            parts.append(indent('+ {0}: {1}'.format(white(name),
                                                    parser.description), 2))
        result = '\n' + '\n'.join(parts)

        return lambda tuple_size: (result, ) * tuple_size


class Parser(argparse.ArgumentParser):
    """Overwrite default parser."""


class UmbrellaCommand(BaseCommand, SubclassMixin):
    """Umbrella for all commands."""

    #: Specify new parser.
    Parser = Parser

    #: Dictionary that contains existed subcommands.
    subcommand_classes = {}

    @cached_property
    def Formatter(self):
        """Create new :class:`Formatter` bounded to this class."""
        return self.subclass_with_self(Formatter, attribute='umbrella')

    @cached_property
    def subcommands(self):
        """Initialize all subcommands."""
        return {name: cls(app=self.app) for name, cls
                in iteritems(self.subcommand_classes)}

    def parser_options(self):
        return dict(formatter_class=self.Formatter)

    def prepare_parser(self, parser):
        """Prepare parser for work."""
        parser = super(UmbrellaCommand, self).prepare_parser(parser)
        subparsers = parser.add_subparsers(dest='subparser_name')
        for name, command in iteritems(self.subcommands):
            subparser = subparsers.add_parser(name,
                                              description=command.description,
                                              usage=command.usage)
            command.prepare_parser(subparser)
        return parser

    def run(self, *args, **options):
        subparser_name = options.pop('subparser_name')
        command = self.subcommands[subparser_name]
        return command.run(*args[1:], **options)


class SubCommandMeta(type):
    """Metaclass that register sub-commands."""

    def __new__(cls, name, bases, attributes):
        is_abstract = attributes['abstract'] = \
            attributes.get('abstract', False)
        klass = (super(SubCommandMeta, cls)
                 .__new__(cls, name, bases, attributes))
        if not is_abstract:
            UmbrellaCommand.subcommand_classes[klass.__name__.lower()] = klass
        return klass


class abstract(with_metaclass(SubCommandMeta, BaseCommand)):
    """Base class for sub-commands."""

    #: Register this command in umbrella?
    abstract = True


class list_slots(abstract):
    """Print all registered slots."""

    def format_slot(self, slot):
        white = self.colored.white
        yellow = self.colored.yellow
        parts = ['+ {0}: '.format(white(slot.name))]
        parts.extend([indent(s, 4) for s in (
            'listen: {0}:{1}'.format(yellow(slot.listener.host),
                                     yellow(slot.listener.port or 0)),
            'backlog: {0}'.format(yellow(slot.listener.backlog)),
            'processor: {0}'.format(yellow(slot.service.Processor)),
            'handler: {0}'.format(yellow(slot.service.Handler)),
        )])
        return '\n'.join(parts).strip()

    def run(self, *args, **options):
        self.app.finalize()
        self.out('Registered slots:\n')
        for slot in self.app.slots:
            self.out(self.format_slot(slot) + '\n')


class manager(abstract, ManagerCommand):
    """Run manager daemon. Same as `thriftpoold`."""


def main():
    UmbrellaCommand().execute()


if __name__ == '__main__':
    main()
