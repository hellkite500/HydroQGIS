# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NWIS Station Search Dialog
                                 A QGIS plugin
 This plugin searches for NWIS stations.
                             -------------------
        begin                : 2014-11-30
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Nels Frazier
        email                : hellkite500@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'nwis_search_dialog_base.ui'))


class NWISsearchDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(NWISsearchDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
    def setTextBrowser(self, output):
        self.txtFeedback.setText(output)
        
    def clearTextBrowser(self):
        self.txtFeedback.clear()

    def addToTextBrowser(self, output):
        self.txtFeedback.insertPlainText(output+'\n')
            
    def getDistance(self):
        return self.searchDistance.value()
