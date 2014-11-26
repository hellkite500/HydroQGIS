# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HydroData
                                 A QGIS plugin
 This plugin searches for hydrological data.
                             -------------------
        begin                : 2014-11-24
        copyright            : (C) 2014 by Nels Frazier
        email                : hellkite500@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load HydroData class from file HydroData.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .hydro_data import HydroData
    return HydroData(iface)
