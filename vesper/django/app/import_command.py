"""Module containing class `ImportArchiveDataCommand`."""


from vesper.django.app.command import Command, CommandSyntaxError
from vesper.singletons import extension_manager
import vesper.django.app.command_utils as command_utils


class ImportCommand(Command):
    
    
    name = 'import'
    
    
    def __init__(self, args):
        super().__init__(args)
        importer_spec = command_utils.get_required_arg('importer', args)
        self._importer = _create_importer(importer_spec)
        
        
    def execute(self, context):
        return self._importer.execute(context)


def _create_importer(importer_spec):
    
    try:
        name = importer_spec['name']
    except KeyError:
        raise CommandSyntaxError('Missing required importer name.')
    
    cls = _get_importer_class(name)

    arguments = importer_spec.get('arguments', {})
    
    return cls(arguments)


def _get_importer_class(name):
    classes = extension_manager.instance.get_extensions('Importer')
    try:
        return classes[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized importer name "{}".'.format(name))