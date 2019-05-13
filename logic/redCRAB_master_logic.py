# -*- coding: utf-8 -*-
"""
DESCRIPTION OF THIS MODULE GOES HERE!

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


from qtpy import QtCore
from core.module import Connector, StatusVar, ConfigOption
from logic.generic_logic import GenericLogic
import os
import time


class OptimizationPulse:

    def __init__(self, id=0, amp_limit_low=0.0, amp_limit_high=1.0, pulsename='Pulse', pulsenumber=1,
                 flag_select_basis=True,
                 flag_reasonable_ampl_var=False, flag_num_gaussians=False, flag_select_basis_f_2=False,
                 flag_frequency_range=False, flag_frequency_range_2=False, flag_freq_select_distr=False,
                 flag_freq_select_distr_2=False, flag_analytic_scaling_fnct_avail=False,
                 flag_numeric_scaling_fnct_avail=False,
                 flag_init_guess_avail=False, flag_analytic_guess_input=False,
                 flag_numeric_guess_input=False, flag_file_guess_input=False,
                 basis_choice='fourier', ampl_var=0.01, num_gauss=1, freq_range_lower=0.5,
                 freq_range_upper=25.0, freq_range_lower_2=0.5, freq_range_upper_2=25.0, w_distr=[1], function='',
                 N_bins=0, num_prob=[0.0, 0.0], w_distr_2=[1], function_2='', N_bins_2=0, num_prob_2=[0.0, 0.0],
                 contr_ampl_time_analytic='', contr_ampl_time_numeric=[0.0, 0.0], guess_scale_type='rel',
                 input_contr_ampl_time_analytic='', input_contr_ampl_time_numeric=[0.0, 0.0], col_nr=0,
                 w_distr_mean=0, w_distr_sigma=1, w_distr_mean_2=0, w_distr_sigma_2=1, **kwargs):

        # mandatory
        self.id = id
        self.pulsename = pulsename
        self.pulsenumber = pulsenumber
        self.amp_limit_low = amp_limit_low
        self.amp_limit_high = amp_limit_high
        self.flag_select_basis = flag_select_basis

        # flags
        self.flag_reasonable_ampl_var = flag_reasonable_ampl_var
        self.flag_num_gaussians = flag_num_gaussians
        self.flag_select_basis_f_2 = flag_select_basis_f_2
        self.flag_frequency_range = flag_frequency_range
        self.flag_frequency_range_2 = flag_frequency_range_2
        self.flag_freq_select_distr = flag_freq_select_distr
        self.flag_freq_select_distr_2 = flag_freq_select_distr_2
        self.flag_analytic_scaling_fnct_avail = flag_analytic_scaling_fnct_avail
        self.flag_numeric_scaling_fnct_avail = flag_numeric_scaling_fnct_avail
        self.flag_init_guess_avail = flag_init_guess_avail
        if flag_init_guess_avail and not flag_analytic_guess_input and not flag_numeric_guess_input:
            self.flag_analytic_guess_input = True
            self.flag_numeric_guess_input = False
        else:
            self.flag_analytic_guess_input = flag_analytic_guess_input
            self.flag_numeric_guess_input = flag_numeric_guess_input
        self.flag_file_guess_input = flag_file_guess_input

        # variables
        self.basis_choice = basis_choice
        self.ampl_var = ampl_var
        self.num_gauss = num_gauss
        self.freq_range_lower = freq_range_lower
        self.freq_range_upper = freq_range_upper
        self.freq_range_lower_2 = freq_range_lower_2
        self.freq_range_upper_2 = freq_range_upper_2
        self.w_distr = w_distr
        self.w_distr_mean = w_distr_mean
        self.w_distr_sigma = w_distr_sigma
        self.function = function
        self.N_bins = N_bins
        self.num_prob = num_prob
        self.w_distr_2 = w_distr_2
        self.w_distr_mean_2 = w_distr_mean_2
        self.w_distr_sigma_2 = w_distr_sigma_2
        self.function_2 = function_2
        self.N_bins_2 = N_bins_2
        self.num_prob_2 = num_prob_2
        self.contr_ampl_time_analytic = contr_ampl_time_analytic
        self.contr_ampl_time_numeric = contr_ampl_time_numeric
        self.guess_scale_type = guess_scale_type
        self.input_contr_ampl_time_analytic = input_contr_ampl_time_analytic
        self.input_contr_ampl_time_numeric = input_contr_ampl_time_numeric
        self.col_nr = col_nr

        self.__dict__.update(kwargs)

    def get_pulse_flag_dict(self):
        flag_dict = {'SelectBasis': self.flag_select_basis,
                     'ReasonableAmplVar': self.flag_reasonable_ampl_var,
                     'NumGaussians': self.flag_num_gaussians,
                     'SelectBasisF2': self.flag_select_basis_f_2,
                     'FrequencyRange': self.flag_frequency_range,
                     'FrequencyRangeF2': self.flag_frequency_range_2,
                     'FreqSelectDistr': self.flag_freq_select_distr,
                     'FreqSelectDistr2': self.flag_freq_select_distr_2,
                     'AnalyticScalingFnctAvail': self.flag_analytic_scaling_fnct_avail,
                     'NumericScalingFnctAvail': self.flag_numeric_scaling_fnct_avail,
                     'InitGuessAvail': self.flag_init_guess_avail,
                     'AnalyticGuessInput': self.flag_analytic_guess_input,
                     'NumericGuessInput': self.flag_numeric_guess_input,
                     'FileGuessInput': self.flag_file_guess_input}
        return flag_dict


class PhysicalParameter:

    def __init__(self, id=0, para_name='Parameter', para_number=1, para_limit_lower=0.0, para_limit_upper=1.0,
                 flag_init_para_available=False,
                 flag_reasonable_para_variation=False,
                 para_value=0.1, para_variation=0.001, **kwargs):

        # mandatory
        self.id = id
        self.para_number = para_number
        self.para_name = para_name
        self.para_limit_lower = para_limit_lower
        self.para_limit_upper = para_limit_upper

        # flags
        self.flag_init_para_available = flag_init_para_available
        self.flag_reasonable_para_variation = flag_reasonable_para_variation

        # variables
        self.para_value = para_value
        self.para_variation = para_variation

        self.__dict__.update(kwargs)

    def get_para_flag_dict(self):
        flag_dict = {'InitParaAvail': self.flag_init_para_available,
                     'ReasonableParaVar': self.flag_reasonable_para_variation}
        return flag_dict


def append_txt(file, text):
    file.write('\n{!s}'.format(text))


def append_int(file, name, value):
    file.write('\n{0!s} := {1:d}'.format(name, value))


def append_float(file, name, value):
    file.write('\n{0!s} := {1:.10f}'.format(name, value))


def append_str(file, name, value):
    file.write('\n{0!s} := \'{1!s}\''.format(name, value))


def append_bool(file, name, value):
    file.write('\n{0!s} := {1:d}'.format(name, value))


def append_range(file, name, lower, upper):
    file.write('\n{0!s} := [{1:.10f}, {2:.10f}]'.format(name, lower, upper))


def append_list(file, name, list):
    file.write('\n{0!s} := {1}'.format(name, str(list)))


# def append_function(file, name, funct):
#     file.write('\n{0!s} := \'lambda t: {1}\''.format(name, funct))
class RedCRABMasterLogic(GenericLogic):
    """
    This logic module is used for an optimization using the RedCRAB server.
    """
    _modclass = 'redcrabmasterlogic'
    _modtype = 'logic'

    # general
    id_number = StatusVar('id_number', default=1)
    total_time = StatusVar('total_time', default=1.0)
    number_of_time_steps = StatusVar('number_of_time_steps', default=100)

    # Algebraic Parameters Main Settings
    form_factor_2_maximization = StatusVar('form_factor_2_maximization', default=1)
    max_num_SI = StatusVar('max_num_SI', default=3)
    max_funct_ev_SI_1 = StatusVar('max_funct_ev_SI_1', default=100)
    max_funct_ev_SI_2 = StatusVar('max_funct_ev_SI_2', default=40)
    std_available = StatusVar('std_available', default=False)
    guess_pulses_available = StatusVar('guess_pulses_available', default=False)
    # optional
    is_pure_para_opti = StatusVar('is_pure_para_opti', default=False)
    individual_output = StatusVar('individual_output', default=True)

    # Flags for Main Settings
    flag_variable_T = StatusVar('flag_variable_T', default=False)
    flag_asc_improvement_expected = StatusVar('flag_asc_improvement_expected', default=False)
    flag_asc_close = StatusVar('flag_asc_close', default=False)
    flag_specify_re_eval_steps = StatusVar('flag_specify_re_eval_steps', default=False)
    flag_is_remote = StatusVar('flag_is_remote', default=True)
    flag_is_none_remote = StatusVar('flag_is_none_remote', default=False)
    flag_name_pymod = StatusVar('flag_name_pymod', default=False)

    TT_min = StatusVar('TT_min', default=0)
    TT_max = StatusVar('TT_max', default=1)
    asc_improvement_expected = StatusVar('asc_improvement_expected', default=100)
    asc_close_after_rel_dist = StatusVar('asc_close_after_rel_dist', default=[40, 0.9])
    re_eval_steps = StatusVar('re_eval_steps', default=[0.33, 0.5, 0.501, 0.51])
    transmission_method = StatusVar('transmission_method', default=True)
    name_python_module = StatusVar('name_python_module', default='')

    saved_pulses = StatusVar('saved_pulses', default=[])
    saved_parameters = StatusVar('saved_parameters', default=[])

    # Path and File for Simulation
    file_path = StatusVar('file_path', default='RedCRAB/Optimize_NV/')
    file_name = StatusVar('file_name', default='Test_NV.py')

    pulses = []
    parameters = []
    
    def __init__(self, config, **kwargs):
        """
        Initialize the base class
        """
        super().__init__(config=config, **kwargs)
        return

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        This part will be executed each time you activate the module so not only upon starting qudi
        and the module but also if you reload the module etc.
        This method has to make sure that the modules variables/settings/states start in a well
        defined state.

        One important thing that needs to be taken care of here is the connection of signals from
        other modules.
        If you want to listen to a signal from i.e. in this case "otherlogicmodule" the connection
        has to be done here.
        """
        # Print a warning message to the qudi log
        # self.log.warning('Uh oh... trying to activate the logic template module.\n'
        #                  'I\'m so excited!!!!!!!!')
        # # Print an error message to the qudi log and prompt the user
        # self.log.error('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH!!!!!11einself')
        # # Print an info message to the qudi log.
        # self.log.info('Just want to inform you that I calmed down a bit.\nCommencing activation.')
        #
        # # Connect signal "sigOtherModuleSignal" from module "otherlogicmodule".
        # # Each time "otherlogicmodule" emits this signal this logic modules "do_stuff_with_signal"
        # # method gets called.
        # self.otherlogicmodule().sigOtherModuleSignal.connect(self.do_stuff_with_signal)
        #
        # # Switch on the "hardware"
        # self.myhardwaremodule().switch_on()

        self.log.info('RedCRB logic loading...')

        # self.saved_pulses = []
        # self.saved_parameters = []

        if abs(self.form_factor_2_maximization - 0.0) < 1e-3:
            self.log.warning('Scaling factor for cost function cannot be 0\nValue set to 1!')
            self.form_factor_2_maximization = 1.0

        self.pulses = []
        self.parameters = []

        self.load_pulses()
        self.load_parameters()

        # self.pulses.append(OptimizationPulse(1, 0, 1))
        # self.parameters.append(PhysicalParameter(1, -100, 100))

        self.log.info('RedCRB logic loaded')

        # self.pulses.append(OptimizationPulse(1, 0, 1))
        # self.parameters.append(PhysicalParameter(1, 0, 1))
        # self.create_config(123)

        # # Just for fun keep track on when the module has been activated
        # self._activation_time = time.time()
        return

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        Essentially this method should undo actions taken by "on_activate" and clean the module up.
        Most importantly it should leave the measurement in a state where it can stay, i.e. stop a
        measurement if it's still running etc.

        Also one should disconnect all signals that have been connected in "on_activate".
        """
        # active_time = int(round(time.time() - self._activation_time))
        # self.log.info('Deactivating module.\nModule has been running for {0:d} seconds.'
        #               ''.format(active_time))
        # self.otherlogicmodule().sigOtherModuleSignal.disconnect()
        # # Switch off the "hardware"
        # self.myhardwaremodule().switch_off()
        self.save_pulses()
        self.save_parameters()
        return

    def get_main_flag_dict(self):
        flag_dict = {'FLAGVARIABLET': self.flag_variable_T,
                     'FLAGASCIMPREXPECT': self.flag_asc_improvement_expected,
                     'FLAGASCCLOSE': self.flag_asc_close,
                     'FLAGSPECIFYREEVALSTEPS': self.flag_specify_re_eval_steps,
                     'FLAGISREMOTE': self.flag_is_remote,
                     'FLAGISNONEREMOTE': self.flag_is_none_remote,
                     'FLAGNAMEPYMOD': self.flag_name_pymod}
        return flag_dict

    def write_main_settings(self, file):

        file.write('-----Main_Settings-----\n')

        append_txt(file, 'STARTPHYSPARS')
        append_float(file, 'TT', self.total_time)
        append_int(file, 'Nt', self.number_of_time_steps)
        append_txt(file, 'ENDPHYSPARS\n')

        append_txt(file, 'STARTALGPARS')
        if abs(self.form_factor_2_maximization - 0.0) < 1e-3:
            append_float(file, 'FomFactor2Maximization', 1)
            self.log.warning('FomFactor2Maximization cannot be 0\nDefault value of 1 has been written to Cfg file!')
        else:
            append_float(file, 'FomFactor2Maximization', self.form_factor_2_maximization)
        append_int(file, 'MaxNumSI', self.max_num_SI)
        append_int(file, 'MaxFunctEvSI1', self.max_funct_ev_SI_1)
        append_int(file, 'MaxFunctEvSI22n', self.max_funct_ev_SI_2)
        append_bool(file, 'StdAvailable', self.std_available)
        append_bool(file, 'GuessPulsesAvailable', self.guess_pulses_available)
        append_bool(file, 'IsPureParaOpti', self.is_pure_para_opti)
        append_bool(file, 'IndividualOutput', self.individual_output)
        append_txt(file, 'ENDALGPARS\n')

        append_txt(file, 'STARTFLAGS')
        main_flag_dict = self.get_main_flag_dict()
        for x in main_flag_dict:
            append_bool(file, x, main_flag_dict[x])
        append_txt(file, 'ENDFLAGS\n')

        if self.flag_variable_T:
            append_txt(file, 'STARTFLAGGED')
            append_range(file, 'TTINT', self.TT_min, self.TT_max)
            append_txt(file, 'ENDFLAGGED\n')
        if self.flag_asc_improvement_expected:
            append_txt(file, 'STARTFLAGGED')
            append_int(file, 'ASCImprovementExpected', self.asc_improvement_expected)
            append_txt(file, 'ENDFLAGGED\n')
        if self.flag_asc_close:
            append_txt(file, 'STARTFLAGGED')
            append_list(file, 'ASCCloseAfterRelDist', self.asc_close_after_rel_dist)
            append_txt(file, 'ENDFLAGGED\n')
        if self.flag_specify_re_eval_steps:
            append_txt(file, 'STARTFLAGGED')
            append_list(file, 'ReEvalSteps', self.re_eval_steps)
            append_txt(file, 'ENDFLAGGED\n')
        if self.flag_is_remote:
            append_txt(file, 'STARTFLAGGED')
            append_bool(file, 'TransmissionMethod', self.transmission_method)
            append_txt(file, 'ENDFLAGGED\n')
        if self.flag_is_none_remote and self.flag_name_pymod:
            append_txt(file, 'STARTFLAGGED')
            append_str(file, 'NamePythonModule', self.name_python_module)
            append_txt(file, 'ENDFLAGGED\n')

    def write_pulse_options(self, file, pulse):

        file.write('\n-----Pulse{:d}-----\n'.format(pulse.pulsenumber))

        file.write('\nSTARTPULSE\n')

        flag_dict = pulse.get_pulse_flag_dict()

        append_txt(file, 'STARTPHYSPARS')
        append_range(file, 'AmpLimits', pulse.amp_limit_low, pulse.amp_limit_high)
        append_txt(file, 'ENDPHYSPARS\n')

        append_txt(file, 'STARTFLAGS')
        for x in flag_dict:
            append_bool(file, x, flag_dict[x])
        append_txt(file, 'ENDFLAGS\n')

        if flag_dict['SelectBasis']:
            append_txt(file, 'STARTFLAGGED')
            append_str(file, 'BasisChoice', pulse.basis_choice)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['ReasonableAmplVar']:
            append_txt(file, 'STARTFLAGGED')
            append_float(file, 'AmplVar', pulse.ampl_var)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['NumGaussians']:
            append_txt(file, 'STARTFLAGGED')
            append_int(file, 'NumGauss', pulse.num_gauss)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['FrequencyRange']:
            append_txt(file, 'STARTFLAGGED')
            append_range(file, 'FreqRange', pulse.freq_range_lower, pulse.freq_range_upper)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['FrequencyRangeF2']:
            append_txt(file, 'STARTFLAGGED')
            append_range(file, 'FreqRange', pulse.freq_range_lower_2, pulse.freq_range_upper_2)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['FreqSelectDistr']:
            append_txt(file, 'STARTFLAGGED')
            append_list(file, 'Wdistr', pulse.w_distr)
            if pulse.w_distr[0] is 'acustom':
                append_str(file, 'Function', pulse.function)
                if pulse.N_bins > 0:
                    append_int(file, 'Nbins', pulse.N_bins)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['FreqSelectDistr2'] and flag_dict['SelectBasisF2']:
            append_txt(file, 'STARTFLAGGED')
            append_list(file, 'Wdistr', pulse.w_distr_2)
            if pulse.w_distr_2[0] is 'acustom':
                append_str(file, 'Function', pulse.function_2)
                if pulse.N_bins_2 > 0:
                    append_int(file, 'Nbins', pulse.N_bins_2)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['AnalyticScalingFnctAvail']:
            append_txt(file, 'STARTFLAGGED')
            append_str(file, 'ContrAmplTime', pulse.contr_ampl_time_analytic)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['NumericScalingFnctAvail']:
            append_txt(file, 'STARTFLAGGED')
            if len(pulse.contr_ampl_time_numeric) is not self.number_of_time_steps:
                self.log.warning('Numeric scaling function not of correct length (should be same as number '
                                 'of time steps)')
                self.log.warning('ContrAmplTime set to 1 for all times')
                append_list(file, 'ContrAmplTime', [1] * self.number_of_time_steps)
            else:
                append_list(file, 'ContrAmplTime', pulse.contr_ampl_time_numeric)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['InitGuessAvail']:
            append_txt(file, 'STARTFLAGGED')
            append_str(file, 'GuessScaleType', pulse.guess_scale_type)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['AnalyticGuessInput']:
            append_txt(file, 'STARTFLAGGED')
            append_str(file, 'ContrAmplTime', pulse.input_contr_ampl_time_analytic)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['NumericGuessInput']:
            append_txt(file, 'STARTFLAGGED')
            if len(pulse.contr_ampl_time_numeric) is not self.number_of_time_steps:
                self.log.warning('Numeric guess input not of correct length (should be same as number of time steps)')
                self.log.warning('ContrAmplTime set to 1 for all times')
                append_list(file, 'ContrAmplTime', [1] * self.number_of_time_steps)
            else:
                append_list(file, 'ContrAmplTime', pulse.input_contr_ampl_time_numeric)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['FileGuessInput'] and flag_dict['InitGuessAvail'] and self.guess_pulses_available:
            append_txt(file, 'STARTFLAGGED')
            append_int(file, 'ColNr', pulse.col_nr)
            append_txt(file, 'ENDFLAGGED\n')

        file.write('\nENDPULSE\n')

    def write_parameters_options(self, file, param):

        file.write('\n-----Parameter{:d}-----\n'.format(param.para_number))

        file.write('\nSTARTPARAMETER\n')

        flag_dict = param.get_para_flag_dict()

        append_txt(file, 'STARTPHYSPARS')
        append_range(file, 'ParaLimits', param.para_limit_lower, param.para_limit_upper)
        append_txt(file, 'ENDPHYSPARS\n')

        append_txt(file, 'STARTFLAGS')
        for x in flag_dict:
            append_bool(file, x, flag_dict[x])
        append_txt(file, 'ENDFLAGS\n')

        if flag_dict['InitParaAvail']:
            append_txt(file, 'STARTFLAGGED')
            append_float(file, 'ParaValue', param.para_value)
            append_txt(file, 'ENDFLAGGED\n')

        if flag_dict['ReasonableParaVar']:
            append_txt(file, 'STARTFLAGGED')
            append_float(file, 'ParaVar', param.para_variation)
            append_txt(file, 'ENDFLAGGED\n')

        file.write('\nENDPARAMETER\n')

    def create_config(self, path='RedCRAB_Configs/'):

        filename = 'Cfg_%i.txt' % self.id_number

        if not os.path.isdir('RedCRAB_Configs'):
            os.mkdir('RedCRAB_Configs')

        # create file and overwrite if already exists
        open(path + filename, 'w')

        file = open(path + filename, 'a')

        self.write_main_settings(file)

        for pulse in self.pulses:
            self.write_pulse_options(file, pulse)
        for param in self.parameters:
            self.write_parameters_options(file, param)
        file.close()

    def create_chopped(self):

        path = 'RedCRAB/Config/Client_config/'

        filename = 'chopped.txt'

        try:
            with open(path + filename) as f:
                with open(path + 'temp.txt', 'w') as f1:
                    for line in f:
                        f1.write(line)

            with open(path + 'temp.txt') as f:
                with open(path + filename, 'w') as f1:
                    for line in f:
                        if line.startswith('PyModPath'):
                            file_path = str(self.file_path)
                            if file_path[-1] is not '/':
                                newline = 'PyModPath := ' + file_path + '/' + str(self.file_name) + '\n'
                            else:
                                newline = 'PyModPath := ' + file_path + str(self.file_name) + '\n'
                            f1.write(line.replace(line, newline))
                        elif line.startswith('PyModName'):
                            newline = 'PyModName := ' + str(self.file_name) + '\n'
                            f1.write(line.replace(line, newline))
                        else:
                            f1.write(line)
        except:
            self.log.error('Sorry, the chopped file could not be created!')

    def save_pulses(self):
        self.saved_pulses = []
        for pulse in self.pulses:
            dictionary = pulse.__dict__
            self.saved_pulses.append(dictionary)

    def save_parameters(self):
        self.saved_parameters = []
        for param in self.parameters:
            dictionary = param.__dict__
            self.saved_parameters.append(dictionary)

    def load_pulses(self):
        for pulse in self.saved_pulses:
            dictionary = pulse
            loaded_pulse = OptimizationPulse(**dictionary)
            self.pulses.append(loaded_pulse)

    def load_parameters(self):
        for param in self.saved_parameters:
            dictionary = param
            loaded_param = PhysicalParameter(**dictionary)
            self.parameters.append(loaded_param)

    def new_pulse(self):
        id = int(time.time()*10)
        name = str(len(self.pulses) + 1)
        number = len(self.pulses) + 1
        self.pulses.append(OptimizationPulse(id=id, pulsename='Pulse {0!s}'.format(name), pulsenumber=number))

    def new_parameter(self):
        id = int(time.time()*10)
        name = str(len(self.parameters) + 1)
        number = len(self.parameters) + 1
        self.parameters.append(PhysicalParameter(id=id, para_name='Parameter {0!s}'.format(name), para_number=number))
