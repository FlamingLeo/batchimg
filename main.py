#!/usr/bin/env python3
from tkinter import *
from tkinter import ttk, filedialog, messagebox, colorchooser
from idlelib.tooltip import Hovertip
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageStat
import threading
import os
import re

VERSION = "1.1"
DATE = "31.03.2024"
CWD = os.path.abspath(os.getcwd()).replace(os.sep, '/')
INPUT_PATH = os.path.join(CWD, 'input').replace(os.sep, '/')
OUTPUT_PATH = os.path.join(CWD, 'output').replace(os.sep, '/')
FILL_COLOR = "#000000"
RESIZE_REGEX = re.compile("^(?:\d+%?x\d+%?|\d+%|\d+x\d+)$")
CROP_REGEX = re.compile("^(?:\d+%?)(?:,\s*\d+%?){3}$")
ACTIVE_THREADS = []
THREAD_COUNT = 0
IMG_COUNT = 0
ERR_COUNT = 0

# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
SAVE_FORMATS = [
    "BLP",  # blp_version (str): "BLP1" or "BLP2" (default)
    "BMP",
    "DDS",
    "DIB",
    "EPS",
    "GIF",  # save_all (bool), interlace (bool)
    "ICNS",
    "ICO",
    "IM",
    "JPEG",  # quality (0-95 or "keep"), optimize (bool), progressive (bool)
    "JFIF",  # same as above
    "JP2",
    "MSP",
    "PCX",
    "PDF",  # save_all (bool)
    "PNG",  # optimize (bool)
    "PBM",
    "PGM",
    "PPM",
    "PNM",
    "SGI",
    "SPI",  # format='SPIDER' has to be provided, extension can be any 3 alphanumeric characters
    "TGA",
    "TIFF",  # save_all (bool)
    "WebP",  # lossless (bool), quality (0-100, def. 80)
    "XBM"
]

MODES = [
    "1",  # values can be directly used
    "L",
    "P",
    "RGB",
    "RGBA",
    "CMYK",
    "YCbCr",
    "LAB",
    "HSV",
    "I",
    "F"
]

RESAMPLING = [
    "NEAREST",  # indices correspond to value
    "LANCZOS",
    "BILINEAR",
    "BICUBIC",
    "BOX",
    "HAMMING",
]

TRANSPOSE = [
    "FLIP_LEFT_RIGHT",  # indices correspond to value
    "FLIP_TOP_BOTTOM",
    "ROTATE_90",
    "ROTATE_180",
    "ROTATE_270"
]

RESIZING = [
    "Contain",
    "Cover",
    "Fit",
    "Pad"
]


def how_to():
    """
    Opens up a new window explaining how the program works.
    """
    help_window = Toplevel()
    help_window.resizable(False, False)

    help_window.title("BatchIMG: Help")

    help_text = """
    To use BatchIMG, you must first select a valid input (source) and
    a valid output (destination) directory. Your source directory will 
    contain the images to operate on.
    
    You may select multiple effects and transformation options, if
    they are compatible with one another, as represented by a possible
    error message.
    
    To learn the syntax / meaning of each option, hover your mouse over
    the corresponding label.
    
    Descriptions taken from the Pillow 10.2.0 documentation:
    https://pillow.readthedocs.io/
    
    IMPORTANT:
    Effects are applied top to bottom, left to right, sequentially. 
    For example, if you have selected "Resize", "Blur", "Smooth", the 
    image will first be resized, then blurred, then finally smoothed. 
    This may lead to some unwanted side effects, such as selecting a 
    border fill color, then grayscaling the image, which will lead to 
    the fill color also becoming grayscaled.
    
    To avoid this, you will need to run the batch processing multiple
    times (e.g. first grayscaling the images, then expanding them).
    
    This also applies to tabs: the operations in the "Transform" tab
    are applied before the operations in the "Advanced" tab.
    
    Some effects are also incompatible with some modes. As a workaround,
    first convert the images to the fitting modes, then try applying the
    effects again.
    """

    ttk.Label(help_window, text=re.sub(' +', ' ', help_text.strip())).pack(
        padx=5, pady=5, anchor=W)
    ttk.Button(help_window, text="Close",
               command=help_window.destroy).pack(padx=5, pady=5)


def about():
    """
    Opens up a new About messagebox.
    """
    messagebox.showinfo(
        "About BatchIMG", "BatchIMG: A GUI for image batch processing.\n" +
        "Developed by FlamingLeo, 2024.\n\n" +
        f"Version {VERSION}, finished {DATE}.\nMade using Python, Pillow and tkinter.\n\n" +
        "PyPI (Pillow): \nhttps://pypi.org/project/pillow/")


def check_on_close():
    """
    Checks for active threads on close.
    If there are still active threads, warn the user about closing the program.
    """
    running_threads = False
    for thread in ACTIVE_THREADS:
        if thread.is_alive():
            running_threads = True
            break

    if running_threads:
        if messagebox.askokcancel("Ongoing Operations", "There are still ongoing operations.\nAre you sure you want to quit?"):
            root.destroy()
    else:
        root.destroy()


def save_logs():
    """
    Saves the logs to an external text file in the same directory as the program.
    """
    try:
        if log_listbox.size():
            with open("logs.txt", "w") as file:
                for listbox_entry in enumerate(log_listbox.get(0, END)):
                    file.write(listbox_entry[1] + "\n")
    except:
        pass


def set_input_path():
    """
    Set input (source) directory and replace input entry box.
    """
    global INPUT_PATH
    INPUT_PATH = filedialog.askdirectory()
    if INPUT_PATH:
        general_input_entry.delete(0, END)
        general_input_entry.insert(0, INPUT_PATH)


def set_output_path():
    """
    Set output (destination) directory and replace output entry box.
    """
    global OUTPUT_PATH
    OUTPUT_PATH = filedialog.askdirectory()
    if OUTPUT_PATH:
        general_output_entry.delete(0, END)
        general_output_entry.insert(0, OUTPUT_PATH)


def set_fill_color():
    """
    Set fill color for expanding.
    """
    global FILL_COLOR
    color = colorchooser.askcolor()[1]
    FILL_COLOR = color if color is not None else FILL_COLOR


def replace_input_path():
    """
    Pastes and replaces input path if the clipboard is not empty.
    """
    if root.clipboard_get():
        general_input_entry.delete(0, END)
        general_input_entry.insert(0, root.clipboard_get())


def replace_output_path():
    """
    Pastes and replaces output path if the clipboard is not empty.
    """
    if root.clipboard_get():
        general_output_entry.delete(0, END)
        general_output_entry.insert(0, root.clipboard_get())


"""
------------------------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------UI functions start here.---------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------
"""


def ui_toggle_resize():
    """
    Enables / disables UI elements if resizing is chosen or not.
    """
    STATE = "readonly" if transform_resize.get() else "disabled"
    transform_resize_entry.config(
        state="normal" if transform_resize.get() else "disabled")
    transform_resize_combobox.config(state=STATE)
    transform_contain_radio.config(state=STATE)
    transform_cover_radio.config(state=STATE)
    transform_fit_radio.config(state=STATE)
    transform_pad_radio.config(state=STATE)


def ui_toggle_transpose():
    """
    Enables / disables UI elements if transposing is chosen or not.
    """
    transform_transpose_combobox.config(
        state="readonly" if transform_transpose.get() else "disabled")


def ui_toggle_crop():
    """
    Enables / disables UI elements if cropping is chosen or not.
    """
    transform_crop_entry.config(
        state="normal" if transform_crop.get() else "disabled")


def ui_toggle_scale():
    """
    Enables / disables UI elements if scaling is chosen or not.
    """
    transform_scale_entry.config(
        state="normal" if transform_scale.get() else "disabled")
    transform_scale_combobox.config(
        state="readonly" if transform_scale.get() else "disabled")


def ui_toggle_expand():
    """
    Enables / disables UI elements if expanding is chosen or not.
    """
    transform_expand_entry.config(
        state="normal" if transform_expand.get() else "disabled")
    transform_expand_button.config(
        state="normal" if transform_expand.get() else "disabled")


