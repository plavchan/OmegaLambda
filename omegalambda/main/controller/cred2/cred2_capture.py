# CRED2 Camera Image Capture - Alan Zhu, 2024-06-21

from astropy.io import fits
import ctypes
import cv2
import numpy as np
import os
import json
import psutil
import queue
import signal
import subprocess
import sys
import threading
from tqdm import tqdm
from time import sleep
from datetime import datetime, timezone, timedelta
from win32com.client import Dispatch
import pythoncom

# from PIL import Image

import FliSdk_V2 as FliSdk

########## Hardcoded - should not need to modify ##########
FILENAME_NUM_LENGTH: int = 8
FILENAME_NUM: int = 0
GROUP_NUM: int = 0
COMPRESS_CMD: list[str] = ["C:\\Program Files (x86)\\CFITSIO\\bin\\fpack.exe", "-h", "-F", "-Y"]
MAX_COMPRESS_PROCESSES: int = 10
IP_ADDRESS: ctypes.c_char_p = ctypes.c_char_p(b"169.254.123.123")
USERNAME: ctypes.c_char_p = ctypes.c_char_p(b"admin")
PASSWORD: ctypes.c_char_p = ctypes.c_char_p(b"flicred1")
CONTEXT: ctypes.c_void_p = None
TEMPERATURE: float = -40.0  # Celsius
TEMP_THRESHOLD: float = 0.5  # Celsius. Temperature threshold for cooler to reach setpoint.
TIME_SCALE_FACTOR: float = 1.0  # 36.0  # Because we don't get accurate frame rates (much higher than expected), compensate for it by increasing the stack time (empirically determined).

CONFIG_FILE: str = os.path.join(os.path.dirname(__file__), "cred2_capture_config.json")
"""Example config file:
{
    "total_run_time_seconds": 0.0,
    "image_stack_time_seconds": 1.0,
    "fps": 20,
    "ndr_num": 60,
    "enable_up_the_ramp_sampling": true,
    "take_calibration_images": false,
    "data_directory": "data",
    "filename_prefix": "image-",
    "enable_compression": true,
    "wait_for_cooler_settle": true,
    "startup_only": false,
    "manual_mode": false,
    "stop_cooler_at_end": false
}
"""
TOTAL_RUN_TIME: float = 0.0 * TIME_SCALE_FACTOR  # Seconds. Total time to capture images for. 0 for continuous capture.
IMAGE_STACK_TIME: float = 1.0 * TIME_SCALE_FACTOR  # Seconds. Stacked exposure time for the stacked images.
FPS: int = 20  # Frames per second for the camera.
NDR_NUM: int = 60  # Number of NDRs (non-destructive reads) to perform per full exposure. Can be used with or without ENABLE_UP_THE_RAMP. Set to 1 for normal behavior (no NDR).
ENABLE_UP_THE_RAMP: bool = True  # If True, will perform up-the-ramp sampling on images. Requires NDR_NUM > 1. If False, will capture images normally.
IMAGE_CHUNK_TIME: float = 3.0 * TIME_SCALE_FACTOR  # Seconds. To conserve memory, continuously stack images in chunks of this size while capturing images until it reaches the final exposure time.
TAKE_CALIBRATION_IMAGES: bool = False  # Take biases, darks, flats
DATA_DIRECTORY: str = "data"
FILENAME_PREFIX: str = "image-"
ENABLE_COMPRESSION: bool = True  # Compress images after saving using fpack
WAIT_FOR_COOLER_SETTLE: bool = True  # Wait for cooler to reach setpoint before capturing images
STARTUP_ONLY: bool = False  # If True, will just startup the control code but not start capturing images
MANUAL_MODE: bool = False  # If True, will not capture images automatically, but will allow manual captures via input
STOP_COOLER_AT_END: bool = False  # If True, will set the temp to 20C at the end of the run

# Load config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
        TOTAL_RUN_TIME = config.get("total_run_time_seconds", TOTAL_RUN_TIME) * TIME_SCALE_FACTOR
        IMAGE_STACK_TIME = config.get("image_stack_time_seconds", IMAGE_STACK_TIME) * TIME_SCALE_FACTOR
        NDR_NUM = config.get("ndr_num", NDR_NUM)
        FPS = config.get("fps", FPS)
        ENABLE_UP_THE_RAMP = config.get("enable_up_the_ramp_sampling", ENABLE_UP_THE_RAMP)
        TAKE_CALIBRATION_IMAGES = config.get("take_calibration_images", TAKE_CALIBRATION_IMAGES)
        DATA_DIRECTORY = config.get("data_directory", DATA_DIRECTORY)
        FILENAME_PREFIX = config.get("filename_prefix", FILENAME_PREFIX)
        ENABLE_COMPRESSION = config.get("enable_compression", ENABLE_COMPRESSION)
        WAIT_FOR_COOLER_SETTLE = config.get("wait_for_cooler_settle", WAIT_FOR_COOLER_SETTLE)
        STARTUP_ONLY = config.get("startup_only", STARTUP_ONLY)
        MANUAL_MODE = config.get("manual_mode", MANUAL_MODE)
        STOP_COOLER_AT_END = config.get("stop_cooler_at_end", STOP_COOLER_AT_END)

if not os.path.isabs(DATA_DIRECTORY):
    DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), DATA_DIRECTORY)

