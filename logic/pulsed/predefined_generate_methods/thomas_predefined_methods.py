# -*- coding: utf-8 -*-

"""
This file contains the Qudi Predefined Methods for sequence generator

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
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase

"""
General Pulse Creation Procedure:
=================================
- Create at first each PulseBlockElement object
- add all PulseBlockElement object to a list and combine them to a
  PulseBlock object.
- Create all needed PulseBlock object with that idea, that means
  PulseBlockElement objects which are grouped to PulseBlock objects.
- Create from the PulseBlock objects a PulseBlockEnsemble object.
- If needed and if possible, combine the created PulseBlockEnsemble objects
  to the highest instance together in a PulseSequence object.
"""


class BasicPredefinedGenerator(PredefinedGeneratorBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    ################################################################################################
    #                             Generation methods for waveforms                                 #
    ################################################################################################
    def generate_optimal_control_test(self, name='opt_control_test', tau_start=10.0e-9, tau_step=10.0e-9,
                                      num_of_points_on_res=50, num_of_points_off_res=50, detuning_in_percent=0.0,
                                      pulse_length=50.0e-9, max_amplitude=1.0, file_name='default_params'):
        """
        Creates the measurement sequence used for fidelity evaluation of optimized pulses
        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        detuned_frequency = self.microwave_frequency*(1+detuning_in_percent/100)
        num_of_guess_pulses = 20
        num_of_opt_pulses = 20
        num_of_short_pulses = 20
        max_ampl_factor = 3

        number_of_lasers = num_of_points_on_res + num_of_points_off_res + num_of_guess_pulses + num_of_short_pulses  + num_of_opt_pulses

        # get tau array for measurement ticks
        num_of_points = num_of_points_on_res + num_of_points_off_res + num_of_guess_pulses + num_of_short_pulses  + num_of_opt_pulses
        tau_array = tau_start + np.arange(num_of_points) * tau_step

        # create the laser_mw elements
        mw_element_on_res = self._get_mw_element(length=tau_start,
                                                 increment=tau_step,
                                                 amp=self.microwave_amplitude,
                                                 freq=self.microwave_frequency,
                                                 phase=0)

        mw_element_off_res = self._get_mw_element(length=tau_start,
                                                  increment=tau_step,
                                                  amp=self.microwave_amplitude,
                                                  freq=detuned_frequency,
                                                  phase=0)

        waiting_element = self._get_idle_element(length=self.wait_time,
                                                 increment=0)

        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)

        delay_element = self._get_delay_gate_element()

        guess_pulse_element = self._get_pi_X_pulse_element(length=pulse_length,
                                                           freq=detuned_frequency,
                                                           phase=0,
                                                           voltage=self.microwave_amplitude,
                                                           Time_2_pi=self.rabi_period,
                                                           max_voltage=max_amplitude)

        short_pulse_element = self._get_pi_X_pulse_element(length=pulse_length / max_ampl_factor,
                                                           freq=detuned_frequency,
                                                           phase=0,
                                                           voltage=self.microwave_amplitude,
                                                           Time_2_pi=self.rabi_period,
                                                           max_voltage=max_amplitude)

        opt_pulse_element = self._get_optimal_control_pulse_element(length=pulse_length,
                                                                    file_name=file_name,
                                                                    freq=detuned_frequency,
                                                                    phase=0,
                                                                    voltage=self.microwave_amplitude,
                                                                    Time_2_pi=self.rabi_period,
                                                                    max_voltage=max_amplitude)

        # Create blocks and append to created_blocks list
        rabi_block_on_res = PulseBlock(name='rabi_on_res')
        rabi_block_on_res.append(mw_element_on_res)
        rabi_block_on_res.append(laser_element)
        rabi_block_on_res.append(delay_element)
        rabi_block_on_res.append(waiting_element)
        created_blocks.append(rabi_block_on_res)

        rabi_block_off_res = PulseBlock(name='rabi_off_res')
        rabi_block_off_res.append(mw_element_off_res)
        rabi_block_off_res.append(laser_element)
        rabi_block_off_res.append(delay_element)
        rabi_block_off_res.append(waiting_element)
        created_blocks.append(rabi_block_off_res)

        guess_pulse_block = PulseBlock(name='guess_pulse_block')
        guess_pulse_block.append(guess_pulse_element)
        guess_pulse_block.append(laser_element)
        guess_pulse_block.append(delay_element)
        guess_pulse_block.append(waiting_element)
        created_blocks.append(guess_pulse_block)

        short_pulse_block = PulseBlock(name='short_pulse_block')
        short_pulse_block.append(short_pulse_element)
        short_pulse_block.append(laser_element)
        short_pulse_block.append(delay_element)
        short_pulse_block.append(waiting_element)
        created_blocks.append(short_pulse_block)

        opt_pulse_block = PulseBlock(name='opt_pulse_block')
        opt_pulse_block.append(opt_pulse_element)
        opt_pulse_block.append(laser_element)
        opt_pulse_block.append(delay_element)
        opt_pulse_block.append(waiting_element)
        created_blocks.append(opt_pulse_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((rabi_block_on_res.name, num_of_points_on_res - 1))
        block_ensemble.append((rabi_block_off_res.name, num_of_points_off_res - 1))
        block_ensemble.append((guess_pulse_block.name, num_of_guess_pulses - 1))
        block_ensemble.append((short_pulse_block.name, num_of_short_pulses - 1))
        block_ensemble.append((opt_pulse_block.name, num_of_opt_pulses - 1))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))


        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = tau_array
        block_ensemble.measurement_information['units'] = ('s', '')
        block_ensemble.measurement_information['labels'] = ('Tau', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = number_of_lasers
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # Append ensemble to created_ensembles list
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

