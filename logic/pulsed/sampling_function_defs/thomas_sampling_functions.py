# -*- coding: utf-8 -*-

"""
This file contains the Qudi file with all default sampling functions.

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
from collections import OrderedDict
from logic.pulsed.sampling_functions import SamplingBase


class Opt_Control(SamplingBase):
    """
    Object representing an optimized pulse element
    """
    params = OrderedDict()
    params['name'] = {'init': '', 'type': str}
    params['use_fm'] = {'init': False, 'type': bool}
    params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': 100, 'type': float}
    params['Time_2_pi'] = {'unit': 's', 'init': 0.0000001, 'min': 0, 'max': 100, 'type': float}
    params['max_voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': +np.inf, 'type': float}

    def __init__(self, name=None, use_fm=None, frequency=None, phase=None, voltage=None, Time_2_pi=None,
                 max_voltage=None):
        if name is None:
            self.name = self.params['name']['init']
        else:
            self.name = name
        if use_fm is None:
            self.use_fm = self.params['use_fm']['init']
        else:
            self.use_fm = use_fm
        if frequency is None:
            self.frequency = self.params['frequency']['init']
        else:
            self.frequency = frequency
        if phase is None:
            self.phase = self.params['phase']['init']
        else:
            self.phase = phase
        if voltage is None:
            self.voltage = self.params['voltage']['init']
        else:
            self.voltage = voltage
        if Time_2_pi is None:
            self.Time_2_pi = self.params['Time_2_pi']['init']
        else:
            self.Time_2_pi = Time_2_pi
        if max_voltage is None:
            self.max_voltage = self.params['max_voltage']['init']
        else:
            self.max_voltage = max_voltage
        return


    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def round_sig(self, value, sig=6, small_value=1.0e-12):
        return round(value, sig - int(np.floor(np.log10(max(abs(value), abs(small_value))))) - 1)

    def get_samples(self, time_array):
        phase_rad = np.pi * self.phase / 180
        # conversion for AWG to actually output the specified voltage (factor two because of AWG), other factor two
        # comes from Rabi probability for transition
        voltage_factor = 2 * self.voltage * self.Time_2_pi
        time = time_array
        bins = len(time_array)
        pulse_time = 10e-9
        guess_amplitude = 0

        path = 'logic/pulsed/sampling_function_defs/optimal_control/'

        try:
            pulse_params = np.loadtxt(path + self.name + '.txt')
        except:
            pulse_params = np.loadtxt(path + 'default_params.txt')
            # print('The file does not exist!')
            self.log.error('The parameters file of the optimized pulse does not exist or could not be loaded! '
                           '\nDefault parameters loaded')

        try:
            if isinstance(pulse_params[0], float):
                pulse_time = pulse_params[0]
                guess_amplitude = pulse_params[1]
                am_amplitudes = [pulse_params[2]]
                am_frequencies = [pulse_params[3]]
                am_phases = [pulse_params[4]]
                fm_amplitudes = [pulse_params[5]]
                fm_frequencies = [pulse_params[6]]
                fm_phases = [pulse_params[7]]
                acceptance = [pulse_params[8]]
            else:
                pulse_time = pulse_params[0][0]
                guess_amplitude = pulse_params[1][0]
                am_amplitudes = pulse_params[2]
                am_frequencies = pulse_params[3]
                am_phases = pulse_params[4]
                fm_amplitudes = pulse_params[5]
                fm_frequencies = pulse_params[6]
                fm_phases = pulse_params[7]
                acceptance = pulse_params[8]
        except:
            am_frequencies = [0, 0]
            am_amplitudes = [0, 0]
            am_phases = [0, 0]
            fm_amplitudes = [0, 0]
            fm_frequencies = [0, 0]
            fm_phases = [0, 0]
            acceptance = [0, 0]
            # print('The file does not have the correct format!')
            self.log.error('The parameters file of the optimized pulse does not have the correct format! '
                           '\nDefault parameters loaded')

        adaption_factor = pulse_time / (time[-1] - time[0])

        # to make sure the pulse amplitude looks like the optimized one, i.e. time start at zero
        correction_time = np.linspace(0, pulse_time, bins)

        am_correction = np.array([1.0] * bins)
        fm_correction = np.array([1.0] * bins)

        for i in range(0, len(am_amplitudes)):
            if acceptance[i] == 1:
                am_correction += self._get_sine(correction_time, am_amplitudes[i], am_frequencies[i], am_phases[i])
                if self.use_fm is True:
                    fm_correction += self._get_sine(correction_time, fm_amplitudes[i], fm_frequencies[i], fm_phases[i])

        carrier_frequency = np.array([self.frequency] * bins) * fm_correction

        ## Here one can select if only amplitude without carrier freq is generated for testing
        pulse = self._get_sine(time, guess_amplitude, carrier_frequency, phase_rad)
        # pulse = np.array([guess_amplitude]*bins)

        opt_pulse = pulse * am_correction * adaption_factor * voltage_factor

        pulse_max = abs(max(opt_pulse, key=abs))

        # factor 2 because needed for AWG
        # pulse should not have higher amplitude than 101% of max. amplitude
        if pulse_max > self.max_voltage * 2 * 1.01:
            opt_pulse = opt_pulse / pulse_max * self.max_voltage * 2
            new_time = pulse_max * (time_array[-1] - time_array[0]) / (2 * self.max_voltage)
            self.log.error('Maximum voltage exceeded during pulse! \nSet pulse length to at least {0} s'.format(
                self.round_sig(new_time, 3)))

        ################################
        ## JUST FOR CHECKING
        # import matplotlib.pyplot as plt
        # fig = plt.figure(figsize=(11, 7))
        # ax = fig.add_subplot(111)
        # plt.subplots_adjust(bottom=0.15, top=0.97, right=0.98, left=0.1)
        #
        # plt.plot(time, opt_pulse, color='Darkblue', linewidth=1.5, zorder=5)
        # plt.grid(True, which="both")
        # plt.show()
        ################################

        return opt_pulse







class Pi_X_Pulse(SamplingBase):
    """
    Object representing a pi pulse with predefined length
    """

    from enum import Enum

    class Area(Enum):
        pi_half = 1
        pi = 2
        pi_three_half = 3

    params = OrderedDict()
    params['area'] = {'init': Area.pi, 'type': Area}
    params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
    params['phase'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
    params['voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': 100, 'type': float}
    params['Time_2_pi'] = {'unit': 's', 'init': 0.0000001, 'min': 0, 'max': 100, 'type': float}
    params['max_voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': +np.inf, 'type': float}

    def __init__(self, area=None, frequency=None, phase=None, voltage=None, Time_2_pi=None, max_voltage=None):
        if area is None:
            self.area = self.params['area']['init']
        else:
            self.area = area
        if frequency is None:
            self.frequency = self.params['frequency']['init']
        else:
            self.frequency = frequency
        if phase is None:
            self.phase = self.params['phase']['init']
        else:
            self.phase = phase
        if voltage is None:
            self.voltage = self.params['voltage']['init']
        else:
            self.voltage = voltage
        if Time_2_pi is None:
            self.Time_2_pi = self.params['Time_2_pi']['init']
        else:
            self.Time_2_pi = Time_2_pi
        if max_voltage is None:
            self.max_voltage = self.params['max_voltage']['init']
        else:
            self.max_voltage = max_voltage
        return


    @staticmethod
    def _get_sine(time_array, amplitude, frequency, phase):
        samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
        return samples_arr

    def round_sig(self, value, sig=6, small_value=1.0e-12):
        return round(value, sig - int(np.floor(np.log10(max(abs(value), abs(small_value))))) - 1)

    def get_samples(self, time_array):
        phase_rad = np.pi * self.phase / 180

        pulse_area = np.pi

        if self.area.value is 1:
            pulse_area = np.pi/2
        elif self.area.value is 2:
            pulse_area = np.pi
        elif self.area.value is 3:
            pulse_area = np.pi*3/2

        pulse_time_factor = pulse_area / (2 * np.pi)

        amplitude = self.voltage * 2

        pulse_time = self.Time_2_pi * pulse_time_factor

        adaption_factor = pulse_time / (time_array[-1] - time_array[0])

        ## Here one can select if only amplitude without carrier freq is generated for testing
        pulse = self._get_sine(time_array, amplitude, self.frequency, phase_rad)
        # pulse = np.array([guess_amplitude]*bins)

        pulse = pulse * adaption_factor

        pulse_max = abs(max(pulse, key=abs))

        # factor 2 because needed for AWG
        # pulse should not have higher amplitude than 101% of max. amplitude
        if pulse_max > self.max_voltage * 2 * 1.01:
            pulse = pulse / pulse_max * self.max_voltage * 2
            new_time = pulse_max * (time_array[-1] - time_array[0]) / (2 * self.max_voltage)
            self.log.error('Maximum voltage exceeded during pulse! \nSet pulse length to at least {0} s'.format(
                self.round_sig(new_time, 3)))

        ################################
        ## JUST FOR CHECKING
        # import matplotlib.pyplot as plt
        # fig = plt.figure(figsize=(11, 7))
        # ax = fig.add_subplot(111)
        # plt.subplots_adjust(bottom=0.15, top=0.97, right=0.98, left=0.1)
        #
        # plt.plot(time_array, pulse, color='Darkblue', linewidth=1.5, zorder=5)
        # plt.grid(True, which="both")
        # plt.show()
        ################################

        return pulse




#
#
# class Pi_Pulse(SamplingBase):
#     """
#     Object representing a pi pulse with predefined length
#     """
#     pulse_area = np.pi
#
#     pulse_time_factor = pulse_area / (2 * np.pi)
#
#     params = OrderedDict()
#     params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
#     params['phase'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
#     params['voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': 100, 'type': float}
#     params['Time_2_pi'] = {'unit': 's', 'init': 0.0000001, 'min': 0, 'max': 100, 'type': float}
#     params['max_voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': +np.inf, 'type': float}
#
#     def __init__(self, frequency=None, phase=None, voltage=None, Time_2_pi=None, max_voltage=None):
#         if frequency is None:
#             self.frequency = self.params['frequency']['init']
#         else:
#             self.frequency = frequency
#         if phase is None:
#             self.phase = self.params['phase']['init']
#         else:
#             self.phase = phase
#         if voltage is None:
#             self.voltage = self.params['voltage']['init']
#         else:
#             self.voltage = voltage
#         if Time_2_pi is None:
#             self.Time_2_pi = self.params['Time_2_pi']['init']
#         else:
#             self.Time_2_pi = Time_2_pi
#         if max_voltage is None:
#             self.max_voltage = self.params['max_voltage']['init']
#         else:
#             self.max_voltage = max_voltage
#         return
#
#
#     @staticmethod
#     def _get_sine(time_array, amplitude, frequency, phase):
#         samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
#         return samples_arr
#
#     def round_sig(self, value, sig=6, small_value=1.0e-12):
#         return round(value, sig - int(np.floor(np.log10(max(abs(value), abs(small_value))))) - 1)
#
#     def get_samples(self, time_array):
#         phase_rad = np.pi * self.phase / 180
#
#         # conversion for AWG to actually output the specified voltage (factor two because of AWG), other factor two
#         # comes from Rabi probability for transition
#         # voltage_factor = 2 * self.voltage * self.Time_2_pi / 2
#
#         amplitude = self.voltage * 2
#
#         pulse_time = self.Time_2_pi * self.pulse_time_factor
#
#         adaption_factor = pulse_time / (time_array[-1] - time_array[0])
#
#         ## HIER RICHTIG AUSWAEHLEN, OB NUR AMPLITUDE ODER GANZER PULS
#         pulse = self._get_sine(time_array, amplitude, self.frequency, phase_rad)
#         # pulse = np.array([guess_amplitude]*bins)
#
#         pulse = pulse * adaption_factor
#
#         pulse_max = abs(max(pulse, key=abs))
#
#         # factor 2 because needed for AWG ?
#         if pulse_max > self.max_voltage * 2:
#             new_time = pulse_max * (time_array[-1] - time_array[0]) / (2 * self.max_voltage)
#             self.log.error('Maximum voltage exceeded during pulse! \nSet pulse length to at least {0} s'.format(
#                 self.round_sig(new_time, 3)))
#
#         ################################
#         ## JUST FOR CHECKING
#         # import matplotlib.pyplot as plt
#         # fig = plt.figure(figsize=(11, 7))
#         # ax = fig.add_subplot(111)
#         # plt.subplots_adjust(bottom=0.15, top=0.97, right=0.98, left=0.1)
#         #
#         # plt.plot(time_array, pulse, color='Darkblue', linewidth=1.5, zorder=5)
#         # plt.grid(True, which="both")
#         # plt.show()
#         ################################
#
#         # np.savetxt('Pulse_qudi.txt', (pulse * correction), fmt='%s')
#
#         return pulse
#
#
#
#
#
#
# class Pi_half_Pulse(SamplingBase):
#     """
#     Object representing a pi half pulse with predefined length
#     """
#     pulse_area = np.pi/2
#
#     pulse_time_factor = pulse_area / (2 * np.pi)
#
#     params = OrderedDict()
#     params['frequency'] = {'unit': 'Hz', 'init': 2.87e9, 'min': 0.0, 'max': np.inf, 'type': float}
#     params['phase'] = {'unit': '°', 'init': 0.0, 'min': -360, 'max': 360, 'type': float}
#     params['voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': 100, 'type': float}
#     params['Time_2_pi'] = {'unit': 's', 'init': 0.0000001, 'min': 0, 'max': 100, 'type': float}
#     params['max_voltage'] = {'unit': 'V', 'init': 1.0, 'min': 0, 'max': +np.inf, 'type': float}
#
#     def __init__(self, frequency=None, phase=None, voltage=None, Time_2_pi=None, max_voltage=None):
#         if frequency is None:
#             self.frequency = self.params['frequency']['init']
#         else:
#             self.frequency = frequency
#         if phase is None:
#             self.phase = self.params['phase']['init']
#         else:
#             self.phase = phase
#         if voltage is None:
#             self.voltage = self.params['voltage']['init']
#         else:
#             self.voltage = voltage
#         if Time_2_pi is None:
#             self.Time_2_pi = self.params['Time_2_pi']['init']
#         else:
#             self.Time_2_pi = Time_2_pi
#         if max_voltage is None:
#             self.max_voltage = self.params['max_voltage']['init']
#         else:
#             self.max_voltage = max_voltage
#         return
#
#
#     @staticmethod
#     def _get_sine(time_array, amplitude, frequency, phase):
#         samples_arr = amplitude * np.sin(2 * np.pi * frequency * time_array + phase)
#         return samples_arr
#
#     def round_sig(self, value, sig=6, small_value=1.0e-12):
#         return round(value, sig - int(np.floor(np.log10(max(abs(value), abs(small_value))))) - 1)
#
#     def get_samples(self, time_array):
#         phase_rad = np.pi * self.phase / 180
#
#         # conversion for AWG to actually output the specified voltage (factor two because of AWG), other factor two
#         # comes from Rabi probability for transition
#         # voltage_factor = 2 * self.voltage * self.Time_2_pi / 2
#
#         amplitude = self.voltage * 2
#
#         pulse_time = self.Time_2_pi * self.pulse_time_factor
#
#         adaption_factor = pulse_time / (time_array[-1] - time_array[0])
#
#         ## HIER RICHTIG AUSWAEHLEN, OB NUR AMPLITUDE ODER GANZER PULS
#         pulse = self._get_sine(time_array, amplitude, self.frequency, phase_rad)
#         # pulse = np.array([guess_amplitude]*bins)
#
#         pulse = pulse * adaption_factor
#
#         pulse_max = abs(max(pulse, key=abs))
#
#         # factor 2 because needed for AWG ?
#         if pulse_max > self.max_voltage * 2:
#             new_time = pulse_max * (time_array[-1] - time_array[0]) / (2 * self.max_voltage)
#             self.log.error('Maximum voltage exceeded during pulse! \nSet pulse length to at least {0} s'.format(
#                 self.round_sig(new_time, 3)))
#
#         ################################
#         ## JUST FOR CHECKING
#         # import matplotlib.pyplot as plt
#         # fig = plt.figure(figsize=(11, 7))
#         # ax = fig.add_subplot(111)
#         # plt.subplots_adjust(bottom=0.15, top=0.97, right=0.98, left=0.1)
#         #
#         # plt.plot(time_array, pulse, color='Darkblue', linewidth=1.5, zorder=5)
#         # plt.grid(True, which="both")
#         # plt.show()
#         ################################
#
#         # np.savetxt('Pulse_qudi.txt', (pulse * correction), fmt='%s')
#
#         return pulse
#
