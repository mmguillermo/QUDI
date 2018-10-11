# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""
import numpy as np
import os
import pyqtgraph as pg

from core.module import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from qtpy import QtGui
import time
import threading

class CameraODMRMainWindow(QtWidgets.QMainWindow):
    """ The main window for the ODMR measurement GUI.
    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_cameraodmrgui.ui')

        # Load it
        super(CameraODMRMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class CameraODMRGui(GUIBase):
    """
    This is the GUI Class for ODMR measurements
    """

    _modclass = 'CameraODMRGui'
    _modtype = 'gui'

    # declare connectors
    odmrlogic1 = Connector(interface='ODMRLogic')
    savelogic = Connector(interface='SaveLogic')
    camera_logic = Connector(interface='CameraLogic')

    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigAreaChanged = QtCore.Signal(list)
    timer = QtCore.QTimer()
    sigDoCameraFit = QtCore.Signal(str, object, object, int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.odmrlogic1()
        self._camera_logic = self.camera_logic()

        # get dimensions of camera
        self.width_x, self.width_y = self._camera_logic._hardware.get_size()

        # Use the inherited class 'Ui_ODMRGuiUI' to create now the GUI element:
        self._mw = CameraODMRMainWindow()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        self.odmr_plot = pg.PlotDataItem(self._odmr_logic.odmr_plot_x,
                                          self._odmr_logic.odmr_plot_y[0],
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)

        self.odmr_fit_image = pg.PlotDataItem(self._odmr_logic.odmr_fit_x,
                                              self._odmr_logic.odmr_fit_y,
                                              pen=pg.mkPen(palette.c2))

        # configure odmr_PlotWidget
        self._mw.odmr_PlotWidget.addItem(self.odmr_plot)
        self._mw.odmr_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.odmr_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.odmr_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # configure video_PlotWidget
        self.raw_data_image = np.zeros((self.width_x, self.width_y))

        self._image = pg.ImageItem(image=self.raw_data_image, axisOrder='col-major')

        self._mw.video_PlotWidget.addItem(self._image)
        self._mw.video_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        # Get the colorscales at set LUT
        self.my_colors = ColorScaleInferno()

        self._image.setLookupTable(self.my_colors.lut)

        self.averaged_image_stack = list()

        # state variable signifying the area of the camera to be evaluated
        self.area = [self.get_index(0, 0), self.get_index(self.width_x - 1, self.width_y - 1)]

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Update signals coming from logic:
        self.timer.timeout.connect(self.update_image)
        self._mw.action_select.toggled.connect(self.select_clicked)
        self._mw.video_PlotWidget.sigMouseClick.connect(self.start_select_point)
        self._mw.video_PlotWidget.sigMouseReleased.connect(self.end_select_point)
        self._odmr_logic.sigOdmrPlotsUpdated.connect(self.update_odmr_plot, QtCore.Qt.QueuedConnection)
        self._odmr_logic.sigNextLine.connect(self.update_variables, QtCore.Qt.QueuedConnection)
        # relay area to crop data
        self.sigAreaChanged.connect(self.update_averaged_plot, QtCore.Qt.QueuedConnection)

        # Connect the buttons and inputs for the colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)
        self._mw.xy_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)

        # do fit
        self.sigDoCameraFit.connect(self._odmr_logic.do_camera_fit, QtCore.Qt.QueuedConnection)
        self._mw.do_fit_PushButton.clicked.connect(self.do_fit)

        ########################################################################
        #                          fit settings                                #
        ########################################################################
        self._fsd = FitSettingsDialog(self._odmr_logic.fc)
        self._fsd.sigFitsUpdated.connect(self._mw.fit_methods_ComboBox.setFitFunctions)
        self._fsd.applySettings()
        self._mw.action_FitSettings.triggered.connect(self._fsd.show)
        self._odmr_logic.sigCameraOdmrFitUpdated.connect(self.update_fit, QtCore.Qt.QueuedConnection)

        ########################################################################
        #                             Color Bar                                #
        ########################################################################
        self.xy_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c')
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        # Show the Main ODMR GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._mw.close()
        self.sigDoCameraFit.disconnect()
        self._fsd.sigFitsUpdated.disconnect()
        return 0

    def update_variables(self):
        n_sweeps = self._odmr_logic.elapsed_sweeps
        if n_sweeps >= 1:
            elapsed_time = self._odmr_logic.elapsed_time
            time_per_sweep = elapsed_time / n_sweeps
            self.odmr_data_x = self._odmr_logic.odmr_plot_x
            self.odmr_data_y = self._odmr_logic.odmr_plot_y
            self.counter = 0
            self.n_freqs = len(self.odmr_data_x)
            # here the plot needs to be updated on a regular basis
            self.interval = time_per_sweep / self.n_freqs
            # qtimer is in ms
            self.timer.start((self.interval-self.interval/10) * 1000)
            self.log.debug("wait time:{0}".format(self.interval))
        else:
            return

    def get_index(self, px_x, px_y):
        """
        Function to transform (a,b)->c where a,b in [0,wdith-1], [0,height-1] and
        c in [0, width*height-1].
        This is done in analogy to np.reshape
        :return:
        """
        index = int(0 + self.width_x * px_x + px_y)
        return index

    #colorbar functions

        # color bar functions
    def get_xy_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.xy_cb_manual_RadioButton.isChecked() or np.max(self._image.image) == 0.0:
            cb_min = self._mw.xy_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.xy_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # xy_image_nonzero = self._image.image[np.nonzero(self._image.image)]

            # Read centile range
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(self._image.image, low_centile)
            cb_max = np.percentile(self._image.image, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and higherst value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range = self.get_xy_cb_range()
        self.xy_cb.refresh_colorbar(cb_range[0], cb_range[1])

    def refresh_xy_image(self):
        """ Update the current XY image from the logic.

        Everytime the scanner is scanning a line in xy the
        image is rebuild and updated in the GUI.
        """
        self._image.getViewBox().updateAutoRange()

        xy_image_data = self._image.image

        cb_range = self.get_xy_cb_range()

        # Now update image with new color scale, and update colorbar
        self._image.setImage(image=xy_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_xy_colorbar()

    def shortcut_to_xy_cb_manual(self):
        """Someone edited the absolute counts range for the xy colour bar, better update."""
        self._mw.xy_cb_manual_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_xy_cb_centiles(self):
        """Someone edited the centiles range for the xy colour bar, better update."""
        self._mw.xy_cb_centiles_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def update_xy_cb_range(self):
        """Redraw xy colour bar and scan image."""
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    def update_image(self):
        self.log.debug("counter:{0}".format(self.counter))
        self._mw.frequency_lcdNumber.display(self.odmr_data_x[self.counter] / 10 ** 9)
        image = np.reshape(self.odmr_data_y[:, self.counter], (self.width_x, self.width_y))
        self._image.setImage(image=image)
        if self.counter < self.n_freqs-1:
            self.counter += 1
        else:
            self.timer.stop()
            self.counter = 0

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def select_clicked(self, is_checked):
        """ Activates the select mode in the image.

        @param bool is_checked: pass the state of the zoom button if checked
                                or not.

        Depending on the state of the zoom button the DragMode in the
        ViewWidgets are changed.  There are 3 possible modes and each of them
        corresponds to a int value:
            - 0: NoDrag
            - 1: ScrollHandDrag
            - 2: RubberBandDrag

        Pyqtgraph implements every action for the NoDrag mode. That means the
        other two modes are not used at the moment. Therefore we are using the
        RubberBandDrag mode to simulate a zooming procedure. The selection
        window in the RubberBandDrag is only used to show the user which region
        will be selected. But the zooming idea is based on catched
        mousePressEvent and mouseReleaseEvent, which will be used if the
        RubberBandDrag mode is activated.

        For more information see the qt doc:
        http://doc.qt.io/qt-4.8/qgraphicsview.html#DragMode-enum
        """

        # You could also set the DragMode by its integer number, but in terms
        # of readability it is better to use the direct attributes from the
        # ViewWidgets and pass them to setDragMode.
        if is_checked:
            self._image.getViewBox().setLeftButtonAction('rect')
        else:
            self._image.getViewBox().setLeftButtonAction('pan')

    def start_select_point(self, event):
        """ Get the mouse coordinates if the mouse button was pressed.

        @param QMouseEvent event: Mouse Event object which contains all the
                                  information at the time the event was emitted
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_select.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        pos = self._image.getViewBox().mapSceneToView(event.localPos())
        # store the initial mouse position in a class variable
        self._current_xy_zoom_start = [pos.x(), pos.y()]
        event.accept()

    def end_select_point(self, event):
        """ Get the mouse coordinates if the mouse button was released.

        @param QEvent event:
        """
        # catch the event if the zoom mode is activated and if the event is
        # coming from a left mouse button.
        if not (self._mw.action_select.isChecked() and (event.button() == QtCore.Qt.LeftButton)):
            event.ignore()
            return

        # get the ViewBox which is also responsible for the xy_image
        viewbox = self._image.getViewBox()

        # Map the mouse position in the whole ViewWidget to the coordinate
        # system of the ViewBox, which also includes the 2D graph:
        pos = viewbox.mapSceneToView(event.localPos())
        endpos = [pos.x(), pos.y()]
        initpos = self._current_xy_zoom_start

        # get the right corners from the zoom window:
        if initpos[0] > endpos[0]:
            xMin = endpos[0]
            xMax = initpos[0]
        else:
            xMin = initpos[0]
            xMax = endpos[0]

        if initpos[1] > endpos[1]:
            yMin = endpos[1]
            yMax = initpos[1]
        else:
            yMin = initpos[1]
            yMax = endpos[1]

        # Finally change the visible area of the ViewBox:
        event.accept()
        self._mw.action_select.setChecked(False)
        self.sigAreaChanged.emit([(xMin, yMin), (xMax, yMax)])
        return

    def update_averaged_plot(self, rect_pos):
        """
        From the position supplied by the function end_select_point via the
        Signal sigAreaChanged.
        :return:
        """
        # unpack the list
        xmin, ymin = rect_pos[0]
        xmax, ymax = rect_pos[1]

        xmin = np.round(xmin)
        ymin = np.round(ymin)
        xmax = np.round(xmax)
        ymax = np.round(ymax)
        self.log.debug('xmin, ymin:{0},{1}'.format(xmin, ymin))
        self.log.debug('xmax, ymax:{0}, {1}'.format(xmax, ymax))
        ind_low = self.get_index(xmin, ymin)
        ind_high = self.get_index(xmax, ymax)
        # update area
        self.area[0] = ind_low
        self.area[1] = ind_high
        self.log.debug('what are the indices:{0},{1}'.format(ind_low, ind_high))

        # get the data needed an average it
        odmr_plot_y = np.average(self._odmr_logic.odmr_plot_y[ind_low:ind_high, :], axis=0)
        odmr_plot_x = self._odmr_logic.odmr_plot_x
        self.log.debug('dimensions of odmr_plot_y:{0}'.format(odmr_plot_y.shape))
        # Update mean signal plot
        self.odmr_plot.setData(odmr_plot_x, odmr_plot_y)

    def update_odmr_plot(self, odmr_plot_x, odmr_plot_y, odmr_plot_xy):
        """
        Resemble the update of plots in the logic by displaying it in the gui
        :return:
        """
        self.averaged_odmr_plot_y = np.average(odmr_plot_y[self.area[0]:self.area[1], :], axis=0)
        self.odmr_plot.setData(odmr_plot_x,
                               self.averaged_odmr_plot_y)


    # fit related

    def do_fit(self):
        fit_function = self._mw.fit_methods_ComboBox.getCurrentFit()[0]
        self.sigDoCameraFit.emit(fit_function, self._odmr_logic.odmr_plot_x, self.averaged_odmr_plot_y, None)
        return

    def update_fit(self, x_data, y_data, result_str_dict, current_fit):
        """ Update the shown fit. """
        if current_fit != 'No Fit':
            # display results as formatted text
            self._mw.odmr_fit_results_DisplayWidget.clear()
            try:
                formated_results = units.create_formatted_output(result_str_dict)
            except:
                formated_results = 'this fit does not return formatted results'
            self._mw.odmr_fit_results_DisplayWidget.setPlainText(formated_results)

        self._mw.fit_methods_ComboBox.blockSignals(True)
        self._mw.fit_methods_ComboBox.setCurrentFit(current_fit)
        self._mw.fit_methods_ComboBox.blockSignals(False)

        # check which Fit method is used and remove or add again the
        # odmr_fit_image, check also whether a odmr_fit_image already exists.
        if current_fit != 'No Fit':
            self.odmr_fit_image.setData(x=x_data, y=y_data)
            if self.odmr_fit_image not in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.addItem(self.odmr_fit_image)
        else:
            if self.odmr_fit_image in self._mw.odmr_PlotWidget.listDataItems():
                self._mw.odmr_PlotWidget.removeItem(self.odmr_fit_image)

        self._mw.odmr_PlotWidget.getViewBox().updateAutoRange()
        return