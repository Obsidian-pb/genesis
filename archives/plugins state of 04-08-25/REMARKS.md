# Использование сторонних библиотек в плагинах

QGIS, as distributed by **OSGeo4W**, usually comes with its own Python installation and its own packages that are independent of your "regular" Python installation.

The easiest way to install a Python package into the OSGeo4W distribution is to open the OSGeo4W Shell and use pip from there. This will install the package into the Python distribution QGIS uses, in my case located at `C:\OSGeo4W64\apps\Python27\` and the modules accordingly at `C:\OSGeo4W64\apps\Python27\Lib\site-packages`. You can also do a **regular pip list** inside the OSGeo4W Shell and your regular Windows Shell (cmd.exe) and compare the outputs to see what packages you might be missing.

If you don't want to install packages to two Python installations you could also try to change the _PythonPath_ to include packages from one installation into the other.

*edit: This answer is directed at the original question regarding pip to install modules to be used with QGIS in Windows. OP has since edited/refined the question so this answer is a bit broad now.*

Источник: https://gis.stackexchange.com/questions/141320/installing-3rd-party-python-libraries-for-qgis-on-windows


# Полезные ссылки

## Страницы документации

Иерархия классов процессинг плагина: https://qgis.org/pyqgis/master/core/QgsProcessingParameterDefinition.html

Определение легенды в макете: https://qgis.org/pyqgis/master/core/QgsDataDefinedSizeLegend.html



