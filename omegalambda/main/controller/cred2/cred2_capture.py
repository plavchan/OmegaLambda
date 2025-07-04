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
COMPRESS_CMD: list[str] = ["C:\\Program Files (x86)\\CFITSIO\\bin\\fpack.exe", "-h", "-F", "-Y"]
MAX_COMPRESS_PROCESSES: int = 10
IP_ADDRESS: ctypes.c_char_p = ctypes.c_char_p(b"169.254.123.123")
USERNAME: ctypes.c_char_p = ctypes.c_char_p(b"admin")
PASSWORD: ctypes.c_char_p = ctypes.c_char_p(b"flicred1")
CONTEXT: ctypes.c_void_p = None
TEMPERATURE: float = -40.0  # Celsius
TEMP_THRESHOLD: float = 0.5  # Celsius. Temperature threshold for cooler to reach setpoint.
FRAME_TIME: float = 1 / 20  # Seconds. Optimal individual frame exposure time for CRED2 camera.
FRAME_TIME = 1 / 600
TIME_SCALE_FACTOR: float = 1.0  # 36.0  # Because we don't get accurate frame rates (much higher than expected), compensate for it by increasing the stack time (empirically determined).

CONFIG_FILE: str = os.path.join(os.path.dirname(__file__), "cred2_capture_config.json")
"""Example config file:
{
    "total_run_time_seconds": 0.0,
    "image_stack_time_seconds": 1.0,
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

# added 20250702
IMAGE_STACK_TIME = IMAGE_STACK_TIME / (256 * FRAME_TIME) * FRAME_TIME

COMPRESS_GROUP_SIZE: int = max(1, 60 // (IMAGE_STACK_TIME / TIME_SCALE_FACTOR))  # Number of images to compress at once
IMAGE_STACK_SIZE: int = int(IMAGE_STACK_TIME / FRAME_TIME)  # Number of images to stack for each stacked image. 1 for no stacking.
IMAGE_CHUNK_SIZE: int = int(IMAGE_CHUNK_TIME / FRAME_TIME)  # Number of images to stack for each chunk. 
NUM_IMAGES = max(int(TOTAL_RUN_TIME / IMAGE_STACK_TIME), 1)  # Number of images to capture.
CONTINUOUS_CAPTURE: bool = TOTAL_RUN_TIME == 0.0  # If True, will capture images continuously until stopped
FPS: float = round(1 / FRAME_TIME)
FITS_HEADER: dict[str, str | float] = {  # For FITS headers
    "ORIGIN": "George Mason University Observatory",
    "INSTRUME": "CRED2 Near-Infrared Camera",
    "OBSERVER": "GMU CRED2 automation code",
    "EXPTIME": IMAGE_STACK_TIME / TIME_SCALE_FACTOR,
    "FRAMTIME": FRAME_TIME,
    "SET-TEMP": TEMPERATURE,
    "FILTER": "NIR",
    "DATE-OBS": None,
}

CAMERA_BUFFER_RESET_TIME: datetime = datetime.now()  # Time of last camera buffer reset
CAMERA_BUFFER_RESET_INTERVAL: float = 45 * 60  # How often to start and stop the camera to reset the buffer, seconds

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
    # FliSdk.FliCredTwo.EnableAntiBlooming(CONTEXT, True)
    # FliSdk.FliCredTwo.SetConversionGain(CONTEXT, "high")
    # FliSdk.FliSerialCamera.SendCommand(CONTEXT, "set tuning short_exposure")

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
def get_image() -> np.ndarray[np.uint16]:
    continue_taking_images.wait()
    if stop_read_event.is_set():
        return np.array([])

    size = read_queue.qsize()

    if size > 5 * FPS:
        print(f"Read queue size is {size}. Clearing queue to get latest exposure.")
        with read_queue.mutex:
            read_queue.queue.clear()

    try:
        image = read_queue.get(timeout=30)
    except queue.Empty:
        if continue_taking_images.is_set():
            print("No image received from camera. Restarting camera...")
            restart_camera()
        return get_image()

    # width, height = FliSdk.GetCurrentImageDimension(CONTEXT)
    pa = ctypes.cast(image, ctypes.POINTER(ArrayType))
    image = np.ndarray((HEIGHT, WIDTH), dtype=np.uint16, buffer=pa.contents)
    read_queue.task_done()

    return image
    # return FliSdk.GetRawImageAsNumpyArray(CONTEXT, -1)
    # return FliSdk.GetProcessedImageGrayscale16bNumpyArray(CONTEXT, -1)


def stack_images(images: list[np.ndarray[np.uint16]]) -> np.ndarray[np.uint32]:
    """Stack images by summing pixel values."""
    return np.sum(images, axis=0, dtype=np.uint32)


def median_images(images: list[np.ndarray[np.uint16]]) -> np.ndarray[np.uint16]:
    """Return an image with the median of the pixel values of the images."""
    return np.median(images, axis=0)


def write_to_fits(image: np.ndarray[np.uint16 | np.uint32], annotation: str = "") -> str:
    global FILENAME_NUM, FITS_HEADER
    FILENAME_NUM += 1
    FITS_HEADER["DATE-OBS"] = datetime.now(timezone.utc).strftime('%F %T.%f')[:-3]
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


def show_image(image: np.ndarray[np.uint16] | np.ndarray[np.uint32]) -> None:
    # Need to be careful to not modify complex data types
    # display_image = np.array(Image.fromarray(image, mode="RGBA").convert("L")) if image.dtype == np.uint32 else image
    display_image = image.astype(np.uint16) if image.dtype == np.uint32 else image
    cv2.imshow("CRED2 Camera", display_image)
    cv2.waitKey(1)


def check_identical_images(image1: np.ndarray[np.uint16], image2: np.ndarray[np.uint16]) -> None:
    # If the two images are identical, restart the camera
    if image1.shape != image2.shape or not np.all(np.isclose(image1, image2)):
        return
    print("Two consecutive identical images detected.")
    restart_camera()


########## Threads ##########
read_queue = queue.Queue()
write_queue = queue.Queue()
compress_queue = queue.Queue()
display_queue = queue.Queue()

read_th: threading.Thread = None
write_th: threading.Thread = None
compress_th: threading.Thread = None
display_th: threading.Thread = None

stopping_event = threading.Event()
stop_event = threading.Event()
stop_read_event = threading.Event()
continue_taking_images = threading.Event()  # If False, will pause taking images
continue_taking_images.set()

STOP = "STOP"


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

    stop_read_event.set()
    if read_th and not script_done:
        print("Stopping read thread...", flush=True)
        if not continue_taking_images.is_set():
            continue_taking_images.set()  # To make read thread stop
        sleep(0.1)
        pause_captures()
        sleep(0.5)
        read_th.join(timeout=IMAGE_CHUNK_TIME * 5)
        if read_th.is_alive():
            print("Read thread failed to stop.", flush=True)
    if CONTEXT:
        print("Disconnecting from camera...", flush=True)
        disconnect()

    exit()


def pause_captures() -> None:
    print("Pausing image captures.")
    FliSdk.Stop(CONTEXT)
    continue_taking_images.clear()


def resume_captures() -> None:
    print("Resuming image captures.")
    start_captures()
    continue_taking_images.set()


def start_captures() -> None:
    if FliSdk.IsStarted(CONTEXT):
        return
    print("Starting image captures.")
    FliSdk.Start(CONTEXT)
    sleep(2)


def reset_buffer() -> None:
    global CAMERA_BUFFER_RESET_TIME
    print("Resetting camera buffer...")
    pause_captures()
    sleep(4)
    FliSdk.ResetBuffer(CONTEXT)
    sleep(4)
    resume_captures()
    CAMERA_BUFFER_RESET_TIME = datetime.now()


def take_one_capture(quiet=False) -> None:
    if not quiet:
        print("Taking one exposure.")
    resume_captures()
    take_stacked_exposure()
    pause_captures()


def take_stacked_exposure(stack_size=IMAGE_STACK_SIZE, write=True) -> np.ndarray[np.uint32]:
    if stack_size > IMAGE_CHUNK_SIZE:
        images = []
        for _ in range(stack_size // IMAGE_CHUNK_SIZE):
            images.extend(get_image() for _ in range(IMAGE_CHUNK_SIZE))
            if stop_read_event.is_set():
                return
            image = stack_images(images)
            images.clear()
            images.append(image)

        remaining_images = stack_size % IMAGE_CHUNK_SIZE
        if remaining_images:
            images.extend(get_image() for _ in range(remaining_images))
            if stop_read_event.is_set():
                return
            image = stack_images(images)
    else: 
        images = [get_image() for _ in range(stack_size)]
        if stop_read_event.is_set():
            return
        image = stack_images(images)

    if write:
        write_queue.put(image)

    if datetime.now() - CAMERA_BUFFER_RESET_TIME > timedelta(seconds=CAMERA_BUFFER_RESET_INTERVAL):
        print("Briefly stopping and resuming exposures to reset buffer...")
        reset_buffer()

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
    if stop_read_event.is_set():
        return

    if not TAKE_CALIBRATION_IMAGES:
        initialize_image_callback()
    else:
        resume_captures()

    if IMAGE_STACK_SIZE > 1:
        if CONTINUOUS_CAPTURE:
            while not stop_read_event.is_set():
                take_stacked_exposure()
        else:
            for _ in tqdm(range(NUM_IMAGES), unit="images"):
                take_stacked_exposure()
                read_images += 1
                if stop_event.is_set():
                    break
    else:
        if CONTINUOUS_CAPTURE:
            while not stop_read_event.is_set():
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
        path = write_to_fits(image)
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
        compress_queue.task_done()

        if len(compress_group_paths) >= COMPRESS_GROUP_SIZE:
            while sum(1 for p in psutil.process_iter() if p.name() == "fpack.exe") >= MAX_COMPRESS_PROCESSES and not stop_event.is_set():
                sleep(0.5)
            compress_group(compress_group_paths)
            compress_group_paths.clear()


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
    global write_th, compress_th, display_th
    write_th = threading.Thread(target=write_thread)
    write_th.start()
    display_th = threading.Thread(target=display_thread)
    display_th.start()
    
    if ENABLE_COMPRESSION:
        compress_th = threading.Thread(target=compress_thread)
        compress_th.start()
    
    print('-' * 40)
    print("Press CTRL+C to stop the control code.")
    print(f"Stacked exposure time: {IMAGE_STACK_TIME / TIME_SCALE_FACTOR} seconds.")
    print(f"Individual frame exposure time: {FRAME_TIME} seconds ({FPS} FPS).")

    if STARTUP_ONLY:
        print("In STARTUP ONLY mode.")
        print("Control code started. Not capturing images yet.")
    elif MANUAL_MODE:
        print("In MANUAL CAPTURE mode.")
        print("Press any key to manually take one exposure.")
        while True:
            try:
                input()
                take_one_capture(quiet=True)
                for _ in tqdm(range(int(IMAGE_STACK_TIME / TIME_SCALE_FACTOR)), desc="Exposing", unit="s"):
                    sleep(1)
                    if stop_event.is_set():
                        break
            except (KeyboardInterrupt, EOFError):
                stop_threads()
                break
    elif CONTINUOUS_CAPTURE:
        print("In CONTINUOUS CAPTURE mode.")
        global read_th
        read_th = threading.Thread(target=read_thread)
        read_th.start()
        print("Capturing images continuously until stopped.")
    else:
        print("In FIXED NUMBER mode.")
        global read_th
        read_th = threading.Thread(target=read_thread)
        read_th.start()
        print(f"Number of images: {NUM_IMAGES}.")
        print(f"Total run time: {NUM_IMAGES * (IMAGE_STACK_TIME / TIME_SCALE_FACTOR)} seconds.")

    # display_thread()
    # TODO: Maybe monitor threads?
    # Keep the main thread alive so that it can catch signals
    while True:
        sleep(0.01)


if __name__ == "__main__":
    main()
