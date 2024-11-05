# -*- coding: utf-8 -*-

__author__ = 'SIBPSA'
__date__ = '2024-10-29'
__copyright__ = '(C) 2024 by SIBPSA'


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GPKGGraphBuilder class from file GPKGGraphBuilder.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .genesis_plugin import GenesisPlugin
    return GenesisPlugin()
