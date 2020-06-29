# Focusing procedures
import os
import logging
import time

def StartupFocusProcedure(focus_obj, camera_obj, exp_time, filter, starting_delta, image_path, focus_tolerance, max_distance):
    '''
    Description
    -----------
    Automated focusing procedure to be used before taking any science images.  Uses the
    camera to take test exposures and measures the FWHM of the images.

    Parameters
    ----------
    focus_obj : CLASS INSTANCE OBJECT of Focuser
        Class object of our focuser, used for moving the focus in/out
    camera_obj : CLASS INSTANCE OBJECT of Camera
        Class object of our camera, used for taking exposures for finding focus
    exp_time : INT
        Length of camera exposures in seconds.
    filter : STR
        Filter to take camera exposures in.
    starting_delta : INT
        Initial focuser movement length.
    image_path : STR
        File path to the CCD images to be used for focusing.
    focus_tolerance : INT
        How close the focus should be to the minimum found before stopping.
    max_distance : INT
        Maximum distance away from the initial position the focuser may move before stopping.

    Returns
    -------
    None.

    '''
    focus_obj.focused.clear()
        
    try: os.mkdir(os.path.join(image_path, r'focuser_calibration_images'))
    except: logging.error('Could not create subdirectory for focusing images, or directory already exists...')
    # Creates new sub-directory for focuser images
    focus_obj.onThread(focus_obj.setFocusDelta, starting_delta)
    focus_obj.onThread(focus_obj.current_position)
    time.sleep(10)
    initial_position = focus_obj.position
    Last_FWHM = None
    minimum = None
    i = 0
    while True:
        image_name = '{0:s}_{1:d}s-{2:04d}.fits'.format('FocuserImage', exp_time, i + 1)
        path = os.path.join(image_path, r'focuser_calibration_images', image_name)
        camera_obj.onThread(camera_obj.expose, exp_time, filter, save_path=path, type="light")
        camera_obj.image_done.wait()
        focus_obj.onThread(focus_obj.current_position)
        time.sleep(1)
        current_position = focus_obj.position
        camera_obj.onThread(camera_obj.get_FWHM)
        time.sleep(1)
        FWHM = camera_obj.fwhm
        if abs(current_position - initial_position) >= max_distance:
            logging.error('Focuser has stepped too far away from initial position and could not find a focus.')
            break
        if minimum != None and abs(FWHM - minimum) < focus_tolerance:
            break
        if not FWHM:
            logging.warning('Could not retrieve FWHM from the last exposure...retrying')
            i += 1
            if i >= 9:
                logging.error('There is a problem with MaxIm DL\'s fwhm property.  Cannot focus.')
                break
            continue
        if Last_FWHM == None:
            # First cycle
            focus_obj.onThread(focus_obj.focusAdjust, "in")
            focus_obj.adjusting.wait()
            focus_obj.onThread(focus_obj.focusAdjust, "in")
            focus_obj.adjusting.wait()
            last = "in"
        elif FWHM <= Last_FWHM:
            # Better FWHM -- Keep going
            focus_obj.onThread(focus_obj.focusAdjust, last)
            focus_obj.adjusting.wait()
        elif FWHM > Last_FWHM:
            # Worse FWHM -- Switch directions
            if i > 1:
                minimum = Last_FWHM
            if last == "in":
                focus_obj.onThread(focus_obj.focusAdjust, "out")
                focus_obj.adjusting.wait()
                last = "out"
            elif last == "out":
                focus_obj.onThread(focus_obj.focusAdjust, "in")
                focus_obj.adjusting.wait()
                last = "in"
        Last_FWHM = FWHM
        i += 1
        
    logging.info('Autofocus achieved a FWHM of {} pixels!'.format(FWHM))
        
    focus_obj.focused.set()
    
def ConstantFocusProcedure(focus_obj):
    pass