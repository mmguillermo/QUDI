# -*- coding: utf-8 -*-

"""
This file contains the Qudi interfuse between ODMR Logic and MW/Slow Counter HW.

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

from core.module import Connector
from logic.generic_logic import GenericLogic
from interface.odmr_counter_interface import ODMRCounterInterface
from core.module import Connector

class ODMRCounterCamera(GenericLogic, ODMRCounterInterface):
    """
    Interfuse to enable using a triggerable camera as a counting device

    This interfuse connects the ODMR logic with a slowcounter and a microwave
    device.
    """

    _modclass = 'ODMRCounterCameraInterfuse'
    _modtype = 'interfuse'

    photon_detector = Connector(interface='IxonUltra')
    clocked_trigger = Connector(interface='NationalInstrumentsClockedTrigger')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module."""
        self._counting_device = self.photon_detector()
        self._ctrigger_device = self.clocked_trigger()  # slow counter device

    def on_deactivate(self):
        pass

    ### ODMR counter interface commands

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        return self._ctrigger_device.set_up_odmr_clock(clock_frequency=clock_frequency,
                                                       clock_channel=clock_channel)

    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """ Configures the actual counter with a given clock.

        @param str counter_channel: if defined, this is the physical channel of
                                    the counter
        @param str photon_source: if defined, this is the physical channel where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str odmr_trigger_channel: if defined, this specifies the trigger
                                         output for the microwave

        @return int: error code (0:OK, -1:error)
        """

        ret_val1 = self._ctrigger_device.set_up_trigger()
        ret_val2 = self._counting_device.set_up_counter()

        # sanity check so that counter down time is not
        # longer than time between triggers

        #TODO: get clock frequency through interface function as
        #      there is no way to ensure that physical values have the same
        #      attribute name across modules in qudi.
        trigger_interval = 1/self._ctrigger_device._clock_frequency
        if trigger_interval < self._counting_device.get_down_time():
            self.log.warning('washing out information by triggering faster than counter can count')

        if ret_val1 != 0:
            self.log.error('the clocked trigger could not be set up')
        if ret_val2 != 0:
            self.log.error('the counter could not be set up')
        return ret_val1 | ret_val2

    def set_odmr_length(self, length=100):
        """Set up the trigger sequence for the ODMR and the triggered microwave.

        @param int length: length of microwave sweep in pixel

        @return int: error code (0:OK, -1:error)
        """
        # might need call to DAQmxCfgImplicitTiming here
        self._odmr_length = length
        return 0


    def count_odmr(self, length = 100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel

        @return float[]: the photon counts per second
        """
        # TODO: Figure out if clock needs to be stopped here or not.
        self.log.debug('in count odmr')
        data = self._counting_device.count_odmr(length)
        self.log.debug('data acquired')
        #self._ctrigger_device.set_up_odmr_clock(clock_frequency=self._ctrigger_device._clock_frequency)
        #self._ctrigger_device.set_up_trigger()
        #self.log.debug('trigger + clock started again')
        return data

    def close_odmr(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        ret_val = self._counting_device.stop_acquisition()
        ret_val = self._ctrigger_device.close_connection()
        return ret_val

    def close_odmr_clock(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self._ctrigger_device.close_clock()

    def get_odmr_channels(self):
        """ Return a list of channel names.

        @return list(str): channels recorded during ODMR measurement
        """
        return self._counting_device.get_counter_channels()