def ui_toggle_posterize():
    """
    Enables / disables UI elements if posterize is chosen or not.
    """
    transform_posterize_entry.config(
        state="normal" if transform_posterize.get() else "disabled")


def ui_toggle_solarize():
    """
    Enables / disables UI elements if solarize is chosen or not.
    """
    transform_solarize_entry.config(
        state="normal" if transform_solarize.get() else "disabled")


def ui_toggle_color():
    """
    Enables / disables UI elements if color is chosen or not.
    """
    transform_color_entry.config(
        state="normal" if transform_color.get() else "disabled")


def ui_toggle_contrast():
    """
    Enables / disables UI elements if contrast is chosen or not.
    """
    transform_contrast_entry.config(
        state="normal" if transform_contrast.get() else "disabled")


def ui_toggle_brightness():
    """
    Enables / disables UI elements if brightness is chosen or not.
    """
    transform_brightness_entry.config(
        state="normal" if transform_brightness.get() else "disabled")


def ui_toggle_sharpness():
    """
    Enables / disables UI elements if sharpness is chosen or not.
    """
    transform_sharpness_entry.config(
        state="normal" if transform_sharpness.get() else "disabled")


def ui_toggle_filetype():
    """
    Enables / disables UI elements if filetype conversion is chosen or not.
    """
    advanced_convert_filetype_combobox.config(
        state="readonly" if advanced_convert_filetype.get() else "disabled")


def ui_toggle_mode():
    """
    Enables / disables UI elements if mode conversion is chosen or not.
    """
    advanced_convert_modes_combobox.config(
        state="readonly" if advanced_convert_modes.get() else "disabled")


def ui_toggle_stats():
    """
    Enables / disables UI elements if statistics showcase is chosen or not.
    """
    STATE = "normal" if advanced_stats.get() else "disabled"
    advanced_extrema_checkbutton.config(state=STATE)
    advanced_count_checkbutton.config(state=STATE)
    advanced_sum_checkbutton.config(state=STATE)
    advanced_sum2_checkbutton.config(state=STATE)
    advanced_mean_checkbutton.config(state=STATE)
    advanced_median_checkbutton.config(state=STATE)
    advanced_rms_checkbutton.config(state=STATE)
    advanced_var_checkbutton.config(state=STATE)
    advanced_stddev_checkbutton.config(state=STATE)


"""
------------------------------------------------------------------------------------------------------------------------------------------
-------------------------------------------------------Helper functions start here.-------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------
"""


def insert_log(msg):
    """
    Helper method to insert string into listbox and move view to end of listbox.
    """
    log_listbox.insert(END, msg)
    log_listbox.yview(END)


def format_size_1d(dim, size):
    """
    Helper method to format the size of an image in one dimension.
    If the input contains a percentage, the corresponding dimension in pixels is calculated.
    Otherwise, return the dimension as is.
    """
    return int(float(dim.split("%")[0]) / 100.0 * size) if '%' in dim else int(dim)


