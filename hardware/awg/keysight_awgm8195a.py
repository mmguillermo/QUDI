# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the AWG M8195A device.

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

import os
import visa
import numpy as np

from core.module import Base, ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints

class AWGM8195A(Base, PulserInterface):
    """ The hardware class to control Keysight AWG M8195. """

    _modclass = 'awgm8195'
    _modtype = 'hardware'

    # config options
    visa_address = ConfigOption(name='awg_visa_address', missing='error')
    awg_timeout = ConfigOption(name='awg_timeout', default=10, missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        config = self.getConfiguration()

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']
            if not os.path.exists(self.pulsed_file_dir):
                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directory defined in parameter '
                                 '"pulsed_file_dir" in the config for '
                                 'AWGM8195A class does not exist!\n'
                                 'The default home directory\n{0}\n will '
                                 'be taken instead.'
                                 ''.format(self.pulsed_file_dir))
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No parameter "pulsed_file_dir" was specified '
                             'in the config for AWGM8195A class as '
                             'directory for the pulsed files!\nThe '
                             'default home directory\n{0}\nwill be taken '
                             'instead.'.format(self.pulsed_file_dir))

        self.host_waveform_directory = self._get_dir_for_name('sampled_hardware_files')

        self.connected = False

        self._rm = visa.ResourceManager()
        if self.visa_address not in self._rm.list_resources():
            self.log.error('VISA address "{0}" not found by the pyVISA '
                           'resource manager.\nCheck the connection by using '
                           'for example "Agilent Connection Expert".'
                           ''.format(self.visa_address))
        else:
            self.awg = self._rm.open_resource(self.visa_address)
            # Set data transfer format (datatype, is_big_endian, container)
            self.awg.values_format.use_binary('f', False, np.array)

            self.awg.timeout = self.awg_timeout*1000 # should be in ms

            self.connected = True

        self.sample_rate = self.get_sample_rate()
        self.amplitude_list, self.offset_list = self.get_analog_level()
        self.markers_low, self.markers_high = self.get_digital_level()
        self.is_output_enabled = self._is_output_on()
        self.use_sequencer = self.has_sequence_mode()
        self.active_channel = self.get_active_channels()
        self.interleave = self.get_interleave()
        self.current_loaded_asset = ''
        self._init_loaded_asset()
        self.current_status = 0


    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module. """

        try:
            self.awg.close()
        except:
            self.log.warning('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')
        self.connected = False





"""
Discussion about sampling the waveform for the AWG. This text will move 
eventually to the sampling method, but will stay for the initial start of the
implementation in this file.

The information for the file format are taken from the Keysight M8195 user 
manual, from section 6.21.10 (p. 247), to be found here:

http://literature.cdn.keysight.com/litweb/pdf/M8195-91040.pdf?id=2678487


We will choose the native file format for the M8195 series with is called BIN8:

It is a binary file format (written in small endian), representing an 8bit 
integer and expressing a real value (not complex for iq modulation).

8bit are for each single channel only and contain no parameter header and no
data header. Excerpt from the manual:

BIN8
is the most memory efficient file format for the M8195A without digital markers. 
As a result, the fastest file download can be achieved.
One file contains waveform samples for one channel. The waveform samples can be 
imported to any of the four M8195A channels. Samples consist of binary int8 
values:


   7   |   6   |   5   |   4   |   3   |   2   |   1   |   0   |
----------------------------------------------------------------
  DB7  | DB6   |  DB5  |  DB4  |  DB3  |  DB2  |  DB1  |  DB0  |

DB = Data bit

so to convert a number to a 8bit representation you have to know the amplitude
range. Here it will be -0.5 V to +0.5 V, so 1Vpp. Therefore -0.5V corresponds to
0 and +0.5V to 255 (since 2^8=256). Hence the conversion is done in the 
following way:

x = float number between -0.5V and +0.5V to be converted to int8:

    int8((x + 0.5)*255)

or of an array:

    x_bin = ((x + 0.5)*255).astype('int8')

"""