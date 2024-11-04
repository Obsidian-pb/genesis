# -*- coding: utf-8 -*-

"""

"""

__author__ = 'SIBPSA'
__date__ = '2024-10-29'
__copyright__ = '(C) 2024 by SIBPSA'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider

from .graph_download_by_box import GDownloadAlgorithm
from .graph_download_by_polygon import GDownloadAlgorithmPoly


class GenesisProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(GDownloadAlgorithm())
        self.addAlgorithm(GDownloadAlgorithmPoly())

    def id(self):
        return 'Genesis'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Генезис')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        return QgsProcessingProvider.icon(self)

    def longName(self):
        return self.name()
