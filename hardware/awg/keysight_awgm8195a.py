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
import time
import numpy as np
from collections import OrderedDict

from core.module import Base, ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints

class AWGM8195A(Base, PulserInterface):
    """ The hardware class to control Keysight AWG M8195.

    The referred manual used for this implementation:
        Keysight M8195A Arbitrary Waveform Generator Revision 2
    available here:
        http://literature.cdn.keysight.com/litweb/pdf/M8195-91040.pdf
    """

    _modclass = 'awgm8195a'
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

        # Sec. 6.2 in manual:
        # The recommended way to program the M8195A module is to use the IVI
        # drivers. See documentation of the IVI drivers how to program using
        # IVI drivers. The connection between the IVI-COM driver and the Soft
        # Front Panel is hidden. To address a module therefore the PXI or USB
        # resource string of the module is used. The IVI driver will connect to
        # an already running Soft Front Panel. If the Soft Front Panel is not
        # running, it will automatically start it.

        # Communicate via SCPI commands through the visa interface:
        # Sec. 6.3.1 in the manual:
        # Before sending SCPI commands to the instrument, the Soft Front Panel
        # (AgM8195SFP.exe) must be started. This can be done in the Windows
        # Start menu (Start > All Programs > Keysight M8195 >
        #             Keysight M8195 Soft Front Panel).
        #
        # Sec. 6.3.1.2 in the manual:
        #   - Socket port: 5025 (e.g. TCPIP0::localhost::5025::SOCKET)
        #   - Telnet port: 5024
        #   - HiSLIP: 0 (e.g. TCPIP0::localhost::hislip0::INSTR)
        #   -  VXI-11.3: 0 (e.g. TCPIP0::localhost::inst0::INSTR)



        self._rm = visa.ResourceManager()
        if self.visa_address not in self._rm.list_resources():
            self.log.error('VISA address "{0}" not found by the pyVISA '
                           'resource manager.\nCheck the connection by using '
                           'for example "Agilent Connection Expert".'
                           ''.format(self.visa_address))
        else:
            self._awg = self._rm.open_resource(self.visa_address)
            # Set data transfer format (datatype, is_big_endian, container)
            self._awg.values_format.use_binary('f', False, np.array)

            self._awg.timeout = self.awg_timeout*1000 # should be in ms

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
            self._awg.close()
        except:
            self.log.warning('Closing AWG connection using pyvisa failed.')
        self.log.info('Closed connection to AWG')
        self.connected = False


    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.

        @return constraints object: object with pulser constraints as attributes.

        Provides all the constraints (e.g. sample_rate, amplitude,
        total_length_bins, channel_config, ...) related to the pulse generator
        hardware to the caller.

            SEE PulserConstraints CLASS IN pulser_interface.py
            FOR AVAILABLE CONSTRAINTS!!!

        If you are not sure about the meaning, look in other hardware files to
        get an impression. If still additional constraints are needed, then
        they have to be added to the PulserConstraints class.

        Each scalar parameter is an ScalarConstraints object defined in
        cor.util.interfaces. Essentially it contains min/max values as well as
        min step size, default value and unit of the parameter.

        PulserConstraints.activation_config differs, since it contain the
        channel configuration/activation information of the form:
            {<descriptor_str>: <channel_list>,
             <descriptor_str>: <channel_list>,
             ...}

        If the constraints cannot be set in the pulsing hardware (e.g. because
        it might have no sequence mode) just leave it out so that the default
        is used (only zeros).
        """
        constraints = PulserConstraints()

        # The compatible file formats are hardware specific.
        constraints.waveform_format = ['bin8']

        if self._AWG_MODEL == 'M8195A':
            constraints.sample_rate.min = 53.76e9
            constraints.sample_rate.max = 65.0e9
            constraints.sample_rate.step = 1.0e7
            constraints.sample_rate.default = 65.00e9
        else:
            self.log.error('The current AWG model has no valid sample rate '
                           'constraints')

        constraints.a_ch_amplitude.min = 0.0375
        constraints.a_ch_amplitude.max = 0.5    # corresponds to 1Vpp
        constraints.a_ch_amplitude.step = 0.002 # actually 1Vpp/2^8=0.0019..
        constraints.a_ch_amplitude.default = 0.5

        # for now, no digital/marker channel.
        #FIXME: implement marker channel configuration.

        constraints.sampled_file_length.min = 128
        constraints.sampled_file_length.max = 2_000_000_000
        constraints.sampled_file_length.step = 128
        constraints.sampled_file_length.default = 128

        constraints.waveform_num.min = 1
        constraints.waveform_num.max = 16_000_000
        constraints.waveform_num.default = 1
        # The sample memory can be split into a maximum of 16 M waveform segments

        # FIXME: Check the proper number for your device
        constraints.sequence_num.min = 1
        constraints.sequence_num.max = 4000
        constraints.sequence_num.step = 1
        constraints.sequence_num.default = 1

        # If sequencer mode is available then these should be specified
        constraints.repetitions.min = 0
        constraints.repetitions.max = 65536
        constraints.repetitions.step = 1
        constraints.repetitions.default = 0

        # ToDo: Check how many external triggers are available
        constraints.trigger_in.min = 0
        constraints.trigger_in.max = 1
        constraints.trigger_in.step = 1
        constraints.trigger_in.default = 0

        # the name a_ch<num> and d_ch<num> are generic names, which describe
        # UNAMBIGUOUSLY the channels. Here all possible channel configurations
        # are stated, where only the generic names should be used. The names
        # for the different configurations can be customary chosen.
        activation_config = OrderedDict()
        if self._AWG_MODEL == 'M8195A':
            activation_config['all'] = ['a_ch1', 'a_ch2', 'a_ch3', 'a_ch4']
            #FIXME: this awg model supports more channel configuration!
            #       Implement those! But keep in mind that the format of the
            #       file might change for difference configurations.

        constraints.activation_config = activation_config

        # FIXME: additional constraint really necessary?
        constraints.dac_resolution = {'min': 8, 'max': 8, 'step': 1,
                                      'unit': 'bit'}
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """
        # Check if AWG is in function generator mode
        # self._activate_awg_mode()


        self._write(':OUTP1 ON')
        self._write(':OUTP2 ON')
        self._write(':OUTP3 ON')
        self._write(':OUTP4 ON')

        # Sec. 6.4 from manual:
        # In the program it is recommended to send the command for starting
        # data generation (:INIT:IMM) as the last command. This way
        # intermediate stop/restarts (e.g. when changing sample rate or
        # loading a waveform) are avoided and optimum execution performance is
        # achieved.

        self._write(':INIT:IMM')

        # wait until the AWG is actually running
        while not self._is_output_on():
            time.sleep(0.25)

        self.current_status = 1
        self.is_output_enabled = True
        return self.current_status

    def pulser_off(self):
        """ Switches the pulsing device off.

        @return int: error code (0:OK, -1:error, higher number corresponds to
                                 current status of the device. Check then the
                                 class variable status_dic.)
        """

        self._write(':OUTP1 OFF')
        self._write(':OUTP2 OFF')
        self._write(':OUTP3 OFF')
        self._write(':OUTP4 OFF')

        # wait until the AWG has actually stopped
        while self._is_output_on():
            time.sleep(0.25)
        self.current_status = 0
        self.is_output_enabled = False
        return self.current_status

    def upload_asset(self, asset_name=None):
        """ Upload an already hardware conform file to the device.
            Does NOT load it into channels.

        @param str name: name of the ensemble/sequence to be uploaded

        @return int: error code (0:OK, -1:error)

        If nothing is passed, method will be skipped.
        """
        # check input
        if asset_name is None:
            self.log.warning('No asset name provided for upload!\nCorrect that!\n'
                             'Command will be ignored.')
            return -1



        # select extended Memory Mode
        self._write(':TRAC1:MMOD EXT')
        self._write(':TRAC2:MMOD EXT')
        self._write(':TRAC3:MMOD EXT')
        self._write(':TRAC4:MMOD EXT')



        self._write(':TRAC1:DATA 1,0,{0}'.format(asset_name + '_ch1.bin8'))
        self._write(':TRAC2:DATA 1,0,{0}'.format(asset_name + '_ch2.bin8'))
        self._write(':TRAC3:DATA 1,0,{0}'.format(asset_name + '_ch3.bin8'))
        self._write(':TRAC4:DATA 1,0,{0}'.format(asset_name + '_ch4.bin8'))



        # self._activate_awg_mode()
        # at first delete all the name, which might lead to confusions in the upload procedure:
        self.delete_asset(asset_name)
        # determine which files to transfer
        filelist = self._get_filenames_on_host()
        upload_names = []
        for filename in filelist:
            if filename == asset_name + '.seq':
                upload_names.append(filename)
                break
            elif filename == asset_name + '.seqx':
                upload_names.append(filename)
                break
            elif fnmatch(filename, asset_name + '_ch?.wfm*'):
                upload_names.append(filename)
            elif fnmatch(filename, asset_name + '.wfm*'):
                upload_names.append(filename)
                break
            elif filename == asset_name + '.mat':
                upload_names.append(filename)
                break
        # Transfer files and load into AWG workspace
        for filename in upload_names:
            self._send_file(filename)
            file_path = os.path.join(self.ftp_root_directory, self.asset_directory, filename)
            if filename.endswith('.mat'):
                self.awg.write('MMEM:OPEN:SASS:WAV "{0}"'.format(file_path))
            else:
                self.awg.write('MMEM:OPEN "{0}"'.format(file_path))
            self.awg.query('*OPC?')
        # Wait for the loading to completed
        while int(self.awg.query('*OPC?')) != 1:
            time.sleep(0.2)
        return 0


    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing
            device.

        @param str asset_name: The name of the asset to be loaded

        @param dict load_dict:  a dictionary with keys being one of the
                                available channel numbers and items being the
                                name of the already sampled
                                waveform/sequence files.
                                Examples:   {1: rabi_ch1, 2: rabi_ch2}
                                            {1: rabi_ch2, 2: rabi_ch1}
                                This parameter is optional. If none is given
                                then the channel association is invoked from
                                the sequence generation,
                                i.e. the filename appendix (_ch1, _ch2 etc.)

        @return int: error code (0:OK, -1:error)

        Unused for digital pulse generators without sequence storage capability
        (PulseBlaster, FPGA).
        """



        self._write(':TRAC1:IMP 1,0,{0}'.format(asset_name + '_ch1.bin8'))
        self._write(':TRAC2:IMP 1,0,{0}'.format(asset_name + '_ch2.bin8'))
        self._write(':TRAC3:IMP 1,0,{0}'.format(asset_name + '_ch3.bin8'))
        self._write(':TRAC4:IMP 1,0,{0}'.format(asset_name + '_ch4.bin8'))



        # Get all sequence and waveform names currently loaded into AWG workspace
        seq_list = self._get_sequence_names_memory()
        wfm_list = self._get_waveform_names_memory()

        # Check if load_dict is None or an empty dict
        if not load_dict:
            # check if the desired asset is in workspace. Load to channels if that is the case.
            if asset_name in seq_list:
                trac_num = int(self.awg.query('SLIS:SEQ:TRAC? "{0}"'.format(asset_name)))
                for chnl in range(1, trac_num + 1):
                    self.awg.write('SOUR{0}:CASS:SEQ "{1}", {2}'.format(chnl, asset_name, chnl))
            # check if the desired asset is in workspace. Load to channels if that is the case.
            elif asset_name + '_ch1' in wfm_list:
                self.awg.write('SOUR1:CASS:WAV "{0}"'.format(asset_name + '_ch1'))
                if self._get_max_a_channel_number() > 1 and asset_name + '_ch2' in wfm_list:
                    self.awg.write('SOUR2:CASS:WAV "{0}"'.format(asset_name + '_ch2'))
            self.current_loaded_asset = asset_name
        else:
            self.log.error('Loading assets into user defined channels is not yet implemented.\n'
                           'In other words: The "load_dict" parameter of the "load_asset" method '
                           'is not handled yet.')

        # Wait for the loading to completed
        while int(self._ask('*OPC?')) != 1:
            time.sleep(0.2)
        return 0


################################################################################
###                         Non interface methods                            ###
################################################################################

    def _ask(self, question):
        """ Ask wrapper.

        @param str question: a question to the device

        @return: the received answer
        """
        return self._awg.query(question)

    def _write(self, cmd, wait=True):
        """ Write wrapper.

        @param str cmd: a command to the device
        @param bool wait: optional, is the wait statement should be skipped.

        @return: str: the statuscode of the write command.
        """

        statuscode = self._awg.write(cmd)
        if wait:
            self._awg.write('*WAI')
        return statuscode


    def _is_output_on(self):
        """
        Aks the AWG if the output is enabled, i.e. if the AWG is running

        @return: bool, (True: output on, False: output off)
        """

        # since output 4 was the last one to be set, assume that all other are
        # already set
        run_state = bool(int(self._ask(':OUTP4?')))
        return run_state

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