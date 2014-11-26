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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QObject, SIGNAL
#Need QMessageBox to show click info in message box
from PyQt4.QtGui import QAction, QIcon#, QMessageBox
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from hydro_data_dialog import HydroDataDialog
import os.path
#Import QGS libraries
from qgis.gui import *
from qgis.core import *

import os
#For web services
import urllib2
import json


class HydroData:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        
        #Get reference to canvas and click functions
        self.canvas = self.iface.mapCanvas()        
        #Tool get get a QgsPoint from each click on the map
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        
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

        # Create the dialog (after translation) and keep reference
        self.dlg = HydroDataDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Hydrology Data Tool')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'HydroData')
        self.toolbar.setObjectName(u'HydroData')

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

        icon_path = ':/plugins/HydroData/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Search for Hydro Data'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        #Subscribe to the mouse click signal
        result = QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
        #QMessageBox.information( self.iface.mainWindow(), "Info", "connect = %s"%str(result) )
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Hydrology Data Tool'),
                action)
            self.iface.removeToolBarIcon(action)

    def epaPointService(self, point):
        x = str(point.x())
        y = str(point.y())
        #Set up the point service URL
        url = "http://ofmpub.epa.gov/waters10/PointIndexing.Service?"\
                +"pGeometry=POINT(%s+%s)"%(x,y)\
                +"&pGeometryMod=WKT%2CSRID%3D8265"\
                +"&pResolution=3"\
                +"&pPointIndexingMethod=DISTANCE"\
                +"&pPointIndexingMaxDist=25"\
                +"&pOutputPathFlag=FALSE"\
                +"&pReturnFlowlineGeomFlag=FALSE"\
                +"&optNHDPlusDataset=2.1"
        #self.dlg.setTextBrowser(url)
        #Call the EPA Waters point service using the qgis lat long coordinates clicked
        response = json.loads(urllib2.urlopen(url).read())
        if response['output']:
            results = response['output']['ary_flowlines']
            showText = x+' , '+y + '\nFound %d results:\n'%len(results)
            showText = showText+'comid = %d\nfmeasure = %d'%(results[0]['comid'],results[0]['fmeasure'])
            self.dlg.setTextBrowser(showText)
            #Return the comid and fmeasure found by the point service
            return (results[0]['comid'], results[0]['fmeasure'])
        else:
            self.dlg.setTextBrowser('No features found at %s, %s'%(x,y))
            return None
    
    def epaNavigationService(self, inputs):
        comID = inputs[0]
        fMeasure = inputs[1]
        #Build navigationDelineation service URL based on inputs retrieved from point service
        url = "http://ofmpub.epa.gov/waters10/NavigationDelineation.Service?"\
                +"pNavigationType=UT"\
                +"&pStartComid=%s"%comID\
                +"&pStartMeasure=%s"%fMeasure\
                +"&pMaxDistance=1000"\
                +"&pMaxTime="\
                +"&pAggregationFlag=true"\
                +"&pFeatureType=CATCHMENT"\
                +"&pOutputFlag=BOTH"\
                +"&optNHDPlusDataset=2.1"\
                +"&optOutGeomFormat=GEOJSON"
        #Call the EPA Waters navigation service
        #TODO need to do this async, and need to keep alive connection...possibly for point service as well
        response = json.loads(urllib2.urlopen(url).read())
        #TODO Store this in tmp space in plugin directory, get this directory dynamically
        with open('/tmp/tmp_watershed.json', 'w') as fp:
            #TODO MAKE SURE THIS HAS VALID DATA!?!?!?!?!?
            json.dump(response['output']['shape'], fp)
        #TODO Add properties to layer from response, such as area ect...
        layer = QgsVectorLayer('/tmp/tmp_watershed.json', 'Delineated Watershed', 'ogr')
        if layer.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(layer)
        else:
            #self.dlg.setTextBrowser(json.dumps(response['output']['shape']))
            self.dlg.setTextBrowser('Layer from:\n'+url+'\n\nis invalid, could not reneder.')
            
           
    def handleMouseDown(self, point, button):
        #QMessageBox.information( self.iface.mainWindow(), "Info", "X,Y = %s,%s"%( str(point.x()), str(point.y()) ) )
        self.dlg.clearTextBrowser()
        self.dlg.setTextBrowser( str(point.x())+' , '+str(point.y()) )
        navInput = self.epaPointService(point)
        if navInput:
            self.epaNavigationService(navInput)
        else:
            #TODO Better error reporting???
            self.dlg.setTextBrowser('No features found, try again')
        
    def run(self):
        """Run method that performs all the real work"""
        #set the click tool
        self.canvas.setMapTool(self.clickTool)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass