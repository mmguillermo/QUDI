import numpy as np


####################################### just a SSR readout, no real experiment ###########################

def add_camera_info(experiment, qm_dict):
    qm_dict['experiment'] = experiment
    qm_dict['sequence_mode'] = True
    # FIXME: This should be improved
    return qm_dict

def set_up_camera_measurement(qm_dict):
    iXon_897.set_up_counter()
    iXon_897._set_frame_transfer(True)
    #TODO set optimal exposure
    iXon_897.set_exposure(qm_dict['exposure_time']-1e3)
    iXon_897._start_acquisition()
    time.sleep(1)
    return


def basic_camera_measurement(qm_dict):
    set_up_camera_measurement(qm_dict)
    pulsedmasterlogic.toggle_pulse_generator(True)
    length = qm_dict['num_of_points'] * qm_dict['repetitions']

    # read images as soon as they are acquired and check if list has correct size
    images = []
    while len(images) < length:
        first, last = iXon_897._get_number_new_images()
        if (first < last) | (first == last == length):
            for i in range(first, last + 1):
                img = iXon_897._get_images(i, i, 1)
                images.append(img)
                pulsedmasterlogic.log.warning(len(images))
    # the first frequency has two triggers, therefore remove one image
    iXon_897.stop_acquisition()
    pulsedmasterlogic.toggle_pulse_generator(False)
    ananlyze_images(images)
    return 0


def ananlyze_images(images):
    pulsedmasterlogic.images=images
    return images