def is_float(string):
    """
    Helper method to determine if string is float. 
    Returns corresponding boolean.
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


def check(val, func, img):
    """
    Helper method. Performs a function only if the checkbutton is checked.
    Yes, this is just a fancy wrapper for if-statements and try-catch-expressions.
    """
    global ERR_COUNT
    if val.get():
        try:
            img = func(img)
        except Exception as e:
            insert_log(f"[ERROR] {str(e)}")
            ERR_COUNT += 1
    return img


def check2(val, func, arg1, arg2):
    """
    Helper method for functions with 2 arguments.
    """
    global ERR_COUNT
    if val.get():
        try:
            arg2 = func(arg1, arg2)
        except Exception as e:
            insert_log(f"[ERROR] {str(e)}")
            ERR_COUNT += 1
    return arg2


"""
------------------------------------------------------------------------------------------------------------------------------------------
-------------------------------------------------Image modification functions start here.-------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------
"""


def func_transform_resize(img):
    """
    Resizes image based on input and resampling selection.
    Returns resized image if entry has valid pattern, otherwise returns unmodified image.
    """
    input = transform_resize_entry.get()
    greater_than = input.split(">")
    less_than = input.split("<")
    new_size = greater_than[0] if len(greater_than) == 2 else less_than[0]

    # check if resizing regex matches input, otherwise don't resize
    if RESIZE_REGEX.match(new_size):
        # check if input is either single percentage (n%) or contains 2 sizes (n x n) to determine new size
        size_input = new_size.split("x")

        if len(size_input) == 2:
            new_size = (format_size_1d(size_input[0], img.width), format_size_1d(
                size_input[1], img.height))
        else:
            new_size = (format_size_1d(size_input[0], img.width), format_size_1d(
                size_input[0], img.height))

        # if one of the dimensions is 0, return default image to prevent division by zero
        if new_size[0] == 0 or new_size[1] == 0:
            insert_log(
                "[WARN] Invalid resize parameter(s). No resizing performed.")
            return img

        # resize based on radio button value (0: contain, 1: cover, 2: fit, 3: pad)
        # also check if greater than / less than dimensions have been specified and fit
        if len(greater_than) == 2:
            if RESIZE_REGEX.match(greater_than[1]):
                resize_input = greater_than[1].split("x")
                if len(resize_input) != 2:
                    insert_log(
                        "[WARN] Invalid resize parameter(s). No resizing performed.")
                    return img
                if resize_input[0].isnumeric() and resize_input[1].isnumeric():
                    new_width = int(resize_input[0])
                    new_height = int(resize_input[0])
                else:
                    insert_log(
                        "[WARN] Invalid resize parameter(s). No resizing performed.")
                    return img
                if img.width < new_width or img.height < new_height:
                    insert_log(
                        f"[INFO] Image dimension(s) less than {new_width}x{new_height}. Skipping.")
                    return img
            else:
                insert_log(
                    "[WARN] Invalid resize parameter(s). No resizing performed.")
                return img

        elif len(less_than) == 2:
            if RESIZE_REGEX.match(less_than[1]):
                resize_input = less_than[1].split("x")
                if len(resize_input) != 2:
                    insert_log(
                        "[WARN] Invalid resize parameter(s). No resizing performed.")
                    return img
                if resize_input[0].isnumeric() and resize_input[1].isnumeric():
                    new_width = int(resize_input[0])
                    new_height = int(resize_input[0])
                else:
                    insert_log(
                        "[WARN] Invalid resize parameter(s). No resizing performed.")
                    return img
                if img.width > new_width or img.height > new_height:
                    insert_log(
                        f"[INFO] Image dimension(s) greater than {new_width}x{new_height}. Skipping.")
                    return img
            else:
                insert_log(
                    "[WARN] Invalid resize parameter(s). No resizing performed.")
                return img

        resize_method = RESAMPLING.index(transform_resize_resample.get())
        match transform_resize_type.get():
            case 0:
                img = ImageOps.contain(img, new_size, method=resize_method)
            case 1:
                img = ImageOps.cover(img, new_size, method=resize_method)
            case 2:
                img = ImageOps.fit(img, new_size, method=resize_method)
            case 3:
                img = ImageOps.pad(img, new_size, method=resize_method)
        insert_log(
            f"[TRANSFORM] Resized image using {transform_resize_resample.get()} ({RESIZING[transform_resize_type.get()]}, {img.width}x{img.height}).")
    else:
        insert_log(
            "[WARN] Incorrect resize syntax. No resizing performed.")
    return img


def func_transform_transpose(img):
    """
    Transposes image based on selection.
    Returns the transposed image.
    """
    img = img.transpose(TRANSPOSE.index(transform_transpose_mode.get()))
    insert_log(
        f"[TRANSFORM] Transposed image using {transform_transpose_mode.get()}.")
    return img


def func_transform_crop(img):
    """
    Crops an image based on input.
    Returns the cropped image if entry has valid pattern and valid coordinates, otherwise returns unmodified image.
    """
    coordinates = transform_crop_entry.get()

    # check if entry matches regex, otherwise don't crop
    if CROP_REGEX.match(coordinates):
        left, upper, right, lower = list(
            map(str.strip, coordinates.split(",")))
        left = (format_size_1d(left, img.width)) if '%' in left else int(left)
        upper = (format_size_1d(upper, img.height)
                 ) if '%' in upper else int(upper)
        right = (img.width - format_size_1d(right, img.width)
                 ) if '%' in right else int(right)
        lower = (img.height - format_size_1d(lower, img.height)
                 ) if '%' in lower else int(lower)

        # check for invalid dimensions
        if left < right and upper < lower and right != 0 and lower != 0:
            img = img.crop((left, upper, right, lower))
            insert_log(
                f"[TRANSFORM] Cropped image region ({left}, {upper}, {right}, {lower}).")
        else:
            insert_log(
                "[WARN] Invalid cropping dimensions. No cropping performed.")
    else:
        insert_log("[WARN] Incorrect cropping syntax. No cropping performed.")
    return img


def func_transform_scale(img):
    """
    Scales image based on input and resampling selection.
    Returns scaled image if input is valid, otherwise returns original image.
    """
    factor = transform_scale_entry.get()
    if is_float(factor) and float(factor) > 0:
        scale_method = RESAMPLING.index(transform_scale_resample.get())
        img = ImageOps.scale(img, float(factor), resample=scale_method)
        insert_log(
            f"[TRANSFORM] Scaled image with factor {factor} using {RESAMPLING[scale_method]}.")
    else:
        insert_log(f"[WARN] Invalid scaling factor. No scaling performed.")
    return img


def func_transform_expand(img):
    """
    Adds border to image.
    Returns expanded image if input is valid, otherwise returns original image.
    """
    border = transform_expand_entry.get()
    if border.isnumeric():
        img = ImageOps.expand(img, int(border), FILL_COLOR)
        insert_log(
            f"[TRANSFORM] Expanded image by {border} pixels with color {FILL_COLOR}.")
    else:
        insert_log(f"[WARN] Invalid border width. No expanding performed.")
    return img


def func_transform_flip(img):
    """
    Flips image.
    Returns flipped image.
    """
    img = ImageOps.flip(img)
    insert_log("[TRANSFORM] Flipped image.")
    return img


def func_transform_mirror(img):
    """
    Mirrors image.
    Returns mirrored image.
    """
    img = ImageOps.mirror(img)
    insert_log("[TRANSFORM] Mirrored image.")
    return img


def func_transform_equalize(img):
    """
    Equalizes image histogram.
    Returns image with equalized histogram.
    """
    img = ImageOps.equalize(img, mask=None)
    insert_log("[TRANSFORM] Equalized image histogram.")
    return img


def func_transform_grayscale(img):
    """
    Grayscales image.
    Returns grayscaled image.
    """
    img = ImageOps.grayscale(img)
    insert_log("[TRANSFORM] Grayscaled image.")
    return img


def func_transform_invert(img):
    """
    Inverts image.
    Returns inverted image.
    """
    img = ImageOps.invert(img)
    insert_log("[TRANSFORM] Inverted image.")
    return img


def func_transform_posterize(img):
    """
    Reduces the number of bits for each color channel.
    Returns posterized image or original image if argument is invalid.
    """
    bits = transform_posterize_entry.get()
    if bits.isnumeric() and int(bits) > 0 and int(bits) < 9:
        img = ImageOps.posterize(img, int(bits))
        insert_log(f"[TRANSFORM] Posterized image, kept {bits} bit(s).")
    else:
        insert_log(
            "[WARN] Invalid posterize argument. Did not posterize image.")
    return img


def func_transform_solarize(img):
    """
    Inverts all pixel values above a threshold.
    Returns solarized image or original image if argument is invalid.
    """
    threshold = transform_solarize_entry.get()
    if threshold.isnumeric() and int(threshold) >= 0:
        img = ImageOps.solarize(img, int(threshold))
        insert_log(f"[TRANSFORM] Solarized image with threshold {threshold}.")
    else:
        insert_log(
            "[WARN] Invalid solarize argument. Did not solarize image.")
    return img


def func_transform_blur(img):
    """
    Applies blur filter to image.
    Returns blurred image.
    """
    img = img.filter(ImageFilter.BLUR)
    insert_log("[TRANSFORM] Applied blur to image.")
    return img


def func_transform_contour(img):
    """
    Applies contour filter to image.
    Returns contoured image.
    """
    img = img.filter(ImageFilter.CONTOUR)
    insert_log("[TRANSFORM] Applied contour to image.")
    return img


def func_transform_detail(img):
    """
    Applies detail filter to image.
    Returns detailed image.
    """
    img = img.filter(ImageFilter.DETAIL)
    insert_log("[TRANSFORM] Applied detail to image.")
    return img


def func_transform_edge_enhance(img):
    """
    Applies edge enhance filter to image.
    Returns edge enhanced image.
    """
    img = img.filter(ImageFilter.EDGE_ENHANCE)
    insert_log("[TRANSFORM] Applied edge enhance to image.")
    return img


def func_transform_edge_enhance_more(img):
    """
    Applies more edge enhance filter to image.
    Returns more edge enhanced image.
    """
    img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    insert_log("[TRANSFORM] Applied more edge enhance to image.")
    return img


def func_transform_emboss(img):
    """
    Applies emboss filter to image.
    Returns embossed image.
    """
    img = img.filter(ImageFilter.EMBOSS)
    insert_log("[TRANSFORM] Applied emboss to image.")
    return img


def func_transform_find_edges(img):
    """
    Applies edgefind filter to image.
    Returns image with edge find filter.
    """
    img = img.filter(ImageFilter.FIND_EDGES)
    insert_log("[TRANSFORM] Applied edgefind to image.")
    return img


def func_transform_sharpen(img):
    """
    Applies sharpen filter to image.
    Returns sharpened image.
    """
    img = img.filter(ImageFilter.SHARPEN)
    insert_log("[TRANSFORM] Applied sharpen to image.")
    return img


def func_transform_smooth(img):
    """
    Applies smooth filter to image.
    Returns smoothed image.
    """
    img = img.filter(ImageFilter.SMOOTH)
    insert_log("[TRANSFORM] Applied smoothing to image.")
    return img


def func_transform_smooth_more(img):
    """
    Applies more smooth filter to image.
    Returns more smoothed image.
    """
    img = img.filter(ImageFilter.SMOOTH_MORE)
    insert_log("[TRANSFORM] Applied more smoothing to image.")
    return img


def func_transform_color(img):
    """
    Enhances color of image based on input.
    Returns enhanced image or original image if input is invalid.
    """
    factor = transform_color_entry.get()
    if is_float(factor) and float(factor) >= 0:
        img = ImageEnhance.Color(img).enhance(float(factor))
        insert_log(
            f"[TRANSFORM] Enhanced color of image with factor {factor}.")
    else:
        insert_log("[WARN] Invalid color factor. No enhancing performed.")
    return img


def func_transform_contrast(img):
    """
    Enhances contrast of image based on input.
    Returns enhanced image or original image if input is invalid.
    """
    factor = transform_contrast_entry.get()
    if is_float(factor) and float(factor) >= 0:
        img = ImageEnhance.Contrast(img).enhance(float(factor))
        insert_log(
            f"[TRANSFORM] Enhanced contrast of image with factor {factor}.")
    else:
        insert_log("[WARN] Invalid contrast factor. No enhancing performed.")
    return img


def func_transform_brightness(img):
    """
    Enhances brightness of image based on input.
    Returns enhanced image or original image if input is invalid.
    """
    factor = transform_brightness_entry.get()
    if is_float(factor) and float(factor) >= 0:
        img = ImageEnhance.Brightness(img).enhance(float(factor))
        insert_log(
            f"[TRANSFORM] Enhanced brightness of image with factor {factor}.")
    else:
        insert_log("[WARN] Invalid brightness factor. No enhancing performed.")
    return img


def func_transform_sharpness(img):
    """
    Enhances sharpness of image based on input.
    Returns sharpened image or original image if input is invalid.
    """
    factor = transform_sharpness_entry.get()
    if is_float(factor) and float(factor) >= 0:
        img = ImageEnhance.Sharpness(img).enhance(float(factor))
        insert_log(
            f"[TRANSFORM] Enhanced sharpness of image with factor {factor}.")
    else:
        insert_log("[WARN] Invalid sharpness factor. No enhancing performed.")
    return img


def func_advanced_convert_filetype(img_extension):
    """
    Converts the filetype of the image.
    Returns the new extension of the image as ".ext"
    """
    new_type = advanced_convert_filetype_option.get()
    img_extension = f".{new_type.lower()}"
    insert_log(f"[ADVANCED] Converted image to filetype {new_type}.")
    return img_extension


def func_advanced_convert_mode(img):
    """
    Converts the mode of the image.
    Returns the image with the converted mode.
    """
    new_mode = advanced_convert_modes_option.get()
    img = img.convert(new_mode)
    insert_log(f"[ADVANCED] Converted image to mode {new_mode}.")
    return img


def process(img):
    """
    Process an image based on selected options.
    Returns the modified Image object, the image name, the final extension and everything to be included in the image statistics post-modification.
    """
    img_name = os.path.splitext(os.path.basename(img.filename))[0]
    img_extension = os.path.splitext(img.filename)[1]
    img_name_full = os.path.split(img.filename)[1]
    img_stats = ""

    insert_log(
        f"[FILE] Processing {img_name_full} ({img.format}, {img.width}x{img.height}, {img.mode})...")

    # transform: transform
    img = check(transform_resize, func_transform_resize, img)
    img = check(transform_transpose, func_transform_transpose, img)
    img = check(transform_crop, func_transform_crop, img)
    img = check(transform_scale, func_transform_scale, img)
    img = check(transform_expand, func_transform_expand, img)

    # transform: operations
    img = check(transform_flip, func_transform_flip, img)
    img = check(transform_mirror, func_transform_mirror, img)
    img = check(transform_equalize, func_transform_equalize, img)
    img = check(transform_grayscale, func_transform_grayscale, img)
    img = check(transform_invert, func_transform_invert, img)
    img = check(transform_posterize, func_transform_posterize, img)
    img = check(transform_solarize, func_transform_solarize, img)

    # transform: filters
    img = check(transform_blur, func_transform_blur, img)
    img = check(transform_contour, func_transform_contour, img)
    img = check(transform_detail, func_transform_detail, img)
    img = check(transform_edge_enhance, func_transform_edge_enhance, img)
    img = check(transform_edge_enhance_more,
                func_transform_edge_enhance_more, img)
    img = check(transform_emboss, func_transform_emboss, img)
    img = check(transform_find_edges, func_transform_find_edges, img)
    img = check(transform_sharpen, func_transform_sharpen, img)
    img = check(transform_smooth, func_transform_smooth, img)
    img = check(transform_smooth_more, func_transform_smooth_more, img)

    # transform: enhancements
    img = check(transform_color, func_transform_color, img)
    img = check(transform_contrast, func_transform_contrast, img)
    img = check(transform_brightness, func_transform_brightness, img)
    img = check(transform_sharpness, func_transform_sharpness, img)

    # advanced: conversion
    img_extension = check(advanced_convert_filetype,
                          func_advanced_convert_filetype, img_extension)
    img = check(advanced_convert_modes, func_advanced_convert_mode, img)

    # advanced: statistics
    if advanced_stats.get():
        img_stats += f"extrema:{str(img.getextrema())}\n" if advanced_extrema.get() else ""
        img_stats += f"count:{str(ImageStat.Stat(img).count)}\n" if advanced_count.get() else ""
        img_stats += f"sum:{str(ImageStat.Stat(img).sum)}\n" if advanced_sum.get() else ""
        img_stats += f"sum2:{str(ImageStat.Stat(img).sum2)}\n" if advanced_sum2.get() else ""
        img_stats += f"mean:{str(ImageStat.Stat(img).mean)}\n" if advanced_mean.get() else ""
        img_stats += f"median:{str(ImageStat.Stat(img).median)}\n" if advanced_median.get() else ""
        img_stats += f"rms:{str(ImageStat.Stat(img).rms)}\n" if advanced_rms.get() else ""
        img_stats += f"var:{str(ImageStat.Stat(img).var)}\n" if advanced_var.get() else ""
        img_stats += f"stddev:{str(ImageStat.Stat(img).stddev)}\n" if advanced_stddev.get() else ""

    # finished image processing
    insert_log(f"[FILE] Successfully processed {img_name_full}.")
    return (img, img_name, img_extension, img_stats)


def start_processing():
    """
    Perform image batch processing for each image in a directory and log errors.
    Optionally, log statistics for each image post-modification in an associated .txt file. 
    """
    global THREAD_COUNT, IMG_COUNT, ERR_COUNT
    INPUT_PATH = general_input_entry.get()
    OUTPUT_PATH = general_output_entry.get()

    IMG_COUNT = 0
    ERR_COUNT = 0
    in_directory = ""
    out_directory = ""

    try:
        in_directory = os.fsencode(INPUT_PATH)
        out_directory = os.fsencode(OUTPUT_PATH)
    except Exception as e:
        insert_log(f"[ERROR] {str(e)}")
        THREAD_COUNT = 0 if THREAD_COUNT < 0 else (THREAD_COUNT - 1)
        log_active_label.config(text=f"Active Threads: {THREAD_COUNT}")
        return

    in_files = []
    out_files = []

    insert_log("[INFO] Started processing job.")

    # create directories if they do not exist
    try:
        if not os.path.exists(in_directory):
            os.makedirs(in_directory)
        if not os.path.exists(out_directory):
            os.makedirs(out_directory)
    except Exception as e:
        insert_log(f"[ERROR] {str(e)}")
        THREAD_COUNT = 0 if THREAD_COUNT < 0 else (THREAD_COUNT - 1)
        log_active_label.config(text=f"Active Threads: {THREAD_COUNT}")
        return

    # check if any file has the same name and warn user if overwrite checkbox not checked
    for file in os.listdir(in_directory):
        in_files.append(os.fsdecode(os.path.splitext(
            os.path.basename(file))[0]).lower().strip())

    for file in os.listdir(out_directory):
        out_files.append(os.fsdecode(os.path.splitext(
            os.path.basename(file))[0]).lower().strip())

    if not set(in_files).isdisjoint(out_files) and not general_overwrite.get():
        if not messagebox.askokcancel("Overwrite Images?", "At least one image has the same name in the output directory.\nAre you sure you want to overwrite these files?"):
            insert_log("[INFO] Aborted processing job.")
            THREAD_COUNT = 0 if THREAD_COUNT < 0 else (THREAD_COUNT - 1)
            log_active_label.config(text=f"Active Threads: {THREAD_COUNT}")
            return

    # try opening each file in directory as image, otherwise show error on load
    for file in os.listdir(in_directory):
        try:
            img_path = os.fsdecode(os.path.join(
                in_directory, file)).replace(os.sep, '/')
            img, img_name, img_extension, img_stats = process(
                Image.open(img_path))
            img_output_path = os.path.join(
                OUTPUT_PATH, img_name + img_extension).replace(os.sep, '/')

            # extension-specific options
            match img_extension:
                case ".spi":
                    insert_log("[FILE] Spider!")
                    img.save(img_output_path, format="SPIDER")
                case ".png" | ".gif" | ".mpo" | ".pdf" | ".tiff" | ".webp":
                    img.save(
                        img_output_path,
                        save_all=advanced_all_frames.get(),
                        interlace=advanced_interlace_gif.get(),
                        optimize=advanced_optimize.get(),
                        lossless=advanced_lossless_webp.get(),
                        quality=advanced_webp_quality.get())
                case _:
                    img.save(
                        img_output_path,
                        blp_version="BLP1" if advanced_blp1.get() else "BLP2",
                        optimize=advanced_optimize.get(),
                        progressive=advanced_progressive_jpeg.get(),
                        quality=advanced_jpg_quality.get())

            insert_log("[FILE] Applied extension-specific options.")
            insert_log(f"[FILE] Saved image: {img_output_path}")

            # store statistics in text file
            if img_stats:
                img_stats_output_path = os.path.join(
                    OUTPUT_PATH, img_name + ".txt").replace(os.sep, '/')
                with open(img_stats_output_path, "w") as file:
                    file.write(img_stats)
                insert_log(
                    f"[FILE] Saved statistics: {img_stats_output_path}.")

            IMG_COUNT += 1
        except Exception as e:
            insert_log(f"[ERROR] {str(e)}")
            ERR_COUNT += 1

    insert_log(
        f"[INFO] Finished processing {IMG_COUNT} images with {ERR_COUNT} error(s).")

    THREAD_COUNT = 0 if THREAD_COUNT < 0 else (THREAD_COUNT - 1)
    log_active_label.config(text=f"Active Threads: {THREAD_COUNT}")


def start_processing_threads():
    """
    Starts processing in a new thread.
    """
    global ACTIVE_THREADS, THREAD_COUNT
    worker_thread = threading.Thread(target=start_processing)
    worker_thread.start()
    ACTIVE_THREADS.append(worker_thread)
    THREAD_COUNT += 1
    log_active_label.config(text=f"Active Threads: {THREAD_COUNT}")


"""
------------------------------------------------------------------------------------------------------------------------------------------
--------------------------------------------------------Tkinter logic starts here.--------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------
"""
root = Tk()
root.resizable(False, False)
root.title(f"BatchIMG {VERSION}")

# menu bar
menu_bar = Menu(root)
root.config(menu=menu_bar)

file_menu = Menu(menu_bar, tearoff=False)
menu_bar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Set Input Path", command=set_input_path)
file_menu.add_command(label="Paste Input Path", command=replace_input_path)
file_menu.add_command(label="Set Output Path", command=set_output_path)
file_menu.add_command(label="Paste Output Path", command=replace_output_path)
file_menu.add_command(label="Begin Processing",
                      command=start_processing_threads)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)

logs_menu = Menu(menu_bar, tearoff=False)
menu_bar.add_cascade(label="Logs", menu=logs_menu)
logs_menu.add_command(label="Save Logs", command=save_logs)
logs_menu.add_command(label="Clear Logs",
                      command=lambda: log_listbox.delete(0, END))

help_menu = Menu(menu_bar, tearoff=False)
menu_bar.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Help", command=how_to)
help_menu.add_command(label="About", command=about)


# tabs
notebook = ttk.Notebook(root)
notebook.pack()

general_frame = Frame(notebook, width=350, height=425)
transform_frame = Frame(notebook, width=350, height=425)
advanced_frame = Frame(notebook, width=350, height=425)

general_frame.pack(fill="both", expand=1)
transform_frame.pack(fill="both", expand=1)
advanced_frame.pack(fill="both", expand=1)

notebook.add(general_frame, text="General")
notebook.add(transform_frame, text="Transform")
notebook.add(advanced_frame, text="Advanced")

pixel = PhotoImage(width=1, height=1)

"""
GENERAL TAB:
- input / output paths (local, remote)
- logging
"""

# I/O (src/dest) frame
general_io_frame = LabelFrame(
    general_frame, text="Input / Output Paths", padx=5, pady=5)
general_io_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)
general_io_frame.grid_columnconfigure(0, weight=1)

general_input_label = ttk.Label(general_io_frame, text="Input Path")
general_input_label.grid(padx=5, sticky=W, row=0, column=0)

general_input_entry = ttk.Entry(general_io_frame, width=35)
general_input_entry.grid(padx=5, sticky=E, row=0, column=1)

general_input_button = ttk.Button(
    general_io_frame, text="Browse", image=pixel, compound="c", width=7, command=set_input_path)
general_input_button.grid(padx=5, sticky=E, row=0, column=2)

general_output_label = ttk.Label(general_io_frame, text="Output Path")
general_output_label.grid(padx=5, sticky=W, row=1, column=0)

general_output_entry = ttk.Entry(general_io_frame, width=35)
general_output_entry.grid(padx=5, sticky=E, row=1, column=1)

general_output_button = ttk.Button(
    general_io_frame, text="Browse", image=pixel, compound="c", width=7, command=set_output_path)
general_output_button.grid(padx=5, sticky=E, row=1, column=2)

general_input_entry.insert(0, INPUT_PATH)
general_output_entry.insert(0, OUTPUT_PATH)

general_input_entry_rightclickmenu = Menu(general_input_entry, tearoff=False)
general_input_entry_rightclickmenu.add_command(
    label="Paste", command=replace_input_path)
general_input_entry_rightclickmenu.add_command(
    label="Browse", command=set_input_path)
general_input_entry_rightclickmenu.add_command(
    label="Clear", command=lambda: general_input_entry.delete(0, END))
general_input_entry.bind(
    "<Button-3>", lambda e: general_input_entry_rightclickmenu.tk_popup(e.x_root, e.y_root))

general_output_entry_rightclickmenu = Menu(general_output_entry, tearoff=False)
general_output_entry_rightclickmenu.add_command(
    label="Paste", command=replace_output_path)
general_output_entry_rightclickmenu.add_command(
    label="Browse", command=set_output_path)
general_output_entry_rightclickmenu.add_command(
    label="Clear", command=lambda: general_output_entry.delete(0, END))
general_output_entry.bind(
    "<Button-3>", lambda e: general_output_entry_rightclickmenu.tk_popup(e.x_root, e.y_root))

# logging
log_frame = LabelFrame(general_frame, text="Logs", padx=5, pady=5)
log_frame.pack(padx=5, pady=5, fill=X, expand=1)
log_frame_inner = Frame(log_frame)
log_frame_inner.pack()
log_frame_scrollbar = ttk.Scrollbar(log_frame_inner)
log_frame_scrollbar.pack(side=RIGHT, fill=Y)
log_listbox = Listbox(log_frame_inner, width=58, height=12,
                      yscrollcommand=log_frame_scrollbar.set)
log_listbox.pack()

log_rightclickmenu = Menu(log_frame, tearoff=False)
log_rightclickmenu.add_command(label="Save", command=save_logs)
log_rightclickmenu.add_command(
    label="Clear", command=lambda: log_listbox.delete(0, END))
log_listbox.bind(
    "<Button-3>", lambda e: log_rightclickmenu.tk_popup(e.x_root, e.y_root))

general_overwrite = IntVar(value=0)

log_info_checkbox = ttk.Checkbutton(
    log_frame, text="Overwrite Without Asking", variable=general_overwrite)
log_info_checkbox.pack(padx=5, side=LEFT)

log_active_label = ttk.Label(log_frame, text=f"Active Threads: {THREAD_COUNT}")
log_active_label.pack(side=RIGHT)

# begin processing
general_help_label = ttk.Label(
    general_frame, text="HINT: To find out what some options do, hover over their labels.")
general_help_label.pack(padx=5, pady=5)
general_begin_button = ttk.Button(
    general_frame, text="Begin", image=pixel, compound="c", width=60, command=start_processing_threads)
general_begin_button.pack(padx=5, pady=5)

"""
TRANSFORM TAB:
- resize images (percentage, absolute / resampling modes)
- crop images (percentage, absolute / L,R,T,B / modes)
- rotate, transpose
- operations (ImageOps)
- enhancements (ImageEnhance)
- filters (ImageFilter)
"""

# transform
transform_img_frame = LabelFrame(
    transform_frame, text="Transform", padx=5, pady=5)
transform_img_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)
transform_img_frame.grid_columnconfigure(0, weight=1)

transform_resize = IntVar(value=0)
transform_transpose = IntVar(value=0)
transform_crop = IntVar(value=0)
transform_scale = IntVar(value=0)
transform_expand = IntVar(value=0)

transform_resize_resample = StringVar()
transform_transpose_mode = StringVar()
transform_scale_resample = StringVar()

transform_resize_checkbutton = ttk.Checkbutton(
    transform_img_frame, text="Resize", variable=transform_resize, command=ui_toggle_resize)
transform_resize_checkbutton.grid(padx=5, sticky=W, row=0, column=0)
transform_resize_tooltip = Hovertip(
    transform_resize_checkbutton, "Possible Formats (interchangable):\n- Percentage (n%, e.g. 50%)\n- Dimensions (SIZExSIZE, e.g. 100x150)\n- Both (e.g. 50%x100)\n\nYou may also specify minimum / maximum\ndimensions for resizing with '>' or '<'.\n- '>': Resize only if image is bigger than nxn.\n e.g. 50%>200x200 will halve the image if it's bigger than 200x200.\n- '<': Resize only if image is smaller than nxn.\n e.g. 200%<200x200 will double the image if it's smaller than 200x200.")

transform_resize_entry = ttk.Entry(
    transform_img_frame, width=25)
transform_resize_entry.insert(END, "100%")
transform_resize_entry.config(state="disabled")
transform_resize_entry.grid(padx=5, sticky=E, row=0, column=1)

transform_resize_combobox = ttk.Combobox(
    transform_img_frame, state="disabled", width=15, textvariable=transform_resize_resample, values=RESAMPLING)
transform_resize_combobox.current(3)
transform_resize_combobox.grid(padx=5, sticky=E, row=0, column=2)

transform_resize_type = IntVar()
transform_resize_type_frame = ttk.Frame(transform_img_frame)
transform_resize_type_frame.grid(sticky=W, row=1, column=0, columnspan=3)

transform_contain_radio = ttk.Radiobutton(
    transform_resize_type_frame, text="Contain", variable=transform_resize_type, value=0, state="disabled")
transform_contain_radio.grid(padx=(5, 25), sticky=W, row=0, column=0)
transform_contain_tooltip = Hovertip(
    transform_contain_radio, "Returns a resized version of the image, set to the maximum width and\nheight within the requested size, while maintaining the original aspect ratio.")

transform_cover_radio = ttk.Radiobutton(
    transform_resize_type_frame, text="Cover", variable=transform_resize_type, value=1, state="disabled")
transform_cover_radio.grid(padx=30, sticky=W, row=0, column=1)
transform_cover_tooltip = Hovertip(
    transform_cover_radio, "Returns a resized version of the image, so that the requested\nsize is covered, while maintaining the original aspect ratio.")

transform_fit_radio = ttk.Radiobutton(
    transform_resize_type_frame, text="Fit", variable=transform_resize_type, value=2, state="disabled")
transform_fit_radio.grid(padx=30, sticky=W, row=0, column=2)
transform_fit_tooltip = Hovertip(
    transform_fit_radio, "Returns a resized and cropped version of the image,\ncropped to the requested aspect ratio and size.")

transform_pad_radio = ttk.Radiobutton(
    transform_resize_type_frame, text="Pad", variable=transform_resize_type, value=3, state="disabled")
transform_pad_radio.grid(padx=(25, 5), sticky=W, row=0, column=3)
transform_pad_tooltip = Hovertip(
    transform_pad_radio, "Returns a resized and padded version of the image,\nexpanded to fill the requested aspect ratio and size.")

transform_transpose_checkbutton = ttk.Checkbutton(
    transform_img_frame, text="Transpose", variable=transform_transpose, command=ui_toggle_transpose)
transform_transpose_checkbutton.grid(padx=5, sticky=W, row=2, column=0)

transform_transpose_tooltip = Hovertip(
    transform_transpose_checkbutton, "Transpose image (flip or rotate in 90 degree steps).")

transform_transpose_combobox = ttk.Combobox(
    transform_img_frame, state="disabled", width=43, textvariable=transform_transpose_mode, values=TRANSPOSE)
transform_transpose_combobox.current(0)
transform_transpose_combobox.grid(
    padx=5, sticky=E, row=2, column=1, columnspan=2)

transform_crop_checkbutton = ttk.Checkbutton(
    transform_img_frame, text="Crop", variable=transform_crop, command=ui_toggle_crop)
transform_crop_checkbutton.grid(padx=5, sticky=W, row=3, column=0)

transform_crop_tooltip = Hovertip(
    transform_crop_checkbutton, "Possible Formats (interchangable):\n- Percentages (LEFT%, UPPER%, RIGHT%, LOWER%)\n- Dimensions (LEFT, UPPER, RIGHT, LOWER)\n- Both (e.g. 25%, 100, 250, 35%)")

transform_crop_entry = ttk.Entry(
    transform_img_frame, width=46)
transform_crop_entry.grid(padx=5, sticky=E, row=3, column=1, columnspan=2)
transform_crop_entry.insert(END, "0%,0%,0%,0%")
transform_crop_entry.config(state="disabled")

transform_scale_checkbutton = ttk.Checkbutton(
    transform_img_frame, text="Scale", variable=transform_scale, command=ui_toggle_scale)
transform_scale_checkbutton.grid(padx=5, sticky=W, row=4, column=0)
transform_scale_tooltip = Hovertip(
    transform_scale_checkbutton, "Possible Factors:\n- 0-1: Contracts image.\n- >1: Expands image.")

transform_scale_entry = ttk.Entry(
    transform_img_frame, width=25)
transform_scale_entry.grid(padx=5, sticky=E, row=4, column=1)
transform_scale_entry.insert(END, "1.0")
transform_scale_entry.config(state="disabled")

transform_scale_combobox = ttk.Combobox(
    transform_img_frame, state="disabled", width=15, textvariable=transform_scale_resample, values=RESAMPLING)
transform_scale_combobox.current(3)
transform_scale_combobox.grid(padx=5, sticky=E, row=4, column=2)

transform_expand_checkbutton = ttk.Checkbutton(
    transform_img_frame, text="Expand", variable=transform_expand, command=ui_toggle_expand)
transform_expand_checkbutton.grid(padx=5, sticky=W, row=5, column=0)
transform_expand_tooltip = Hovertip(
    transform_expand_checkbutton, "Expands image on all sides.\nTakes border width in pixels as parameter.")

transform_expand_entry = ttk.Entry(
    transform_img_frame, width=25)
transform_expand_entry.insert(END, "0")
transform_expand_entry.config(state="disabled")
transform_expand_entry.grid(padx=5, sticky=E, row=5, column=1)
transform_expand_button = ttk.Button(
    transform_img_frame, text="Fill Color", state="disabled", image=pixel, compound="c", width=17, command=set_fill_color)
transform_expand_button.grid(padx=5, sticky=E, row=5, column=2)

# operations
transform_operations_frame = LabelFrame(
    transform_frame, text="Operations", padx=5, pady=5)
transform_operations_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)

transform_flip = IntVar(value=0)
transform_mirror = IntVar(value=0)
transform_equalize = IntVar(value=0)  # mask=None!
transform_grayscale = IntVar(value=0)
transform_invert = IntVar(value=0)
transform_posterize = IntVar(value=0)
transform_solarize = IntVar(value=0)

transform_flip_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Flip (V)", variable=transform_flip)
transform_flip_checkbutton.grid(padx=(5, 2), sticky=W, row=0, column=0)
transform_flip_tooltip = Hovertip(
    transform_flip_checkbutton, "Flip the image vertically (top to bottom).")
transform_mirror_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Mirror (H)", variable=transform_mirror)
transform_mirror_checkbutton.grid(padx=2, sticky=W, row=0, column=1)
transform_mirror_tooltip = Hovertip(
    transform_mirror_checkbutton, "Flip image horizontally (left to right).")
transform_equalize_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Equalize", variable=transform_equalize)
transform_equalize_checkbutton.grid(padx=2, sticky=W, row=0, column=2)
transform_equalize_tooltip = Hovertip(
    transform_equalize_checkbutton, "Equalize the image histogram.\nThis effect applies a non-linear mapping to the input\nimage, in order to create a uniform distribution of\ngrayscale values in the output image.")
transform_grayscale_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Grayscale", variable=transform_grayscale)
transform_grayscale_checkbutton.grid(padx=2, sticky=W, row=0, column=3)
transform_grayscale_tooltip = Hovertip(
    transform_grayscale_checkbutton, "Convert the image to grayscale.")
transform_invert_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Invert", variable=transform_invert)
transform_invert_checkbutton.grid(padx=2, sticky=W, row=0, column=4)
transform_invert_tooltip = Hovertip(
    transform_invert_checkbutton, "Invert (negate) the image.")
transform_posterize_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Posterize", variable=transform_posterize, command=ui_toggle_posterize)
transform_posterize_checkbutton.grid(padx=(5, 2), sticky=W, row=1, column=0)
transform_posterize_entry = ttk.Entry(
    transform_operations_frame, width=5)
transform_posterize_entry.insert(END, "8")
transform_posterize_entry.config(state="disabled")
transform_posterize_entry.grid(padx=2, sticky=W, row=1, column=1)
transform_posterize_tooltip = Hovertip(
    transform_posterize_checkbutton, "Reduce the number of bits for each color channel.\nTakes number of bits to keep for each channel (1-8) as parameter.")
transform_solarize_checkbutton = ttk.Checkbutton(
    transform_operations_frame, text="Solarize", variable=transform_solarize, command=ui_toggle_solarize)
transform_solarize_checkbutton.grid(padx=2, sticky=W, row=1, column=3)
transform_solarize_entry = ttk.Entry(
    transform_operations_frame, width=5)
transform_solarize_entry.insert(END, "256")
transform_solarize_entry.config(state="disabled")
transform_solarize_entry.grid(padx=2, sticky=W, row=1, column=4)
transform_solarize_tooltip = Hovertip(
    transform_solarize_checkbutton, "All pixels above inputted grayscale level are inverted.")

# filters
transform_filters_frame = LabelFrame(
    transform_frame, text="Filters", padx=5, pady=5)
transform_filters_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)

transform_blur = IntVar(value=0)
transform_contour = IntVar(value=0)
transform_detail = IntVar(value=0)
transform_edge_enhance = IntVar(value=0)
transform_edge_enhance_more = IntVar(value=0)
transform_emboss = IntVar(value=0)
transform_find_edges = IntVar(value=0)
transform_sharpen = IntVar(value=0)
transform_smooth = IntVar(value=0)
transform_smooth_more = IntVar(value=0)

transform_blur_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Blur", variable=transform_blur)
transform_blur_checkbutton.grid(padx=(5, 2), sticky=W, row=0, column=0)
transform_contour_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Contour", variable=transform_contour)
transform_contour_checkbutton.grid(padx=2, sticky=W, row=0, column=1)
transform_detail_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Detail", variable=transform_detail)
transform_detail_checkbutton.grid(padx=2, sticky=W, row=0, column=2)
transform_edge_enhance_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Edgehance", variable=transform_edge_enhance)
transform_edge_enhance_checkbutton.grid(padx=2, sticky=W, row=0, column=3)
transform_edge_enhance_more_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="EH++", variable=transform_edge_enhance_more)
transform_edge_enhance_more_checkbutton.grid(padx=2, sticky=W, row=0, column=4)
transform_edge_enhance_more_tooltip = Hovertip(
    transform_edge_enhance_more_checkbutton, "Edge Enhance More.")

transform_emboss_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Emboss", variable=transform_emboss)
transform_emboss_checkbutton.grid(padx=(5, 2), sticky=W, row=1, column=0)
transform_find_edges_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Edgefind", variable=transform_find_edges)
transform_find_edges_checkbutton.grid(padx=2, sticky=W, row=1, column=1)
transform_sharpen_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Sharpen", variable=transform_sharpen)
transform_sharpen_checkbutton.grid(padx=2, sticky=W, row=1, column=2)
transform_smooth_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="Smooth", variable=transform_smooth)
transform_smooth_checkbutton.grid(padx=2, sticky=W, row=1, column=3)
transform_smooth_more_checkbutton = ttk.Checkbutton(
    transform_filters_frame, text="S++", variable=transform_smooth_more)
transform_smooth_more_checkbutton.grid(padx=2, sticky=W, row=1, column=4)
transform_smooth_more_tooltip = Hovertip(
    transform_smooth_more_checkbutton, "Smooth More.")

# enhancements
transform_enhancements_frame = LabelFrame(
    transform_frame, text="Enhancements", padx=5, pady=5)
transform_enhancements_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)
transform_enhancements_frame.grid_columnconfigure(1, weight=1)

transform_color = IntVar(value=0)
transform_contrast = IntVar(value=0)
transform_brightness = IntVar(value=0)
transform_sharpness = IntVar(value=0)

transform_color_checkbutton = ttk.Checkbutton(
    transform_enhancements_frame, text="Color", variable=transform_color, command=ui_toggle_color)
transform_color_checkbutton.grid(padx=5, sticky=W, row=0, column=0)
transform_color_entry = ttk.Entry(
    transform_enhancements_frame, width=5)
transform_color_entry.insert(END, "1.0")
transform_color_entry.config(state="disabled")
transform_color_entry.grid(padx=5, sticky=W, row=0, column=1)
transform_contrast_checkbutton = ttk.Checkbutton(
    transform_enhancements_frame, text="Contrast", variable=transform_contrast, command=ui_toggle_contrast)
transform_contrast_checkbutton.grid(padx=5, sticky=W, row=0, column=2)
transform_contrast_entry = ttk.Entry(
    transform_enhancements_frame, width=5)
transform_contrast_entry.insert(END, "1.0")
transform_contrast_entry.config(state="disabled")
transform_contrast_entry.grid(padx=5, sticky=W, row=0, column=3)
transform_brightness_checkbutton = ttk.Checkbutton(
    transform_enhancements_frame, text="Brightness", variable=transform_brightness, command=ui_toggle_brightness)
transform_brightness_checkbutton.grid(padx=5, sticky=W, row=1, column=0)
transform_brightness_entry = ttk.Entry(
    transform_enhancements_frame, width=5)
transform_brightness_entry.insert(END, "1.0")
transform_brightness_entry.config(state="disabled")
transform_brightness_entry.grid(padx=5, sticky=W, row=1, column=1)
transform_sharpness_checkbutton = ttk.Checkbutton(
    transform_enhancements_frame, text="Sharpness", variable=transform_sharpness, command=ui_toggle_sharpness)
transform_sharpness_checkbutton.grid(padx=5, sticky=W, row=1, column=2)
transform_sharpness_entry = ttk.Entry(
    transform_enhancements_frame, width=5)
transform_sharpness_entry.insert(END, "1.0")
transform_sharpness_entry.config(state="disabled")
transform_sharpness_entry.grid(padx=5, sticky=W, row=1, column=3)

transform_color_tooltip = Hovertip(
    transform_color_checkbutton, "Adjust image color balance.\n- 0.0: Black and white.\n- 1.0: Original image.")
transform_contrast_tooltip = Hovertip(
    transform_contrast_checkbutton, "Adjust image contrast.\n- 0.0: Solid gray image.\n- 1.0: Original image.")
transform_brightness_tooltip = Hovertip(
    transform_brightness_checkbutton, "Adjust image brightness.\n- 0.0: Black image.\n- 1.0: Original image.")
transform_sharpness_tooltip = Hovertip(
    transform_sharpness_checkbutton, "Adjust image sharpness.\n- 0.0: Blurred image.\n- 1.0: Original image.\n- 2.0: Sharpened image.")

"""
ADVANCED TAB:
- convert to filetype
- convert modes (L, RGB, CMYK...)
- error recognition (false extensions)
- extension specific options
- image statistics
"""

# conversion
advanced_conversion_frame = LabelFrame(
    advanced_frame, text="Conversion", padx=5, pady=5)
advanced_conversion_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)
advanced_conversion_frame.grid_columnconfigure(0, weight=1)

advanced_convert_filetype = IntVar(value=0)
advanced_convert_modes = IntVar(value=0)
advanced_broken_extensions = IntVar(value=0)

advanced_convert_filetype_option = StringVar()
advanced_convert_modes_option = StringVar()

advanced_convert_filetype_checkbutton = ttk.Checkbutton(
    advanced_conversion_frame, text="Convert Filetype", variable=advanced_convert_filetype, command=ui_toggle_filetype)
advanced_convert_filetype_checkbutton.grid(padx=5, sticky=W, row=0, column=0)
advanced_convert_modes_checkbutton = ttk.Checkbutton(
    advanced_conversion_frame, text="Convert Mode", variable=advanced_convert_modes, command=ui_toggle_mode)
advanced_convert_modes_checkbutton.grid(padx=5, sticky=W, row=1, column=0)
advanced_broken_extensions_checkbutton = ttk.Checkbutton(
    advanced_conversion_frame, text="Detect and Fix Broken Extensions", variable=advanced_broken_extensions, state=DISABLED)
advanced_broken_extensions_checkbutton.grid(
    padx=5, sticky=W, row=2, column=0, columnspan=2)

advanced_convert_filetype_combobox = ttk.Combobox(
    advanced_conversion_frame, state="disabled", width=35, textvariable=advanced_convert_filetype_option, values=SAVE_FORMATS)
advanced_convert_filetype_combobox.current(0)
advanced_convert_filetype_combobox.grid(padx=5, sticky=W, row=0, column=1)
advanced_convert_modes_combobox = ttk.Combobox(
    advanced_conversion_frame, state="disabled", width=35, textvariable=advanced_convert_modes_option, values=MODES)
advanced_convert_modes_combobox.current(0)
advanced_convert_modes_combobox.grid(padx=5, sticky=W, row=1, column=1)

# extension-specific options
advanced_extensions_frame = LabelFrame(
    advanced_frame, text="Extension-specific Options", padx=5, pady=5)
advanced_extensions_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)
advanced_extensions_frame.grid_columnconfigure(0, weight=1)

advanced_blp1 = IntVar()
advanced_all_frames = IntVar()
advanced_interlace_gif = IntVar()
advanced_optimize = IntVar()
advanced_progressive_jpeg = IntVar()
advanced_lossless_webp = IntVar()

advanced_blp1_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="BLP: Use BLP1 instead of BLP2", variable=advanced_blp1)
advanced_blp1_checkbutton.grid(padx=5, sticky=W, row=0, column=0, columnspan=2)
advanced_all_frames_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="APNG, GIF, MPO, PDF, TIFF, WebP: Save all animation frames", variable=advanced_all_frames)
advanced_all_frames_checkbutton.grid(
    padx=5, sticky=W, row=1, column=0, columnspan=2)
advanced_interlace_gif_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="GIF: Interlace image", variable=advanced_interlace_gif)
advanced_interlace_gif_checkbutton.grid(
    padx=5, sticky=W, row=2, column=0, columnspan=2)
advanced_optimize_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="JPEG, JFIF, PNG: Optimize", variable=advanced_optimize)
advanced_optimize_checkbutton.grid(
    padx=5, sticky=W, row=3, column=0, columnspan=2)
advanced_progressive_jpeg_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="JPEG, JFIF: Save as progressive JPEG", variable=advanced_progressive_jpeg)
advanced_progressive_jpeg_checkbutton.grid(
    padx=5, sticky=W, row=4, column=0, columnspan=2)
advanced_lossless_webp_checkbutton = ttk.Checkbutton(
    advanced_extensions_frame, text="WebP: Save lossless WebP (disregard quality)", variable=advanced_lossless_webp)
advanced_lossless_webp_checkbutton.grid(
    padx=5, sticky=W, row=5, column=0, columnspan=2)

advanced_jpg_quality = IntVar(value=75)
advanced_webp_quality = IntVar(value=80)

advanced_jpg_quality_label = ttk.Label(
    advanced_extensions_frame, text="JPG Quality (75):")
advanced_jpg_quality_label.grid(padx=5, sticky=W, row=6, column=0)
advanced_jpg_quality_scale = ttk.Scale(
    advanced_extensions_frame, length=200, from_=0, to_=95, variable=advanced_jpg_quality,
    command=lambda val: advanced_jpg_quality_label.config(text=f"JPG Quality ({int(float(val))}):"))
advanced_jpg_quality_scale.grid(padx=5, sticky=W, row=6, column=1)
advanced_webp_quality_label = ttk.Label(
    advanced_extensions_frame, text="WebP Quality (80):")
advanced_webp_quality_label.grid(padx=5, sticky=W, row=7, column=0)
advanced_webp_quality_scale = ttk.Scale(
    advanced_extensions_frame, length=200, from_=0, to_=100, variable=advanced_webp_quality,
    command=lambda val: advanced_webp_quality_label.config(text=f"WebP Quality ({int(float(val))}):"))
advanced_webp_quality_scale.grid(padx=5, sticky=W, row=7, column=1)

advanced_jpg_quality_tooltip = Hovertip(
    advanced_jpg_quality_label, "Default: 75.")
advanced_webp_quality_tooltip = Hovertip(
    advanced_webp_quality_label, "Default: 80.")

# statistics
advanced_stats_frame = LabelFrame(
    advanced_frame, text="Statistics", padx=5, pady=5)
advanced_stats_frame.pack(padx=5, pady=5, fill=X, expand=1, anchor=N)

advanced_stats = IntVar()
advanced_extrema = IntVar()
advanced_count = IntVar()
advanced_sum = IntVar()
advanced_sum2 = IntVar()
advanced_mean = IntVar()
advanced_median = IntVar()
advanced_rms = IntVar()
advanced_var = IntVar()
advanced_stddev = IntVar()

advanced_stats_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Save Stats", variable=advanced_stats, command=ui_toggle_stats)
advanced_stats_checkbutton.grid(padx=5, sticky=W, row=0, column=0)
advanced_extrema_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Extrema", variable=advanced_extrema, state="disabled")
advanced_extrema_tooltip = Hovertip(
    advanced_extrema_checkbutton, "Min/max values for each band in the image.")
advanced_extrema_checkbutton.grid(padx=5, sticky=W, row=0, column=1)
advanced_count_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Count", variable=advanced_count, state="disabled")
advanced_count_tooltip = Hovertip(
    advanced_count_checkbutton, "Total number of pixels for each band in the image.")
advanced_count_checkbutton.grid(padx=5, sticky=W, row=0, column=2)
advanced_sum_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Sum", variable=advanced_sum, state="disabled")
advanced_sum_tooltip = Hovertip(
    advanced_sum_checkbutton, "Sum of all pixels for each band in the image.")
advanced_sum_checkbutton.grid(padx=5, sticky=W, row=0, column=3)
advanced_sum2_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Sum²", variable=advanced_sum2, state="disabled")
advanced_sum2_tooltip = Hovertip(
    advanced_sum2_checkbutton, "Squared sum of all pixels for each band in the image.")
advanced_sum2_checkbutton.grid(padx=5, sticky=W, row=0, column=4)

advanced_mean_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Mean", variable=advanced_mean, state="disabled")
advanced_mean_tooltip = Hovertip(
    advanced_mean_checkbutton, "Average (arithmetic mean) pixel level for each band in the image.")
advanced_mean_checkbutton.grid(padx=5, sticky=W, row=1, column=0)
advanced_median_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Median", variable=advanced_median, state="disabled")
advanced_median_tooltip = Hovertip(
    advanced_median_checkbutton, "Median pixel level for each band in the image.")
advanced_median_checkbutton.grid(padx=5, sticky=W, row=1, column=1)
advanced_rms_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="RMS", variable=advanced_rms, state="disabled")
advanced_rms_tooltip = Hovertip(
    advanced_rms_checkbutton, "RMS (root-mean-square) for each band in the image.")
advanced_rms_checkbutton.grid(padx=5, sticky=W, row=1, column=2)
advanced_var_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Var.", variable=advanced_var, state="disabled")
advanced_var_tooltip = Hovertip(
    advanced_var_checkbutton, "Variance for each band in the image.")
advanced_var_checkbutton.grid(padx=5, sticky=W, row=1, column=3)
advanced_stddev_checkbutton = ttk.Checkbutton(
    advanced_stats_frame, text="Dev.", variable=advanced_stddev, state="disabled")
advanced_stddev__tooltip = Hovertip(
    advanced_stddev_checkbutton, "Standard deviation for each band in the image.")
advanced_stddev_checkbutton.grid(padx=5, sticky=W, row=1, column=4)

"""
Done.
"""
root.protocol("WM_DELETE_WINDOW", check_on_close)
root.mainloop()
