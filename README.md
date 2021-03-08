# TDMS-Data-Browsers
Two Python GUI applications that can visualize the data within TDMS files. Created as a project for a student-run research laboratory at UT.

To run the browsers, make sure to download their files and the example TDMS file. The two data browser scripts `Browser_From_Scratch.py` and `Browser_Pre-set.py`, and the example TDMS file is `Test TDMS file.tdms`. Running `Browser_Pre-set.py` also requires downloading `customizations.output`, but more on that in a little bit.

In addition, there are 4 Python packages that are required to run the two Python scripts. These are:
- nptdms
- numpy
- PyQt5
- pyqtgraph

Also make sure that you are running Python 3.7 or higher.

Lastly, at runtime, the Python scripts will ask the user to input a tdms file. When this occurs, make sure
that ".tdms" is included at the end. For example, the TDMS file provided in this repository would be inputted as `Test TDMS file.tdms`. For `Browser_Pre-set.py` specifically, it will also ask to "Enter a file containing the plot info" -- this is `customizations.output`.

The two browsers, as implied by their names, serve different purposes. `Browser_From_Scratch.py` allows the user to add/remove the data very easily and starts off with an empty graph. On the other hand, `Browser_Pre-set.py` uses the information in `customizations.output` to create multiple plots that can be easily toggled back and forth. In other words, `Browser_From_Scratch.py` is typically used when the user wants to skim the data, adding and removing plots rapidly. `Browser_Pre-set.py` is used when the user knows exactly what they want to graph and only want to see that information.

Both data browsers include a customizations area, where the user can switch the color and symbol of the data that has been plotted. In `Browser_Pre-set.py`, these customizations can be saved with the button located on the bottom right corner. After clicking this button, the user can switch to another plot and then switch back without having to re-do those customizations a second time. In addition, upon being closed, the application will ask the user if they wish to push the newly saved information to a text file, so that it can be used in future applications. If the user clicks "Yes," the browser will override the information in `customizations.output` with the customizations the user saved.

Here are some pictures of the two data browsers in action!

These two pictures are from `Browser_From_Scratch.py`...
<img src="https://github.com/andy1503hsu/TDMS-Data-Browsers/blob/main/Example%20Pictures/Browser%20From%20Scratch%20Pic%201.PNG" width = "900">

<img src="https://github.com/andy1503hsu/TDMS-Data-Browsers/blob/main/Example%20Pictures/Browser%20From%20Scratch%20Pic%202.PNG" width = "900">

And these two are from `Browser_Pre-set.py`.
<img src="https://github.com/andy1503hsu/TDMS-Data-Browsers/blob/main/Example%20Pictures/Browser%20Pre-set%20Pic%201.PNG" width = "900">

<img src="https://github.com/andy1503hsu/TDMS-Data-Browsers/blob/main/Example%20Pictures/Browser%20Pre-set%20Pic%202.PNG" width = "900">

For more information about this project and its purpose, check out [this file](https://github.com/andy1503hsu/TDMS-Data-Browser/blob/main/About%20This%20Project.md).
