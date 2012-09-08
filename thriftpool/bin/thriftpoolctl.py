from __future__ import absolute_import

from thriftpool.bin.base import BaseCommand, Option
from thriftpool.utils.functional import cached_property
from thriftpool.utils.text import indent


class UmbrellaCommand(BaseCommand):
    """Umbrella for all commands."""

    #: Dictionary that contains existed subcommands.
    subcommand_classes = {}

    @cached_property
    def subcommands(self):
        """Initialize all subcommands."""
        return {name: cls(app=self.app) for name, cls
                in self.subcommand_classes.items()}

    def prepare_parser(self, parser):
        """Prepare parser for work."""
        parser = super(UmbrellaCommand, self).prepare_parser(parser)
        subparsers = parser.add_subparsers(dest='subparser_name')
        for name, command in self.subcommands.items():
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
        is_abstract = attributes['abstract'] = attributes.get('abstract', False)
        klass = super(SubCommandMeta, cls).__new__(cls, name, bases, attributes)
        if not is_abstract:
            UmbrellaCommand.subcommand_classes[klass.__name__.lower()] = klass
        return klass


class abstract(BaseCommand):
    """Base class for sub-commands."""

    __metaclass__ = SubCommandMeta

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
            'processor: {0}'.format(yellow(slot.service.processor_cls)),
            'handler: {0}'.format(yellow(slot.service.handler_cls)),
        )])
        return '\n'.join(parts).strip()

    def run(self, *args, **options):
        self.app.finalize()
        self.out('Registered slots:\n')
        for slot in self.app.slots:
            self.out(self.format_slot(slot) + '\n')


def main():
    UmbrellaCommand().execute()


if __name__ == '__main__':
    main()
