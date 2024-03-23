# BatchIMG
A batch image processor, written in Python using Pillow and tkinter.

# Usage
- Install Pillow: `pip install pillow`
- Run the application: `python3 main.py`

# Help
To use BatchIMG, you must first select a valid input (source) and a valid output (destination) directory. Your source directory will contain the images to operate on. You may select multiple effects and transformation options, if they are compatible with one another, as represented by a possible error message. To learn the syntax / meaning of each option, hover your mouse over the corresponding label.

Descriptions taken from the Pillow 10.2.0 documentation: https://pillow.readthedocs.io/

**IMPORTANT**:

Effects are applied top to bottom, left to right, sequentially. For example, if you have selected "Resize", "Blur", "Smooth", the image will first be resized, then blurred, then finally smoothed. This may lead to some unwanted side effects, such as selecting a border fill color, then grayscaling the image, which will lead to the fill color also becoming grayscaled. To avoid this, you will need to run the batch processing multiple times (e.g. first grayscaling the images, then expanding them). This also applies to tabs: the operations in the "Transform" tab are applied before the operations in the "Advanced" tab. Some effects are also incompatible with some modes. As a workaround, first convert the images to the fitting modes, then try applying the effects again.

# Notes
Once again, this is another personal project, similar to [YT-DLP-GUI](https://github.com/FlamingLeo/yt-dlp-gui), both in look and feel. I wrote this to help manage images for [my website](https://home.in.tum.de/~scfl/), primarily to resize and optimize larger images, but after seeing how many options and effects the base Pillow package offers, I decided to incorporate several other features into this program.

Future additions might include image deforming, custom filename support, thumbnails, GIF support and image captions.