# replace DATA_DIRECTORY with Python formatted path
DATA_DIRECTORY = os.path.realpath(DATA_DIRECTORY)

########## Calculated parameters ##########
FRAME_TIME: float = round(1 / FPS, 4)  # Seconds. Time for each frame exposure.
COMPRESS_GROUP_SIZE: int = min(max(1, 60 // (IMAGE_STACK_TIME / TIME_SCALE_FACTOR)), 100)  # Number of images to compress at once
IMAGE_STACK_SIZE: int = int(IMAGE_STACK_TIME / FRAME_TIME)  # Number of images to stack for each stacked image. 1 for no stacking.
IMAGE_CHUNK_SIZE: int = int(IMAGE_CHUNK_TIME / FRAME_TIME)  # Number of images to stack for each chunk. 
NUM_IMAGES = max(int(TOTAL_RUN_TIME / IMAGE_STACK_TIME), 1)  # Number of images to capture.
CONTINUOUS_CAPTURE: bool = TOTAL_RUN_TIME == 0.0  # If True, will capture images continuously until stopped
FITS_HEADER: dict[str, str | float] = {  # For FITS headers
    "ORIGIN": "George Mason University Observatory",
    "INSTRUME": "CRED2 Near-Infrared Camera",
    "OBSERVER": "GMU CRED2 automation code",
    "EXPTIME": IMAGE_STACK_TIME / TIME_SCALE_FACTOR,
    "FRAMTIME": FRAME_TIME,
    "FPS": FPS,
    "SET-TEMP": TEMPERATURE,
    "FILTER": "NIR",  # Placeholder for filter name because alnitak expects one
    "DATE-OBS": None,
}

if ENABLE_UP_THE_RAMP:
    FITS_HEADER.update({
        "GROUPNUM": None,
        "TOT-NDRS": None,
        "SET-NDRS": NDR_NUM,
    })

CAMERA_BUFFER_RESET_TIME: datetime = datetime.now()  # Time of last camera buffer reset
CAMERA_BUFFER_RESET_INTERVAL: float = 50 * 60  # How often to start and stop the camera to reset the buffer, seconds
NDR_GROUPS_NUM: int = int(IMAGE_STACK_TIME / (FRAME_TIME * NDR_NUM)) if ENABLE_UP_THE_RAMP else None # Number of NDR groups that constitute a full exposure. We need to count groups instead of images because there are often image drops.

########## Checks ##########
if IMAGE_STACK_TIME < FRAME_TIME:
    raise ValueError("IMAGE_STACK_TIME must be greater than or equal to FRAME_TIME.")

if ENABLE_UP_THE_RAMP and NDR_NUM <= 1:
    raise ValueError("NDR_NUM must be greater than 1 to enable up-the-ramp sampling.")

if NDR_GROUPS_NUM and NDR_GROUPS_NUM < 1:
    raise ValueError(
        f"The specified image stack time is less than the minimum stack time of {FRAME_TIME * NDR_NUM} seconds with the selected number of NDRs. " \
        "Increase the image stack time or decrease the number of NDRs."
    )

if not isinstance(FPS, int):
    print("Warning: FPS should be an integer. Using the nearest integer value.")
    FPS = round(FPS)

########## Helpers ##########
def create_save_directory() -> None:
    if not os.path.exists(DATA_DIRECTORY):
        os.makedirs(DATA_DIRECTORY)
        print(f"Created directory {DATA_DIRECTORY} for saving images.")
    elif not os.path.isdir(DATA_DIRECTORY):
        print(f"Error: {DATA_DIRECTORY} is not a directory.")
        disconnect()
        exit()
    elif len(os.listdir(DATA_DIRECTORY)) > 0:
        # If directory already exists, attempt to continue numbering from last image
        try:
            global FILENAME_NUM
            FILENAME_NUM = max(
                int(file[len(FILENAME_PREFIX): len(FILENAME_PREFIX) + FILENAME_NUM_LENGTH]) 
                for file in os.listdir(DATA_DIRECTORY) 
                if file.startswith(FILENAME_PREFIX)
            )
            print(f"Continuing numbering from image {FILENAME_NUM}.")
        except ValueError:
            print(f"Error: {DATA_DIRECTORY} contains files that do not match the expected format. Attempting to continue.")
            pass

    print(f"Saving images to {DATA_DIRECTORY}.")


########## Camera control ##########
def setup() -> None:
    print("Setting up CRED2 camera.")
    set_temp(TEMPERATURE)

    # Set options
    FliSdk.FliCredTwo.EnableAntiBlooming(CONTEXT, False)
    FliSdk.FliCredTwo.SetConversionGain(CONTEXT, "low")
    FliSdk.FliCredTwo.EnableBadPixel(CONTEXT, True)  # Onboard bad pixel correction
    FliSdk.FliCredTwo.EnableRawImages(CONTEXT, NDR_NUM > 1)  # Raw images required for NDR processing
    FliSdk.FliCredTwo.SetNbReadWoReset(CONTEXT, NDR_NUM)  # This is the number of NDRs

    tuning_mode = "long_exposure" if NDR_NUM > 1 else "short_exposure"  # Long exposure mode decreases bad pixels dramatically with NDRs
    FliSdk.FliSerialCamera.SendCommand(CONTEXT, f"set tuning {tuning_mode}")

    create_save_directory()

    if WAIT_FOR_COOLER_SETTLE:
        print("Waiting for cooler to reach setpoint...")
        temp = get_temp()
        timeout = datetime.now() + timedelta(minutes=10)
        while abs(temp - TEMPERATURE) > TEMP_THRESHOLD and datetime.now() < timeout:
            sleep(5)
            temp = get_temp()
            print(temp, end=" ", flush=True)
        if abs(temp - TEMPERATURE) > TEMP_THRESHOLD:
            print(f"\nCooler did not reach setpoint after 10 minutes. Current temperature: {temp} C.")
            print("Continuing without waiting for cooler to reach setpoint.")
        else:
            print("\nCooler has reached setpoint.")

    if TAKE_CALIBRATION_IMAGES:
        take_calibration_images()
    
    set_fps(FPS)
    
    sleep(2)  # Wait for camera to set up
    print("CRED2 camera setup complete.")


# CONTEXT = FliSdk.Init()
def connect(exit_on_fail=True) -> None:
    global CONTEXT
    CONTEXT = FliSdk.Init()

    print("Attempting to connect to CRED2 camera via Ethernet...")
    camera: str = FliSdk.AddEthernetCamera(CONTEXT, IP_ADDRESS, USERNAME, PASSWORD)[1]
    
    if not camera:
        print("Could not connect to CRED2 camera via Ethernet.")
        disconnect()
        if exit_on_fail:
            print("Exiting...")
            exit(1)

    FliSdk.SetCamera(CONTEXT, camera)
    FliSdk.Update(CONTEXT)
    print("Connected to CRED2 camera via Ethernet.")


def disconnect() -> None:
    if FliSdk.IsStarted(CONTEXT):
        FliSdk.Stop(CONTEXT)
    FliSdk.Exit(CONTEXT)
    print("Disconnected from CRED2 camera.")


def get_fps() -> float:
    return FliSdk.FliSerialCamera.GetFps(CONTEXT)[1]


def set_fps(fps: float) -> float:
    FliSdk.FliSerialCamera.SetFps(CONTEXT, fps)
    print(f"FPS set to {get_fps()}.")


def get_temp() -> float:
    return FliSdk.FliCredTwo.GetTempSnake(CONTEXT)[1]


def set_temp(temp: float) -> float:
    FliSdk.FliCredTwo.SetTempSnakeSetPoint(CONTEXT, temp)
    print(f"Temperature setpoint set to {FliSdk.FliCredTwo.GetTempSnakeSetPoint(CONTEXT)[1]} C.")
    print(f"Current temperature: {get_temp()} C.")


NUM_RESTARTS: int = 0
LAST_RESTART: datetime = datetime.now() - timedelta(days=1)
def restart_camera() -> None:
    global NUM_RESTARTS, LAST_RESTART
    print("Restarting camera...")

    # Prevent too many restarts
    if (datetime.now() - LAST_RESTART).total_seconds() < max(60 * 3, 3 * IMAGE_STACK_TIME / TIME_SCALE_FACTOR) and NUM_RESTARTS > 2:
        print("Camera has restarted too many times in a short period of time. Continuing without restarting for now...")
        return
    if (datetime.now() - LAST_RESTART).total_seconds() < 60 * 60 and NUM_RESTARTS > 4:
        print("Camera has restarted too many times in the last hour. Continuing without restarting for now...")
        return
    if NUM_RESTARTS > 10:
        print("Camera has restarted too many times. Continuing without restarting...")
        return
    
    pause_captures()
    print(f"Camera restarted {NUM_RESTARTS} times. Last restart: {LAST_RESTART.strftime('%Y-%m-%d %H:%M:%S')}, Current restart: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sleep(10)
    print("Rebooting camera...")
    FliSdk.FliCredTwo.Reboot(CONTEXT)
    # FliSdk.FliSerialCamera.SendCommand(CONTEXT, "reboot")
    sleep(2)
    disconnect()
    # FliSdk.Stop(CONTEXT)
    print("Camera rebooting. Waiting for 90 seconds for camera to start up again...")
    sleep(90)

    print("Reconnecting to camera...")
    tries = 5
    while tries > 0:
        try:
            connect(exit_on_fail=False)
            setup()
            break
        except Exception as e:
            print(f"Error connecting to camera: {e}. Sleeping for {10 + tries * 4} seconds, then trying again...")
            sleep(10 + tries * 4)
            tries -= 1
    if tries == 0:
        print("Failed to connect to camera after 5 tries. Exiting...")
        stop_threads()
        exit(1)

    sleep(2)
       
    NUM_RESTARTS += 1
    LAST_RESTART = datetime.now()

    fps = get_fps()
    if fps == 0.0:
        print("FPS is 0.0 after restarting camera. Restarting camera again...")
        restart_camera()
        return

    initialize_image_callback()
    sleep(2)

    print("Camera restarted successfully.")
    resume_captures()


########## Calibration images ##########
NUM_DARK_IMAGES: int = max(int(5 * 60 / (IMAGE_STACK_TIME / TIME_SCALE_FACTOR)), 10)  # 5 min of images or 10 frames, whichever is greater
NUM_FLAT_IMAGES: int = NUM_DARK_IMAGES
# FLAT_STACK_TIME: float = 10.0 * TIME_SCALE_FACTOR  # Seconds. Stacked exposure time for the flat images.
FLAT_STACK_TIME: float = IMAGE_STACK_TIME  # setting this to the same as IMAGE_STACK_TIME for now


def take_darks() -> None:
    set_fps(FPS)
    print(f"Taking {NUM_DARK_IMAGES} dark frames at {FPS} FPS stacked to {IMAGE_STACK_TIME / TIME_SCALE_FACTOR}s (science exposure time).")
    take_calibration_image("dark", NUM_DARK_IMAGES, IMAGE_STACK_TIME)
    if IMAGE_STACK_TIME != FLAT_STACK_TIME:
        print(f"Taking {NUM_FLAT_IMAGES} dark frames at {FPS} FPS stacked to {FLAT_STACK_TIME / TIME_SCALE_FACTOR}s (flat exposure time).")
        FITS_HEADER["EXPTIME"] = FLAT_STACK_TIME / TIME_SCALE_FACTOR
        take_calibration_image("dark", NUM_FLAT_IMAGES, FLAT_STACK_TIME)
        FITS_HEADER["EXPTIME"] = IMAGE_STACK_TIME / TIME_SCALE_FACTOR


def take_flats() -> None:
    set_fps(FPS)
    print(f"Taking {NUM_FLAT_IMAGES} flat frames at {FPS} FPS stacked to {IMAGE_STACK_TIME / TIME_SCALE_FACTOR}s (science exposure time).")
    take_calibration_image("flat", NUM_FLAT_IMAGES, IMAGE_STACK_TIME)
    if IMAGE_STACK_TIME != FLAT_STACK_TIME:
        print(f"Taking {NUM_FLAT_IMAGES} flat frames at {FPS} FPS stacked to {FLAT_STACK_TIME / TIME_SCALE_FACTOR}s (flat exposure time).")
        FITS_HEADER["EXPTIME"] = FLAT_STACK_TIME / TIME_SCALE_FACTOR
        take_calibration_image("flat", NUM_FLAT_IMAGES, FLAT_STACK_TIME)
        FITS_HEADER["EXPTIME"] = IMAGE_STACK_TIME / TIME_SCALE_FACTOR


def take_calibration_images() -> None:
    global NUM_DARK_IMAGES, NUM_FLAT_IMAGES
    initialize_image_callback(start=False)
    print("-" * 40)
    print("Beginning calibration images procedure.")
    print("Preparing to take dark frames. Ensure the dome is darkened, and turn away the tertiary mirror to ensure no light enters the sensor.")
    
    num_darks = ""
    while not (num_darks.strip().isdigit() or num_darks.strip().lower() == "skip"):
        num_darks = input(f"Enter the number of dark frames to take (default is {NUM_DARK_IMAGES}), or type SKIP to skip taking darks: ")
    if num_darks.strip().lower() == "skip":
        print("Skipping taking dark frames.")
    else:
        NUM_DARK_IMAGES = int(num_darks) if num_darks.strip() else NUM_DARK_IMAGES
        take_darks()
        print()

    # print(f"Taking {NUM_BIAS_FRAMES} bias frames at {BIAS_FPS} FPS.")
    # set_fps(BIAS_FPS)
    # take_calibration_image("bias", NUM_BIAS_FRAMES)
    # print()

    print("Preparing to take flat frames. Turn the tertiary mirror to the CRED2 camera and turn on the flat lamp.")
    num_flats = ""
    while not (num_flats.strip().isdigit() or num_flats.strip().lower() == "skip"):
        num_flats = input(f"Enter the number of flat frames to take (default is {NUM_FLAT_IMAGES}), or type SKIP to skip taking flats: ")
    if num_flats.strip().lower() == "skip":
        print("Skipping taking flat frames.")
    else:
        NUM_FLAT_IMAGES = int(num_flats) if num_flats.strip() else NUM_FLAT_IMAGES
        take_flats()
        print()

    print("Done taking calibration images.")
    print("-" * 40)


def take_calibration_image(calibration_type, num_images, stack_time) -> None:
    maxim = Dispatch("MaxIm.Application")
    maxim.LockApp = True
    maxim_document = Dispatch("MaxIm.Document")

    stack_size = int(stack_time / FRAME_TIME)
    annotation = f"{calibration_type}_{stack_time / TIME_SCALE_FACTOR:.2f}s"
    paths = []
    prev_image = np.array([])

    resume_captures()
    for _ in tqdm(range(num_images), unit="images"):
        image = take_stacked_exposure(stack_size=stack_size, write=False)
        path = write_to_fits(image, annotation=annotation)
        maxim_document.OpenFile(path)
        paths.append(path)

        check_identical_images(image, prev_image)
        prev_image = image

        if stop_event.is_set():
            break
    pause_captures()

    if ENABLE_COMPRESSION:
        print("Compressing calibration images...")
        compress_group(paths)


########## Image processing ##########
WIDTH = 640
HEIGHT = 512
ArrayType = ctypes.c_uint16 * WIDTH * HEIGHT
bad_image_count = 0
def get_image() -> np.ndarray[np.uint16]:
    global bad_image_count

    continue_taking_images.wait()
    if stop_event.is_set():
        return np.array([])

    size = read_queue.qsize()

    if size > 10 * FPS:
        print(f"Read queue size is {size}. Clearing queue to get latest exposure.")
        with read_queue.mutex:
            read_queue.queue.clear()

    try:
        image = read_queue.get(timeout=10)
    except queue.Empty:
        if continue_taking_images.is_set():
            print("No image received from camera. Restarting camera...")
            restart_camera()
        read_queue.task_done()
        return get_image()

    # width, height = FliSdk.GetCurrentImageDimension(CONTEXT)
    pa = ctypes.cast(image, ctypes.POINTER(ArrayType))
    image = np.ndarray((HEIGHT, WIDTH), dtype=np.uint16, buffer=pa.contents)

    read_queue.task_done()

    if image.shape != (HEIGHT, WIDTH):
        bad_image_count += 1
        print(f"Bad image received from camera. Total bad images: {bad_image_count}")

        if bad_image_count > 10:
            print("Too many bad images received. Restarting camera...")
            restart_camera()
            bad_image_count = 0

        return get_image()

    bad_image_count = 0  # Reset bad image count if a good image is received
    return image
    # return FliSdk.GetRawImageAsNumpyArray(CONTEXT, -1)
    # return FliSdk.GetProcessedImageGrayscale16bNumpyArray(CONTEXT, -1)


def stack_images(images: list[np.ndarray]) -> np.ndarray:
    """Stack images by summing pixel values."""
    return np.sum(images, axis=0)


def median_images(images: list[np.ndarray]) -> np.ndarray:
    """Return an image with the median of the pixel values of the images."""
    return np.median(images, axis=0)


exptime_timedelta: timedelta = timedelta(seconds=IMAGE_STACK_TIME / TIME_SCALE_FACTOR)
def write_to_fits(image: np.ndarray, annotation: str = "", total_ndrs: int = None) -> str:
    global FILENAME_NUM, FITS_HEADER, GROUP_NUM
    FILENAME_NUM += 1
    FITS_HEADER["DATE-OBS"] = (datetime.now(timezone.utc) - exptime_timedelta).strftime('%F %T.%f')[:-3]
    if ENABLE_UP_THE_RAMP:
        GROUP_NUM += 1
        FITS_HEADER["GROUPNUM"] = GROUP_NUM
        if total_ndrs is not None:
            FITS_HEADER["TOT-NDRS"] = total_ndrs
    header: fits.Header = fits.Header(FITS_HEADER)
    hdu: fits.PrimaryHDU = fits.PrimaryHDU(image, header=header)
    filename: str = f"{DATA_DIRECTORY}/{FILENAME_PREFIX}{str(FILENAME_NUM).zfill(FILENAME_NUM_LENGTH)}{'_' + annotation if annotation else ''}.fits"
    hdu.writeto(filename, overwrite=True)
    return filename
    # image_8bit = np.array(Image.fromarray(image, mode="RGBA").convert("L"))
    # hdu_8bit: fits.PrimaryHDU = fits.PrimaryHDU(image_8bit)
    # filename_8bit: str = f"{DATA_DIRECTORY}/{FILENAME_PREFIX}{str(FILENAME_NUM).zfill(FILENAME_NUM_LENGTH)}_8bit.fits"
    # hdu_8bit.writeto(filename_8bit)


def compress(path: str) -> None:
    subprocess.Popen(COMPRESS_CMD + [path])


def compress_group(paths: list[str]) -> None:
    subprocess.Popen(COMPRESS_CMD + paths)


def show_image(image: np.ndarray) -> None:
    # Need to be careful to not modify complex data types
    # display_image = np.array(Image.fromarray(image, mode="RGBA").convert("L")) if image.dtype == np.uint32 else image
    display_image = image.astype(np.uint16)
    cv2.imshow("CRED2 Camera", display_image)
    cv2.waitKey(1)


def check_identical_images(image1: np.ndarray, image2: np.ndarray) -> None:
    # If the two images are identical, restart the camera
    if image1.shape != image2.shape or not np.all(np.isclose(image1, image2)):
        return
    print("Two consecutive identical images detected.")
    restart_camera()


def uptheramp_fit(images: list[np.ndarray]) -> np.ndarray:
    # Performs up-the-ramp linear regression
    images = np.array(images)
    start_num = images[0][0][0]  # The first pixel in the image holds the image number; we don't have a good way of getting the actual timestamp
    times = np.array([(image[0][0] - start_num) * FRAME_TIME for image in images], dtype=np.float32)  # Approximate back to image timestamps
    t = times[:, np.newaxis, np.newaxis]

    # Compute means
    t_mean = np.mean(t)
    y_mean = np.mean(images, axis=0)

    # Compute slope: numerator and denominator of covariance/variance
    numerator = np.sum((t - t_mean) * (images - y_mean), axis=0, dtype=np.float32)
    denominator = np.sum((t - t_mean) ** 2, dtype=np.float32)
    m = numerator / denominator  # slope at each (i, j)

    # Compute intercept
    # b = y_mean - m * t_mean
    return m


########## Threads ##########
read_queue = queue.Queue()
write_queue = queue.Queue()
compress_queue = queue.Queue()
display_queue = queue.Queue()
progress_queue = queue.Queue()
uptheramp_queue = queue.Queue()

read_th: threading.Thread = None
write_th: threading.Thread = None
compress_th: threading.Thread = None
display_th: threading.Thread = None
progress_th: threading.Thread = None
uptheramp_th: threading.Thread = None

stopping_event = threading.Event()
stop_event = threading.Event()
continue_taking_images = threading.Event()  # If False, will pause taking images
continue_taking_images.set()

STOP = "STOP"
RESET = "RESET"


def stop_threads(*args, script_done=False) -> None:
    if stopping_event.is_set():
        print("A stop threads command was already issued. Ignoring this command.", flush=True)
        return
    stopping_event.set()
    print("Stopping threads...", flush=True)
    if ENABLE_COMPRESSION:
        compress_queue.put(STOP)
    display_queue.put(STOP)
    write_queue.put(STOP)
    progress_queue.put(STOP)
    uptheramp_queue.put(STOP)
    sleep(0.1)
    stop_event.set()

    if STOP_COOLER_AT_END:
        set_temp(20.0)

    if ENABLE_COMPRESSION and compress_th:
        print("Stopping compress thread...", flush=True)
        compress_th.join(timeout=5)
        if compress_th.is_alive():
            print("Compress thread failed to stop.", flush=True)
    if write_th:
        print("Stopping write thread...", flush=True)
        write_th.join(timeout=5)
        if write_th.is_alive():
            print("Write thread failed to stop.", flush=True)
    if display_th:
        print("Stopping display thread...", flush=True)
        display_th.join(timeout=5)
        if display_th.is_alive():
            print("Display thread failed to stop.", flush=True)
    if progress_th:
        print("Stopping progress bar thread...", flush=True)
        progress_th.join(timeout=5)
        if progress_th.is_alive():
            print("Progress bar thread failed to stop.", flush=True)
    if uptheramp_th:
        print("Stopping up-the-ramp sampling thread...", flush=True)
        uptheramp_th.join(timeout=10)
        if uptheramp_th.is_alive():
            print("Up-the-ramp sampling thread failed to stop.", flush=True)
    if read_th and not script_done:
        print("Stopping read thread...", flush=True)
        if not continue_taking_images.is_set():
            continue_taking_images.set()  # To make read thread stop
        sleep(0.1)
        pause_captures()
        sleep(1)
        read_th.join(timeout=IMAGE_CHUNK_TIME * 5)
        if read_th.is_alive():
            print("Read thread failed to stop.", flush=True)
    if CONTEXT:
        print("Disconnecting from camera...", flush=True)
        disconnect()
    exit()


def pause_captures(quiet=False) -> None:
    if not quiet:
        print("Pausing image captures.")
    FliSdk.Stop(CONTEXT)
    continue_taking_images.clear()


def resume_captures(quiet=False) -> None:
    if not quiet:
        print("Resuming image captures.")
    start_captures(quiet=quiet)
    continue_taking_images.set()


def start_captures(quiet=False) -> None:
    if FliSdk.IsStarted(CONTEXT):
        return
    if not quiet:
        print("Starting image captures.")
    FliSdk.Start(CONTEXT)
    sleep(2)


def reset_buffer() -> None:
    global CAMERA_BUFFER_RESET_TIME
    print("Resetting camera buffer...")
    pause_captures()
    sleep(4)
    FliSdk.ResetBuffer(CONTEXT)

    if ENABLE_UP_THE_RAMP:  # Resetting the buffer will mess with NDRs
        uptheramp_queue.put(RESET)
        # TODO: also do something for NDR_NUM > 1 but not ENABLE_UP_THE_RAMP

    sleep(4)
    resume_captures()
    CAMERA_BUFFER_RESET_TIME = datetime.now()


def check_buffer_needs_reset() -> None:
    if datetime.now() - CAMERA_BUFFER_RESET_TIME > timedelta(seconds=CAMERA_BUFFER_RESET_INTERVAL):
        print("Briefly stopping and resuming exposures to reset buffer...")
        reset_buffer()

def take_one_capture(quiet=False) -> None:
    if not quiet:
        print("Taking one exposure.")
    resume_captures(quiet=quiet)
    take_stacked_exposure()
    pause_captures(quiet=quiet)


def take_stacked_exposure(stack_size=IMAGE_STACK_SIZE, write=True) -> np.ndarray | None:
    if stack_size == 1 and not ENABLE_UP_THE_RAMP:
        image = get_image()
        if stop_event.is_set():
            return
    elif ENABLE_UP_THE_RAMP:
        for _ in range(stack_size // IMAGE_CHUNK_SIZE):
            for _ in range(IMAGE_CHUNK_SIZE):
                uptheramp_queue.put(get_image())
            if stop_event.is_set():
                return
        remaining_images = stack_size % IMAGE_CHUNK_SIZE
        if remaining_images:
            for _ in range(remaining_images):
                uptheramp_queue.put(get_image())
            if stop_event.is_set():
                return
    elif stack_size > IMAGE_CHUNK_SIZE:
        images = []
        for _ in range(stack_size // IMAGE_CHUNK_SIZE):
            images.extend(get_image() for _ in range(IMAGE_CHUNK_SIZE))
            if stop_event.is_set():
                return
            image = stack_images(images)
            images.clear()
            images.append(image)

        remaining_images = stack_size % IMAGE_CHUNK_SIZE
        if remaining_images:
            images.extend(get_image() for _ in range(remaining_images))
            if stop_event.is_set():
                return
            image = stack_images(images)
    else: 
        images = [get_image() for _ in range(stack_size)]
        if stop_event.is_set():
            return
        image = stack_images(images)

    if write and not ENABLE_UP_THE_RAMP:
        write_queue.put(image)
        return image


def image_callback(image, context=None):
    if not continue_taking_images.is_set():
        return
    read_queue.put(image)

image_callback_func = FliSdk.CWRAPPER(image_callback)
read_images = 0


def initialize_image_callback(start=True) -> None:
    global read_images
    FliSdk.EnableRingBuffer(CONTEXT, True)
    user_context = None
    callback_context = FliSdk.AddCallBackNewImage(CONTEXT, image_callback_func, FPS, False, user_context)
    if start:
        start_captures()
    read_images = 0


def read_thread() -> None:
    global read_images, CAMERA_START_TIME
    CAMERA_START_TIME = datetime.now()

    continue_taking_images.wait()  # for STARTUP_ONLY mode
    if stop_event.is_set():
        return

    if not TAKE_CALIBRATION_IMAGES:
        initialize_image_callback()
    else:
        resume_captures(quiet=True)

    if IMAGE_STACK_SIZE > 1:
        if CONTINUOUS_CAPTURE:
            while not stop_event.is_set():
                take_stacked_exposure()
        else:
            for _ in tqdm(range(NUM_IMAGES), unit="images"):
                take_stacked_exposure()
                read_images += 1
                if stop_event.is_set():
                    break
    else:
        if CONTINUOUS_CAPTURE:
            while not stop_event.is_set():
                image = get_image()
                write_queue.put(image)
        else:
            for _ in tqdm(range(NUM_IMAGES), unit="images"):
                image = get_image()
                write_queue.put(image)
                read_images += 1
                if stop_event.is_set():
                    break

    if read_images >= NUM_IMAGES and not CONTINUOUS_CAPTURE:
        print()
        print(f"Done capturing {NUM_IMAGES} images.")
        # wait_time = write_queue.qsize() * 0.05 + (compress_queue.qsize() * 0.1 if ENABLE_COMPRESSION else 0)
        # if wait_time > 0:
        #     wait_time += 1
        #     print(f"Waiting for {wait_time:.2f} seconds for remaining images to be saved and compressed...")
        #     sleep(wait_time)
        stop_threads(script_done=True)


def write_thread() -> None:
    prev_image = np.array([])
    while not stop_event.is_set():
        image = write_queue.get()
        if isinstance(image, str) and image == STOP:
            break
        if ENABLE_UP_THE_RAMP and isinstance(image, tuple):
            image, total_ndrs = image
        if not image.shape == (HEIGHT, WIDTH):
            print(f"Warning: Image shape {image.shape} does not match expected shape {(HEIGHT, WIDTH)}. Skipping image.")
            write_queue.task_done()
            continue
        path = write_to_fits(image, total_ndrs=total_ndrs if ENABLE_UP_THE_RAMP else None)
        write_queue.task_done()
        display_queue.put(path)
        if ENABLE_COMPRESSION:
            compress_queue.put(path)
        check_identical_images(prev_image, image)
        prev_image = image


def compress_thread() -> None:
    compress_group_paths: list[str] = []

    while not stop_event.is_set():
        path = compress_queue.get()
        if isinstance(path, str) and path == STOP:
            break
        compress_group_paths.append(path)

        if len(compress_group_paths) >= COMPRESS_GROUP_SIZE:
            try:
                while sum(1 for p in psutil.process_iter() if p.name() == "fpack.exe") >= MAX_COMPRESS_PROCESSES and not stop_event.is_set():
                    sleep(0.5)
                compress_group(compress_group_paths)
            except Exception as e:
                print(f"Error compressing images: {e}. Continuing...")
            compress_group_paths.clear()
        compress_queue.task_done()


def uptheramp_thread() -> None:
    images: list[np.ndarray] = []
    resultants: list[np.ndarray] = []
    ndr_groups: int = 0
    skip_next_resultant: bool = False
    last_ndr_num: int = NDR_NUM
    total_ndrs: int = 0

    while not stop_event.is_set():
        image = uptheramp_queue.get()
        if isinstance(image, str):
            if image == STOP:
                break
            elif image == RESET:  # Throw out the next resultant if it's affected by a buffer reset
                skip_next_resultant = True
                uptheramp_queue.task_done()
                continue

        total_ndrs += 1
        ndr_num = image[0][2]  # The third pixel in the image holds the current NDR number
        if last_ndr_num < ndr_num < NDR_NUM:
            if skip_next_resultant:
                skip_next_resultant = False
                images.clear()
                uptheramp_queue.task_done()
                continue
            resultant = uptheramp_fit(images)
            resultants.append(resultant)
            images.clear() 
            ndr_groups += 1
        
        images.append(image)
        last_ndr_num = ndr_num

        if len(images) >= NDR_NUM * 10:
            print("Warning: Too many images in up-the-ramp queue. There may be a problem with taking NDRs. Resetting queue.")
            images.clear()

        if len(resultants) >= 5:
            resultant = stack_images(resultants)
            resultants.clear()
            resultants.append(resultant)

        if ndr_groups >= NDR_GROUPS_NUM:
            resultant = stack_images(resultants)
            resultants.clear()
            ndr_groups = 0
            write_queue.put((resultant, total_ndrs))
            total_ndrs = 0
        uptheramp_queue.task_done()


def display_thread() -> None:
    pythoncom.CoInitialize()  # Initialize COM for MaxIm - needed for thread
    maxim = Dispatch("MaxIm.Application")
    maxim.LockApp = True
    maxim_document = Dispatch("MaxIm.Document")
    while not stop_event.is_set():
        # image = display_queue.get()
        # show_image(image)
        path = display_queue.get()
        if isinstance(path, str) and path == STOP:
            break
        maxim_document.OpenFile(path)
        with display_queue.mutex:
            display_queue.queue.clear()  # Always show the latest image
        display_queue.task_done()


def progress_thread() -> None:
    """Progress bar for manual capture mode."""
    while not stop_event.is_set():
        progress_time = progress_queue.get()
        if isinstance(progress_time, str) and progress_time == STOP:
            break
        for _ in tqdm(range(int(progress_time)), desc="Exposing", unit="s"):
            sleep(1)
            if stop_event.is_set():
                break
        progress_queue.task_done()

########## Main ##########
def main() -> None:
    signal.signal(signal.SIGINT, stop_threads)
    signal.signal(signal.SIGTERM, stop_threads)
    signal.signal(signal.SIGABRT, pause_captures)  # Send SIGABRT to pause captures 
    signal.signal(signal.SIGILL, resume_captures)  # Send SIGILL to resume captures
    signal.signal(signal.SIGFPE, take_one_capture)  # Send SIGFPE to take one exposure

    connect()
    setup()
    
    if len(sys.argv) > 1 and (calibration_image := sys.argv[1]) in ("darks", "flats"):
        if calibration_image == "darks":
            take_darks()
        elif calibration_image == "flats":
            take_flats()
        stop_threads(script_done=True)

    if NUM_IMAGES <= 0:
        print("No images to capture.")
        stop_threads(script_done=True)

    if STARTUP_ONLY:
        pause_captures()
    
    print("Starting threads...")
    global write_th, compress_th, display_th, uptheramp_th
    write_th = threading.Thread(target=write_thread)
    write_th.start()
    display_th = threading.Thread(target=display_thread)
    display_th.start()
    
    if ENABLE_COMPRESSION:
        compress_th = threading.Thread(target=compress_thread)
        compress_th.start()

    if ENABLE_UP_THE_RAMP:
        uptheramp_th = threading.Thread(target=uptheramp_thread)
        uptheramp_th.start()

    print('-' * 40)
    print(f"Stacked exposure time: {IMAGE_STACK_TIME / TIME_SCALE_FACTOR} seconds.")
    print(f"Individual frame exposure time: {FRAME_TIME} seconds ({FPS} FPS).")
    print(f"Non-destructive reads (NDRs): {NDR_NUM}.")
    print("Press CTRL+C to stop the control code.")
    print('-' * 40)
    if STARTUP_ONLY:
        print("In STARTUP ONLY mode.")
        print("Control code started. Not capturing images yet.")
    elif MANUAL_MODE:
        global FILENAME_NUM
        print("In MANUAL CAPTURE mode.")
        print("Input the number of images to take, followed by ENTER, to manually take exposures. The default number to take is 1.")
        print("Press CTRL+C followed by ENTER to stop the control code.")

        global progress_th
        progress_th = threading.Thread(target=progress_thread)
        progress_th.start()
        initialize_image_callback(start=False)

        while True:
            try:
                # Start numbering at the nearest thousand greater than the current FILENAME_NUM
                num_images = input()
                if num_images.strip() == "":
                    num_images = "1"
                if not num_images.strip().isdigit() or int(num_images) <= 0:
                    print("Invalid input.")
                    continue
                num_images = int(num_images)

                FILENAME_NUM = (FILENAME_NUM // 1000 + 1) * 1000
                print(f"Taking {num_images} exposures.")
                print(f"Starting image number: {FILENAME_NUM + 1} | Ending image number: {FILENAME_NUM + num_images}")
                progress_queue.put(IMAGE_STACK_TIME / TIME_SCALE_FACTOR * num_images)  # Start progress bar

                resume_captures(quiet=True)
                for _ in range(num_images):
                    take_stacked_exposure()
                    if stop_event.is_set():
                        break
                    if NDR_NUM == 1:
                        check_buffer_needs_reset()
                pause_captures(quiet=True)
            except (KeyboardInterrupt, EOFError):
                stop_threads()
                break
            check_buffer_needs_reset()
    else:
        if CONTINUOUS_CAPTURE:
            print("In CONTINUOUS CAPTURE mode.")
            print("Capturing images continuously until stopped.")
        else:
            print("In FIXED NUMBER mode.")
            print(f"Number of images: {NUM_IMAGES}.")
            print(f"Total run time: {NUM_IMAGES * (IMAGE_STACK_TIME / TIME_SCALE_FACTOR)} seconds.")
        global read_th
        read_th = threading.Thread(target=read_thread)
        read_th.start()

    # display_thread()
    # TODO: Maybe monitor threads?
    # Keep the main thread alive so that it can catch signals
    counter = 0
    while True:
        sleep(0.01)
        counter += .01
        if counter >= 60:
            check_buffer_needs_reset()
            counter = 0


if __name__ == "__main__":
    main()
