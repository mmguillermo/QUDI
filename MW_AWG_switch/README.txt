Quick and dirty qudi switch module to change between CW MW and AWG channel.

=== Installation ===
step 1) copy "cw_awg_switch_logic.py" into "qudi/logic/"

step 2) copy "switch_cwmw_awg.ui" and "cw_awg_switch_gui.py" into "qudi/gui/"

step 3) add the following entry to your config into "logic" section (replace <mynicard> with the name you gave the ni_card hardware module):
	
	cwawgswitch:
        module.Class: 'cw_awg_switch_logic.CwAwgSwitchLogic'
        ttl_channel: '/Dev1/PFI9'  # The actual NI card channel to use (make sure it does not collide with other channels)
        connect:
            ttl_generator: '<mynicard>'
			
step 4) add the following entry to your config into "gui" section:

	cwawgswitchgui:
        module.Class: 'cw_awg_switch_gui.CwAwgSwitchGui'
        connect:
            cwawgswitchlogic: 'cwawgswitch'
			
step 5) Profit!