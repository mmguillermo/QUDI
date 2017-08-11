# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module for the Tektronix DTG 5334.

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

import ctypes
from collections import OrderedDict
import numpy as np
import os
import time
import visa

from interface.pulser_interface import PulserInterface, PulserConstraints
from core.module import Base, ConfigOption


class DTG5334(Base, PulserInterface):
    """
        Tektronix DTG 5334
    """
    _modclass = 'dtg5334'
    _modtype = 'hardware'

    visa_address = ConfigOption('visa_address', missing='error')

    ch_map = {
        'd_ch1': ('A', 1),
        'd_ch2': ('A', 2),
        'd_ch3': ('B', 1),
        'd_ch4': ('B', 2),
        'd_ch5': ('C', 1),
        'd_ch6': ('C', 2),
        'd_ch7': ('D', 1),
        'd_ch8': ('D', 2)
    }

    stb_values = {
        0: 'Wat'
    }

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.current_loaded_asset = ''
        config = self.getConfiguration()

        if 'pulsed_file_dir' in config.keys():
            self.pulsed_file_dir = config['pulsed_file_dir']
            if not os.path.exists(self.pulsed_file_dir):
                homedir = self.get_home_dir()
                self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
                self.log.warning('The directory defined in parameter "pulsed_file_dir" in the '
                                 'config for SequenceGeneratorLogic class does not exist!\n'
                                 'The default home directory\n{0}\n will be taken instead.'
                                 ''.format(self.pulsed_file_dir))
        else:
            homedir = self.get_home_dir()
            self.pulsed_file_dir = os.path.join(homedir, 'pulsed_files')
            self.log.warning('No parameter "pulsed_file_dir" was specified in the config for '
                             'SequenceGeneratorLogic as directory for the pulsed files!\nThe '
                             'default home directory\n{0}\nwill be taken instead.'
                             ''.format(self.pulsed_file_dir))

        # connect to DTG
        self._rm = visa.ResourceManager()

        if self.visa_address not in self._rm.list_resources():
            self.log.error('VISA address "{0}" not found by the pyVISA resource manager.\nCheck '
                           'the connection by using for example "Agilent Connection Expert".'
                           ''.format(self.visa_address))
        else:
            self.dtg = self._rm.open_resource(self.visa_address)
            # Set data transfer format (datatype, is_big_endian, container)
            self.dtg.values_format.use_binary('f', False, np.array)
            # set timeout by default to 15 sec
            self.dtg.timeout = 15000

        self.connected = True

        self._mfg, self._model, self._serial, self._fw = self._get_id()
        self.log.debug('Found the following model: {0}'.format(self._model))

        self.sample_rate = self.get_sample_rate()
        self.amplitude_list, self.offset_list = self.get_analog_level()
        self.markers_low, self.markers_high = self.get_digital_level()
        self.is_output_enabled = self._is_output_on()
        self.use_sequencer = self.has_sequence_mode()
        self.active_channel = self.get_active_channels()
        self.interleave = self.get_interleave()
        self.current_loaded_asset = ''
        self.current_status = 0

    def on_deactivate(self):
        """ Required tasks to be performed during deactivation of the module.
        """
        # Closes the connection to the DTG
        try:
            self.dtg.close()
        except:
            self.log.debug('Closing DTG connection using pyvisa failed.')
        self.log.info('Closed connection to DTG')
        self.connected = False
        return

    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude, total_length_bins,
        channel_config, ...) related to the pulse generator hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to get an impression.
        If still additional constraints are needed, then they have to be added to the
        PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in cor.util.interfaces.
        Essentially it contains min/max values as well as min step size, default value and unit of
        the parameter.

        PulserConstraints.activation_config differs, since it contain the channel
        configuration/activation information of the form:
            {<descriptor_str>: <channel_list>,
             <descriptor_str>: <channel_list>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because it might have no
        sequence mode) just leave it out so that the default is used (only zeros).
        """
        # Example for configuration with default values:
        constraints = PulserConstraints()

        # The file formats are hardware specific.
        constraints.waveform_format = ['dtg']
        constraints.sequence_format = ['seq']

        constraints.sample_rate.min = 50e3
        constraints.sample_rate.max = 3.35e9
        constraints.sample_rate.step = 1e3
        constraints.sample_rate.default = 12.0e9

        constraints.a_ch_amplitude.min = 0.0
        constraints.a_ch_amplitude.max = 0.0
        constraints.a_ch_amplitude.step = 0.0
        constraints.a_ch_amplitude.default = 0.0

        constraints.a_ch_offset.min = 0.0
        constraints.a_ch_offset.max = 0.0
        constraints.a_ch_offset.step = 0.0
        constraints.a_ch_offset.default = 0.0

        constraints.d_ch_low.min = -2.0
        constraints.d_ch_low.max = 2.44
        constraints.d_ch_low.step = 0.05
        constraints.d_ch_low.default = 0.0

        constraints.d_ch_high.min = -1.0
        constraints.d_ch_high.max = 2.47
        constraints.d_ch_high.step = 0.05
        constraints.d_ch_high.default = 2.4

        constraints.sampled_file_length.min = 80
        constraints.sampled_file_length.max = 64800000
        constraints.sampled_file_length.step = 1
        constraints.sampled_file_length.default = 80

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 32000
        constraints.waveform_num.step = 1
        constraints.waveform_num.default = 1

        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 8000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        constraints.subsequence_num.min = 1
        constraints.subsequence_num.max = 4000
        constraints.subsequence_num.step = 1
        constraints.subsequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65539
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        constraints.trigger_in.min = 0
        constraints.trigger_in.max = 2
        constraints.trigger_in.step = 1
        constraints.trigger_in.default = 0

        constraints.event_jump_to.min = 0
        constraints.event_jump_to.max = 8000
        constraints.event_jump_to.step = 1
        constraints.event_jump_to.default = 0

        constraints.go_to.min = 0
        constraints.go_to.max = 8000
        constraints.go_to.step = 1
        constraints.go_to.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe UNAMBIGUOUSLY the
        # channels. Here all possible channel configurations are stated, where only the generic
        # names should be used. The names for the different configurations can be customary chosen.
        activation_conf = OrderedDict()
        activation_conf['all'] = ['d_ch1', 'd_ch2', 'd_ch3', 'd_ch4', 'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8']
        constraints.activation_config = activation_conf
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('OUTP:STAT:ALL ON;*WAI')
        self.dtg.write('TBAS:RUN ON')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 1 else -1
        return state

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('OUTP:STAT:ALL OFF;*WAI')
        self.dtg.write('TBAS:RUN OFF')
        state = 0 if int(self.dtg.query('TBAS:RUN?')) == 0 else -1
        return state

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device mass memory.
            Also loads these files into the device workspace if present.
            Does NOT load waveforms/sequences/patterns into channels.

        @param asset_name: string, name of the ensemble/sequence to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.

        This method has no effect when using pulser hardware without own mass memory
        (i.e. PulseBlaster, FPGA)
        """
        return 0

    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing device.
        For devices that have a workspace (i.e. AWG) this will load the asset from the device
        workspace into the channel.
        For a device without mass memory this will transfer the waveform/sequence/pattern data
        directly to the device so that it is ready to play.

        @param str asset_name: The name of the asset to be loaded

        @param dict load_dict:  a dictionary with keys being one of the available channel numbers
                                and items being the name of the already sampled waveform/sequence
                                files.
                                Examples:   {1: rabi_Ch1, 2: rabi_Ch2}
                                            {1: rabi_Ch2, 2: rabi_Ch1}
                                This parameter is optional. If none is given then the channel
                                association is invoked from the file name, i.e. the appendix
                                (_ch1, _ch2 etc.)

        @return int: error code (0:OK, -1:error)
        """
        self.current_loaded_asset = asset_name
        return 0

    def get_loaded_asset(self):
        """ Retrieve the currently loaded asset name of the device.

        @return str: Name of the current asset ready to play. (no filename)
        """
        return self.current_loaded_asset

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('GROUP:DEL:ALL;*WAI')
        self.dtg.write('BLOC:DEL:ALL;*WAI')
        self.current_loaded_asset = ''
        return 0

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.
        """
        status = 0
        return status, self.stb_values

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        return float(self.dtg.query('TBAS:FREQ?'))

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        self.dtg.write('TBAS:FREQ {0:e}'.format(sample_rate))
        return self.get_sample_rate()

    def get_analog_level(self, amplitude=None, offset=None):
        """ Device has no analog channels.
        """
        return {}, {}

    def set_analog_level(self, amplitude=None, offset=None):
        """ Device has no analog channels.
        """
        return {}, {}

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If nothing (or None) is passed then the levels of all channels are being returned.
        If no digital channels are present, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {'d_ch1': 1.0, 'd_ch2': 1.0, 'd_ch3': 1.0, 'd_ch4': 4.0}
        Since no high request was performed, the high values for ALL channels are returned (here 4).

        The major difference to analog signals is that digital signals are either ON or OFF,
        whereas analog channels have a varying amplitude range. In contrast to analog output
        levels, digital output levels are defined by a voltage, which corresponds to the ON status
        and a voltage which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between (amplitude, offset) and
        (value high, value low)!
        """
        if low is None:
            low = self.get_constraints().activation_config['all']
        if high is None:
            high = self.get_constraints().activation_config['all']

        ch_low = {chan: float(self.dtg.query('PGEN{0}:CH{1}:LOW?'.format(*(self.ch_map[chan])))) for chan in low}
        ch_high = {chan: float(self.dtg.query('PGEN{0}:CH{1}:HIGH?'.format(*(self.ch_map[chan])))) for chan in high}

        return ch_high, ch_low

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.

        The major difference to analog signals is that digital signals are either ON or OFF,
        whereas analog channels have a varying amplitude range. In contrast to analog output
        levels, digital output levels are defined by a voltage, which corresponds to the ON status
        and a voltage which corresponds to the OFF status (both denoted in (absolute) voltage)

        In general there is no bijective correspondence between (amplitude, offset) and
        (value high, value low)!
        """
        if low is None:
            low = {}
        if high is None:
            high = {}

        for chan, level in low.items():
            gen, gen_ch = self.ch_map[chan]
            self.dtg.write('PGEN{0}:CH{1}:LOW {2}'.format(gen, gen_ch, level))

        for chan, level in high.items():
            gen, gen_ch = self.ch_map[chan]
            self.dtg.write('PGEN{0}:CH{1}:HIGH {2}'.format(gen, gen_ch, level))

        return self.get_digital_level()

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.

        Example for an possible input (order is not important):
            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']
        then the output might look like
            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True, 'd_ch1': False}

        If no parameter (or None) is passed to this method all channel states will be returned.
        """
        if ch is None:
            chan_list = self.get_constraints().activation_config['all']

        active_ch = {
            chan: int(self.dtg.query('PGEN{0}:CH{1}:OUTP?'.format(*(self.ch_map[chan])))) == 1 for chan in chan_list}

        return active_ch

    def set_active_channels(self, ch=None):
        """ Set the active channels for the pulse generator hardware.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and digital channels

        If nothing is passed then the command will simply return the unchanged current state.

        Note: After setting the active channels of the device,
              use the returned dict for further processing.

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1.

        The hardware itself has to handle, whether separate channel activation is possible.
        """
        for chan, state in ch.items():
            gen, gen_ch = self.ch_map[chan]
            b_state = 1 if state else 0
            self.dtg.write('PGEN{0}:CH{1}:OUTP {2}'.format(gen, gen_ch, b_state))

        return self.get_active_channels()

    def get_uploaded_asset_names(self):
        """ Retrieve the names of all uploaded assets on the device.

        @return list: List of all uploaded asset name strings in the current device directory.
                      This is no list of the file names.

        Unused for pulse generators without sequence storage capability (PulseBlaster, FPGA).
        """
        return []

    def get_saved_asset_names(self):
        """ Retrieve the names of all sampled and saved assets on the host PC. This is no list of
            the file names.

        @return list: List of all saved asset name strings in the current
                      directory of the host PC.
        """
        return []

    def delete_asset(self, asset_name):
        """ Delete all files associated with an asset with the passed asset_name from the device
            memory (mass storage as well as i.e. awg workspace/channels).

        @param str asset_name: The name of the asset to be deleted
                               Optionally a list of asset names can be passed.

        @return list: a list with strings of the files which were deleted.

        Unused for pulse generators without sequence storage capability (PulseBlaster, FPGA).
        """
        return[]

    def set_asset_dir_on_device(self, dir_path):
        """ Change the directory where the assets are stored on the device.

        @param str dir_path: The target directory

        @return int: error code (0:OK, -1:error)

        Unused for pulse generators without changeable file structure (PulseBlaster, FPGA).
        """
        return 0

    def get_asset_dir_on_device(self):
        """ Ask for the directory where the hardware conform files are stored on the device.

        @return str: The current file directory

        Unused for pulse generators without changeable file structure (i.e. PulseBlaster, FPGA).
        """
        return ''

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """
        return False

    def tell(self, command):
        """ Sends a command string to the device.

        @param string command: string containing the command

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write(command)

    def ask(self, question):
        """ Asks the device a 'question' and receive and return an answer from it.

        @param string question: string containing the command

        @return string: the answer of the device to the 'question' in a string
        """
        return self.dtg.query(question)

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        self.dtg.write('*RST')

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return True

    def _get_id(self):
        return self.dtg.query('*IDN?').replace('\n', '').split(',')

    def _is_output_on(self):
        return int(self.dtg.query('TBAS:RUN?')) == 1

    def direct_write_ensemble(self, ensemble_name, analog_samples, digital_samples):
        """
        @param ensemble_name: Name for the waveform to be created.
        @param analog_samples:  numpy.ndarray of type float32 containing the voltage samples.
        @param digital_samples: numpy.ndarray of type bool containing the marker states for each
                                sample.
                                First dimension is marker index; second dimension is sample number
        @return:
        """
        # check input
        if not ensemble_name:
            self.log.error('Please specify an ensemble name for direct waveform creation.')
            return -1

        if type(digital_samples).__name__ != 'ndarray':
            self.log.warning('Digital samples for direct waveform creation have wrong data type.\n'
                             'Converting to numpy.ndarray of type bool.')
            digital_samples = np.array(digital_samples, dtype=bool)

        min_samples = 960
        if digital_samples.shape[1] < min_samples:
            self.log.error('Minimum waveform length for DTG5334 series is {0} samples.\n'
                           'Direct waveform creation failed.'.format(min_samples))
            return -1

        # determine active channels
        activation_dict = self.get_active_channels()
        active_chnl = [chnl for chnl in activation_dict if activation_dict[chnl]]
        active_digital = [chnl for chnl in active_chnl if 'd_ch' in chnl]
        active_digital.sort()
        print(active_digital)

        # Sanity check of channel numbers
        if len(active_digital) != digital_samples.shape[0]:
            self.log.error(
                'Mismatch of channel activation and sample array dimensions for direct '
                'write.\nChannel activation is: {} digital.\n'
                'Sample arrays have: {} digital.'
                ''.format(len(active_digital), digital_samples.shape[0]))
            return -1

        self._block_new(ensemble_name, digital_samples.shape[1])
        print(self.dtg.query('BLOC:SEL?'))
        self._block_write(ensemble_name, digital_samples)
        self.current_loaded_asset = ensemble_name

    def _block_length(self, name):
        return int(self.dtg.query('BLOC:LENG? "{0}"'.format(name)))

    def _block_exists(self, name):
        return self._block_length(name) != -1

    def _block_delete(self, name):
        self.dtg.write('BLOC:DEL "{0}"'.format(name))

    def _block_new(self, name, length):
        if self._block_exists(name):
            self._block_delete(name)

        self.dtg.write('BLOC:NEW "{0}", {1}'.format(name, length))
        self.dtg.query('*OPC?')
        self.dtg.write('BLOC:SEL "{0}"'.format(name))
        self.dtg.query('*OPC?')

    def _block_write(self, name, digital_samples):
        self.dtg.write('BLOC:SEL "{0}"'.format(name))

        for ch, data in enumerate(digital_samples):
            self._channel_write('d_ch{0}'.format(ch + 1), data)

        self.dtg.query('*OPC?')

    def _channel_write(self, channel, data):
        c = self.ch_map[channel]
        max_blocksize = 1024 * 1024
        dlen = len(data)
        start = 0

        # when there is more than 1MB of data to transfer, split it up
        while dlen >= max_blocksize:
            end = start + max_blocksize
            datstr = ''.join(map(lambda x: str(int(x)), data[start:end]))
            print(channel, 'loop', dlen, len(datstr))
            self.dtg.write('PGEN{0}:CH{1}:DATA {2},{3},"{4}"'.format(
                c[0], c[1], start, end - start, datstr))
            dlen -= end - start
            start = end

        end = start + dlen
        datstr = ''.join(map(lambda x: str(int(x)), data[start:end]))
        print(channel, 'end', len(datstr))
        self.dtg.write('PGEN{0}:CH{1}:DATA {2},{3},"{4}"'.format(
            c[0], c[1], start, end - start, datstr))

    def direct_write_sequence(self, sequence_name, sequence_params):
        """
        @param sequence_name:
        @param sequence_params:

        @return:
        """
        num_steps = len(sequence_params)

        # Check if sequence already exists and delete if necessary.
        #if sequence_name in self._get_sequence_names_memory():
        #    self.dtg.write('BLOC:DEL "{0}"'.format(sequence_name))

        self._set_sequence_length(num_steps)
        for line_nr, param in enumerate(sequence_params):
            print(line_nr, param)
            self._set_sequence_line(
                line_nr,
                '{0}'.format(line_nr + 1),
                param['trigger_wait'],
                param['name'][0].rsplit('.')[0],
                param['repetitions'],
                param['event_jump_to'],
                param['go_to']
            )

        # Wait for everything to complete
        while int(self.dtg.query('*OPC?')) != 1:
            time.sleep(0.2)
        return 0

    def _get_sequence_line(self, line_nr):
        fields = self.dtg.query('SEQ:DATA? {0}'.format(line_nr)).split(', ')
        print(fields)
        label, trigger, block, repeat, jump, goto = fields
        return (
            label.strip('"'),
            int(trigger),
            block.strip('"'),
            int(repeat),
            jump.strip('"'),
            goto.strip('"')
        )

    def _set_sequence_line(self, line_nr, label, trigger, block, repeat, jump, goto):
        print(line_nr, label, trigger, block, repeat, jump, goto)
        self.dtg.write('SEQ:DATA {0}, "{1}", {2}, "{3}", {4}, "{5}", "{6}"'.format(
            line_nr, label, trigger, block, repeat, jump, goto
        ))

    def _get_sequence_length(self):
        return int(self.dtg.query('SEQ:LENG?'))

    def _set_sequence_length(self, length):
        self.dtg.write('SEQ:LENG {0}'.format(length))