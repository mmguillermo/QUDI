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

    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    timer = QtCore.QTimer()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._odmr_logic = self.odmrlogic1()

        # Use the inherited class 'Ui_ODMRGuiUI' to create now the GUI element:
        self._mw = CameraODMRMainWindow()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        #TODO get this from the camera directly
        raw_data_image = np.zeros((512, 512))

        self.odmr_image = pg.ImageItem(image=raw_data_image, axisOrder='row-major')

        self._mw.video_PlotWidget.addItem(self.odmr_image)
        self._mw.video_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.video_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.video_PlotWidget.showGrid(x=True, y=True, alpha=0.8)
        # Get the colorscales at set LUT
        self.my_colors = ColorScaleInferno()

        self.odmr_image.setLookupTable(self.my_colors.lut)

        self.averaged_image_stack = list()

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Update signals coming from logic:
        self._odmr_logic.sigNextLine.connect(self.update_plots, QtCore.Qt.QueuedConnection)
        self.timer.timeout.connect(self.update_image)

        # Show the Main ODMR GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        self._mw.close()
        return 0

    def update_plots(self):
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

    def get_index(self):
        """
        Function to transform (a,b)->c where a,b in [0,wdith-1], [0,height-1] and
        c in [0, width*height-1].
        This is done in analog to how np.reshape works
        :return:
        """
        index = 0 + self.width * self.px_x + self.px_y
        return index

    def update_xy_cb_range(self):
        """Redraw xy colour bar and scan image."""
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    def update_image(self):
        self.log.debug("counter:{0}".format(self.counter))
        self._mw.frequency_lcdNumber.display(self.odmr_data_x[self.counter] / 10 ** 9)
        image = np.reshape(self.odmr_data_y[:, self.counter], (512, 512))
        self.odmr_image.setImage(image=image)
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



