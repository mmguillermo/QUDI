# -*- coding: utf-8 -*-

"""
This file contains the Qudi Hardware module NICard class.

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
import re

import PyDAQmx as daq


from core.module import Base, ConfigOption

class NationalInstrumentsClockedTrigger(Base):
    """
    Experimental!
    For the moment no interface is defined for this module.
    """

    _modtype = 'NationalInstrumentsClockedTrigger'
    _modclass = 'hardware'

    _clock_channel = ConfigOption('clock_channel', missing='error')
    _default_clock_frequency = ConfigOption('default_clock_frequency', 100, missing='info')

    # odmr
    _odmr_trigger_channel = ConfigOption('odmr_trigger_channel', missing='error')

    _gate_in_channel = ConfigOption('gate_in_channel', missing='error')
    # number of readout samples, mainly used for gated counter
    _default_samples_number = ConfigOption('default_samples_number', 50, missing='info')
    # used as a default for expected maximum counts
    _max_counts = ConfigOption('max_counts', 3e7)
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', 10)
    _counting_edge_rising = ConfigOption('counting_edge_rising', True)

    def on_activate(self):
        """
        Starts up the NI Card at activation
        """
        self._clock_daq_task = None
        self._line_length = None
        self._odmr_length = None

    def on_deactivate(self):
        """
        Shut down the NI card
        """
        self.reset_hardware()

    def set_up_clock(self, clock_frequency=None, clock_channel=None, idle=False):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool idle: set whether idle situation of the counter (where
                          counter is doing nothing) is defined as
                                True  = 'Voltage High/Rising Edge'
                                False = 'Voltage Low/Falling Edge'

        @return int: error code (0:OK, -1:error)
        """
        # Create handle for task, this task will generate pulse signal for
        # photon counting
        my_clock_daq_task = daq.TaskHandle()

        # assign the clock frequency, if given
        if clock_frequency is not None:
            self._clock_frequency = float(clock_frequency)
        else:
            self._clock_frequency = self._default_clock_frequency

        # use the correct clock in this method
        my_clock_frequency = self._clock_frequency * 2

        # assign the clock channel, if given
        if clock_channel is not None:
            self._clock_channel = clock_channel
        # use the correct clock channel in this method
        my_clock_channel = self._clock_channel

        # Adjust the idle state if necessary
        my_idle = daq.DAQmx_Val_High if idle else daq.DAQmx_Val_Low
        try:
            # create task for clock
            task_name = 'CounterClock'
            daq.DAQmxCreateTask(task_name, daq.byref(my_clock_daq_task))

            # create a digital clock channel with specific clock frequency:
            daq.DAQmxCreateCOPulseChanFreq(
                # The task to which to add the channels
                my_clock_daq_task,
                # which channel is used?
                my_clock_channel,
                # Name to assign to task (NIDAQ uses by # default the physical channel name as
                # the virtual channel name. If name is specified, then you must use the name
                # when you refer to that channel in other NIDAQ functions)
                'Clock Producer',
                # units, Hertz in our case
                daq.DAQmx_Val_Hz,
                # idle state
                my_idle,
                # initial delay
                0,
                # pulse frequency, divide by 2 such that length of semi period = count_interval
                my_clock_frequency / 2,
                # duty cycle of pulses, 0.5 such that high and low duration are both
                # equal to count_interval
                0.5)

            # Configure Implicit Timing.
            # Set timing to continuous, i.e. set only the number of samples to
            # acquire or generate without specifying timing:
            daq.DAQmxCfgImplicitTiming(
                # Define task
                my_clock_daq_task,
                # Sample Mode: set the task to generate a continuous amount of running samples
                daq.DAQmx_Val_ContSamps,
                # buffer length which stores temporarily the number of generated samples
                1000)

            # actually start the preconfigured clock task
            daq.DAQmxStartTask(my_clock_daq_task)
            self._clock_daq_task = my_clock_daq_task
        except:
            self.log.exception('Error while setting up clock.')
            return -1
        return 0

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        return self.set_up_clock(
            clock_frequency=clock_frequency,
            clock_channel=clock_channel,
            idle=False)

    def set_up_trigger(self, clock_frequency=None, clock_channel=None):
        """ Connects the clock to an output terminal for triggering of
            external devices.

        @param string clock_channel: if defined, this specifies the clock for
                                     the counter
        @param string odmr_trigger_channel: if defined, this specifies the
                                            trigger output for the microwave

        @return int: error code (0:OK, -1:error)
        """
        # this task will give out triggers
        try:
            # start and stop pulse task to correctly initiate idle state high voltage.
            # daq.DAQmxStartTask(self._clock_daq_task)
            # otherwise, it will be low until task starts, and MW will receive wrong pulses.
            # daq.DAQmxStopTask(self._clock_daq_task)

            # connect the clock to the trigger channel to give triggers for the
            # microwave
            daq.DAQmxConnectTerms(
                self._clock_channel + 'InternalOutput',
                self._odmr_trigger_channel,
                daq.DAQmx_Val_DoNotInvertPolarity)
        except:
            self.log.exception('Error while setting up ODMR scan.')
            return -1
        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             should be used to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """

        my_task = self._clock_daq_task
        try:
            # Stop the clock task:
            daq.DAQmxStopTask(my_task)

            # After stopping delete all the configuration of the clock:
            daq.DAQmxClearTask(my_task)

            # Set the task handle to None as a safety
            self._clock_daq_task = None
        except:
            self.log.exception('Could not close clock.')
            return -1
        return 0

    def close_connection(self):
        """ Closes the odmr and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        try:
            # disconnect the trigger channel
            daq.DAQmxDisconnectTerms(
                self._clock_channel + 'InternalOutput',
                self._odmr_trigger_channel)

        except:
            self.log.exception('Error while disconnecting ODMR clock channel.')
            retval = -1

        return retval


    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [
            self._odmr_trigger_channel,
            self._clock_channel,
            ]

        devicelist = []
        for channel in chanlist:
            if channel is None:
                continue
            match = re.match(
                '^/(?P<dev>[0-9A-Za-z\- ]+[0-9A-Za-z\-_ ]*)/(?P<chan>[0-9A-Za-z]+)',
                channel)
            if match:
                devicelist.append(match.group('dev'))
            else:
                self.log.error('Did not find device name in {0}.'.format(channel))
        for device in set(devicelist):
            self.log.info('Reset device {0}.'.format(device))
            try:
                daq.DAQmxResetDevice(device)
            except:
                self.log.exception('Could not reset NI device {0}'.format(device))
                retval = -1
        return retval

    # adding manual switch to test the setup
    def digital_channel_switch(self, channel_name, mode=True):
        """
        Switches on or off the voltage output (5V) of one of the digital channels, that
        can as an example be used to switch on or off the AOM driver or apply a single
        trigger for ODMR.
        @param str channel_name: Name of the channel which should be controlled
                                    for example ('/Dev1/PFI9')
        @param bool mode: specifies if the voltage output of the chosen channel should be turned on or off

        @return int: error code (0:OK, -1:error)
        """
        if channel_name == None:
            self.log.error('No channel for digital output specified')
            return -1
        else:

            self.digital_out_task = daq.TaskHandle()
            if mode:
                self.digital_data = daq.c_uint32(0xffffffff)
            else:
                self.digital_data = daq.c_uint32(0x0)
            self.digital_read = daq.c_int32()
            self.digital_samples_channel = daq.c_int32(1)
            daq.DAQmxCreateTask('DigitalOut', daq.byref(self.digital_out_task))
            daq.DAQmxCreateDOChan(self.digital_out_task, channel_name, "", daq.DAQmx_Val_ChanForAllLines)
            daq.DAQmxStartTask(self.digital_out_task)
            daq.DAQmxWriteDigitalU32(self.digital_out_task, self.digital_samples_channel, True,
                                        self._RWTimeout, daq.DAQmx_Val_GroupByChannel,
                                        np.array(self.digital_data), self.digital_read, None);

            daq.DAQmxStopTask(self.digital_out_task)
            daq.DAQmxClearTask(self.digital_out_task)
            return 0


