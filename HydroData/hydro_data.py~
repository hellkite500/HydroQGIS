# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HydroData
                                 A QGIS plugin
 This plugin searches for hydrological data.
                              -------------------
        begin                : 2014-11-24
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
#Need to import QObject and SIGNAL as well as defaults from plugin builder
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
#Need QMessageBox to show click info in message box
from PyQt4.QtGui import QAction, QIcon, QMenu, QToolButton#, QMessageBox
# Initialize Qt resources from file resources.py
import resources_rc


import os.path
from tools.Deliniation import DeliniationTool
from tools.NWISsearch import NWISsearchTool            
class HydroData():
    """QGIS Plugin Implementation.
    This is the entry point for the suite of tools for HydroQGIS
    Each tool can be implemented under the tools module, and then be
    imported and added to the plugin menu as actions.
    
    This allows each tool to have its own implementation and dialog.
    Additional utilities can be created as sub-modules, such as the services module
    that contains utilities for calling EPA WATERS services.  These services are then
    called via threads in the DeliniationTool.
    """

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """        
        # Save reference to the QGIS interface
        self.iface = iface
        
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HydroData_{0}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)



        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hydrology Data Tool')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'HydroData')
        self.toolbar.setObjectName(u'HydroData')
        #Create toolbar menu and widget
        self.popupMenu = QMenu(self.iface.mainWindow())
        self.toolButton = QToolButton()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('HydroData', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        #Create the objects for each tool
        self.deliniationTool = DeliniationTool(self.iface)
        self.nwisSearchTool = NWISsearchTool(self.iface)
        
        icon_path = ':/plugins/HydroData/icon.png'
        #Add watershed deliniation tool to the menu
        self.add_action(
            icon_path,
            text=self.tr(u'Deliniate Watershed'),
            callback=self.deliniationTool.run,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)
        #Add NWIS search tool to the menu
        self.add_action(
            icon_path, 
            text=self.tr(u'Search for NWIS Stations'), 
            callback=self.nwisSearchTool.run, 
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)
            

        #Add all the actions to the popupMenu to display on the toolbar
        for action in self.actions:
            self.popupMenu.addAction(action)
        
        self.toolButton.setMenu( self.popupMenu )
        self.toolButton.setDefaultAction( self.actions[0] )
        self.toolButton.setPopupMode( QToolButton.InstantPopup )

        self.iface.addToolBarWidget( self.toolButton )
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Hydrology Data Tool'),
                action)
            self.iface.removeToolBarIcon(action)
