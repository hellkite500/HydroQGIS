# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FFADialog
                                 A QGIS plugin
 This plugin performs flood frequency analysis.
                             -------------------
        begin                : 2015-04-01
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
    os.path.dirname(__file__), 'ffa_dialog_base.ui'))


class FFADialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(FFADialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.browse_button.clicked.connect(self.saveToFile)
        
    def setTextBrowser(self, output):
        self.txtFeedback.setText(output)
        
    def clearTextBrowser(self):
        self.txtFeedback.clear()

    def addToTextBrowser(self, output):
        self.txtFeedback.insertPlainText(output+'\n')
        
    def saveToFile(self):
        self.save_edit.setText(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))
        
