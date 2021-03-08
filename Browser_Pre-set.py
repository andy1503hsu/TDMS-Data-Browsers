from nptdms import TdmsFile
from PyQt5.QtWidgets import QWidget, QGridLayout, QMainWindow, QApplication, QComboBox, QPushButton, QColorDialog, QLabel, QScrollArea, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import numpy as np
import pyqtgraph as pg
import sys
from functools import partial


class TDMS_File():
    def __init__(self, file_open):
        self.tdms_file = TdmsFile.read(file_open)
        self.start_time_info = (None,15,"")
        self.time_range = 0
        self.timesDict = self.setTimes()
        self.nondigital = list()
        self.digital = list()
        self.digital = self.findDigital()
        self.editDigital()
        self.file_name = file_open
        # self.debug()
    
    def setTimes(self):
        timesDict = {}
        self.start_time_info = self.find_earliest_time()
        if self.start_time_info[0] is True:
            self.time_range = self.start_time_info[3] - self.start_time_info[1] 
            start_time = self.start_time_info[1]
            # time is formatted as a float
            for group in self.tdms_file.groups():
                time = group["time"][:]
                for i, times in enumerate(time):
                    time[i] = float(times) - start_time
                timesDict[group.name] = time
        else: # string
            start = self.start_time_info[1]
            start_time = int(start[6:8]) + int(start[10:12])/100 # seconds, milliseconds
            end = self.start_time_info[3]
            end_time = int(end[6:8]) + int(end[10:12])/100
            # print(start_time, end_time)
            self.time_range = end_time - start_time
            for group in self.tdms_file.groups():
                time = group["time"][:]
                for i, times in enumerate(time):
                    seconds = times[6:8]
                    milliseconds = times[10:12]
                    new_time = int(seconds) + int(milliseconds)/100
                    time[i] = new_time - start_time
                timesDict[group.name] = time
        return timesDict

    def find_earliest_time(self): # it's really finding both earliest and latest times
        earliest_time = self.tdms_file.groups()[0]["time"][0]
        earliest_group = self.tdms_file.groups()[0].name
        for group in self.tdms_file.groups():
            first_time = group["time"][0]
            if first_time < earliest_time:
                earliest_time = first_time
                earliest_group = group.name
        latest_time_list = [group["time"][-1] for group in self.tdms_file.groups()]
        latest_time = max(latest_time_list)
        # print(latest_time)
        # print(earliest_time)
        try:
            earliest_time = float(earliest_time)
            return (True, earliest_time, earliest_group, float(latest_time))
        except:
            return (False, earliest_time, earliest_group, latest_time)
    
    def findDigital(self):
        digital = []
        breakOut = False
        for group in self.tdms_file.groups():
            for channel in group.channels():
                if channel.name == "time": continue
                for data in channel[:int(len(channel) * .2)]: # looks at the first 20% to see if anything is digital
                    data = float(data)
                    if abs(data) >= 1.0e-6 and abs(data - 1) >= 1.0e-6:
                        breakOut = True
                        break
            if breakOut:
                breakOut = False
                self.nondigital.append(group.name)
            else:
                digital.append(group.name)
        return digital
    
    def editDigital(self): 
        
        for digital_group in self.digital: # make the digital plots more asymptomic
            time_info = self.timesDict[digital_group]
            #print(digital_group, [format(time, ".4f") for time in time_info])
            for channel in self.tdms_file[digital_group].channels():
                for i in range(1, len(channel[1:])):
                    if abs(float(channel[i]) - float(channel[i - 1])) > 1.0e-6: # valve opened or closed
                        time_info[i - 1] = time_info[i] - 0.001
            #print(digital_group, [format(time, ".4f") for time in time_info])
        
        '''digital_channel_count = 0
        for digital_group in self.digital:
            digital_channel_count += len(self.tdms_file[digital_group].channels())
        digital_channel_count -= len(self.digital) # subtracts one per group (to ignore time channel, which really isn't a channel)
        print("Number of Digital Channels:", digital_channel_count)'''

        self.digital_adjustment = {}
        adjustment = 0
        for digital_group in self.digital:
            for digital_channel in self.tdms_file[digital_group].channels():
                if digital_channel.name == "time": continue
                self.digital_adjustment[digital_channel.name] = adjustment
                adjustment += 0.01
        #print(self.digital_adjustment)
    
    def debug(self):
        print("---------Verify with Excel Spreadsheet---------")
        print("Group Names:", [group.name for group in self.tdms_file.groups()])
        print("Digital Groups: (Only 0 and 1 for output)", self.digital)
        print()
        print("** Start time Info **")
        print("Start time:", self.start_time_info[1])
        print("Time was from", self.start_time_info[2], "group")

class Multiple_Plots_File():
    def __init__(self, fileName):
        self.fileUsed = fileName
        file = open(fileName)
        self.numPlots = int(file.readline())
        self.plotsInfo = dict() # dictionary stores data for every plot, including plot name and info in plots
        self.plotsInfoErrors = dict() # stores the group/channel combos that couldn't be found

        for _ in range(self.numPlots):
            plotName = file.readline().strip()
            singlePlotInfo = list() # stores data for one plot only (will be added to dictionary)
            while True:
                nextLineInFile = file.readline().strip()
                if nextLineInFile == "": break # reached end of "graph"
                singlePlotInfo.append(nextLineInFile.split())
            self.plotsInfo[plotName] = singlePlotInfo
        
        self.resolveColorsAndSymbols()
        file.close()
    
    def resolveColorsAndSymbols(self):
        for plotData in self.plotsInfo.values():
            for lineData in plotData:
                colorData = lineData[2]
                if colorData[0] == '(': # color is in r g b format
                    data = colorData.strip("()") # gets rid of the parenthesses
                    colorData = eval(data) # converts it to a tuple
                lineData[2] = colorData

                symbolData = lineData[3]
                if symbolData == "np": lineData[3] = None
    
    def validate_groups_and_channels(self, tdmsFile):
        for plotName, listOfLines in self.plotsInfo.items():
            counter = 0
            while counter < len(listOfLines):
                line = listOfLines[counter]
                group = line[0]
                channel = line[1]
                errorList = self.plotsInfoErrors.get(plotName, [])
                try:
                    tdmsFile.tdms_file[group][channel][0]
                except:
                    errorList.append((group, channel))
                    # listOfLines.remove(line) # CAN'T DO THIS (in current form) SINCE INFINITE LOOP
                counter += 1
                self.plotsInfoErrors[plotName] = errorList
    
    def button_name(self, plotName):
        button_string = plotName + "\n("
        count = 0
        for lineData in self.plotsInfo[plotName]:
            if (lineData[0], lineData[1]) in self.plotsInfoErrors[plotName]:
                continue
            count += 1
            button_string += lineData[1] + ", "
            if count % 5 == 0 and count != len(self.plotsInfo[plotName]):
                button_string += "\n"
        button_string = button_string[:-2] + ")" # slice off the ", " and add the close parenthesses
        return button_string
    
    def debug(self):
        print()
        print("File Used:", self.fileUsed)
        print("Number of Plots:", self.numPlots)
        print("Plot(s) Info:")
        print()
        for plotName in self.plotsInfo.keys():
            print("Plot Name:", plotName)
            for line in self.plotsInfo[plotName]:
                print(line)
            print()
        
        print("Error Info:")
        print(self.plotsInfoErrors)
        '''for plotName in self.plotsInfo.keys():
            print("Plot Name:", plotName)
            for line in self.plotsInfoErrors[plotName]:
                print(line)
            print()'''

class MainWindow(QMainWindow):

    def __init__(self, tdms, plotInfoInstance):
        super().__init__()

        self.legendFontSize = 8
        self.tdms = tdms
        self.plotInfoInstance = plotInfoInstance
        self.plotInfoInstance.validate_groups_and_channels(tdms)
        #print("After validation:")
        #self.plotInfoInstance.debug()

        windowLength = 1750
        windowHeight = 900
        self.setGeometry(100,50,windowLength, windowHeight)
        self.setWindowTitle("TREL TDMS Data Visualization")

        self.graphWidget = pg.PlotWidget()
        self.initGraphWidget()

        numRows = 2 * self.plotInfoInstance.numPlots + 3
        widthOfRight = 290
        customMenuHeight = 200
        saveButtonHeight = 35
        buttonHeight = int((windowHeight - customMenuHeight - saveButtonHeight)/ numRows * 1.5)
        spacerHeight = int((windowHeight - customMenuHeight - saveButtonHeight)/ numRows * 0.5)

        layout = QGridLayout()
        layout.addWidget(self.graphWidget, 0,0, numRows, 1)

        for i in range(numRows - 2): # numRows - 1 because of the scroll area and "save" button
            if i % 2 == 1:
                # .replace('\\n', '\n')
                plotName = list(self.plotInfoInstance.plotsInfo.keys())[int(i/2)]
                button = QPushButton(self.plotInfoInstance.button_name(plotName))
                button.setFixedSize(widthOfRight,buttonHeight)
                layout.addWidget(button, i, 1)
                button.clicked.connect(partial(self.button_clicked, plotName))
            else: # i is even
                spacer = QLabel()
                spacer.setFixedSize(widthOfRight, spacerHeight)
                layout.addWidget(spacer, i, 1)

        scroll2 = QScrollArea()
        scroll2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll2.setWidgetResizable(True)
        scroll2.setFixedSize(widthOfRight,customMenuHeight)

        self.interLayout = QGridLayout()
        self.interLayout.setAlignment(Qt.AlignTop)
        self.interaction = QWidget()
        self.interaction.setLayout(self.interLayout)
        scroll2.setWidget(self.interaction)
        layout.addWidget(scroll2, numRows - 2,1) 

        saveButton = QPushButton("Save Customizations")
        saveButton.setFixedSize(widthOfRight, saveButtonHeight)
        layout.addWidget(saveButton, numRows - 1, 1)
        saveButton.clicked.connect(self.saveButton_clicked)
        
        self.plottedData = dict()
        self.numPlotted = 0
        self.currentPlotName = ""
        self.shapes = { 0 : None, 1 : 'o', 2 : 's', 3 : 't', 4 : 'd', 5: '+' }
        self.saveButtonClicked = False

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def button_clicked(self, plotName):
        while len(self.plottedData) != 0:
            (info, lineInfo) = self.plottedData.popitem() # returns (key, value)
            # the key is:
            # key[0] --> group, key[1] --> channel
            # value[0] --> the thing on the graph itself
            # value[1] --> the label in the interaction
            # value[2] --> the color button
            # value[3] --> the shape combobox
            group = info[0]
            if group in self.tdms.digital:
                self.p2.removeItem(lineInfo[0])
                self.legend.removeItem(lineInfo[0])
            else:
                self.graphWidget.removeItem(lineInfo[0])
            lineInfo[1].deleteLater()
            lineInfo[2].deleteLater()
            lineInfo[3].deleteLater()
        
        self.numPlotted = 0
        self.currentPlotName = plotName
            
        if len(self.plotInfoInstance.plotsInfoErrors[plotName]) > 0:
            self.showErrorBox(plotName)

        plotInfo = self.plotInfoInstance.plotsInfo[plotName] # list of groups, channels, color, point/no-point
        
        for lineInfo in plotInfo: # lineInfo is one single line
            if (lineInfo[0], lineInfo[1]) in self.plotInfoInstance.plotsInfoErrors[plotName]: continue
            self.numPlotted += 1
            self.add_to_plot(lineInfo)

    # shows an error box to display the group/channel combos that couldn't be plotted
    def showErrorBox(self, plotName):
        box_title = "Couldn't plot some data"
        unplottable = '\n'.join(map(lambda x: x[0] + " " + x[1], self.plotInfoInstance.plotsInfoErrors[plotName]))
        box_text = "The following group—channel combination(s) could not be found in the tdms file: \n" + unplottable
        QMessageBox.information(self, box_title, box_text, QMessageBox.Ok)

    def saveButton_clicked(self):
        if self.currentPlotName == "": return
        self.saveButtonClicked = True # knows to create a file later on

        for lineInfo in self.plotInfoInstance.plotsInfo[self.currentPlotName]:
            group = lineInfo[0]
            channel = lineInfo[1]
            lineOnGraph = self.plottedData[(group, channel)][0] # plotDataItem
            # print(lineOnGraph.opts)
            rgba_tuple = lineOnGraph.opts["pen"].color().getRgb() # the amount of pain i went through to get this SINGLE line
            color = eval(str(rgba_tuple[:3])) # get rgb but no alpha
            shape_comboBox = self.plottedData[(group, channel)][3]
            shape = self.shapes[shape_comboBox.currentIndex()]
            lineInfo[2] = color
            lineInfo[3] = shape
            #print(lineInfo)
        #print(self.plotInfoInstance.plotsInfo[self.currentPlotName])

        confirm_title = "Save has been confirmed"
        confirm_text = "The customizations for " + self.currentPlotName + " have been saved."
        QMessageBox.information(self, confirm_title, confirm_text, QMessageBox.Ok)

    # will be called when "X" is clicked
    def closeEvent(self, event):
        if not self.saveButtonClicked: 
            event.accept()
            return
        box_text = 'Do you want to keep a copy of the saved customizations for future use? If yes, the customizations will be saved under "customizations.output"'
        reply = QMessageBox.question(self, 'Print Customizations?', box_text,
			    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes: self.create_file()
        event.accept()
    
    # Creates customizations.output
    def create_file(self):
        file = open("customizations.output", "w") # w is write to a file (while overriding what is already there)
        file.write(str(self.plotInfoInstance.numPlots) + "\n")
        for plotName, plottingInfo in self.plotInfoInstance.plotsInfo.items():
            file.write(plotName + "\n")
            for lineInfo in plottingInfo:
                lineInfo[2] = "".join(str(lineInfo[2]).split())
                if lineInfo[3] is None: lineInfo[3] = "np"
                lineInfoStr = " ".join(lineInfo)
                file.write(lineInfoStr + "\n")
            file.write("\n")

        file.close()

    def initGraphWidget(self):
        self.graphWidget.setTitle("Data Visualization of " + self.tdms.file_name, color="d", size="25px")
        pg.setConfigOption('foreground', 'w')
        self.legend = self.graphWidget.addLegend(offset = (200,100), labelTextSize = str(self.legendFontSize) + "pt")
        self.graphWidget.showGrid(x=True, y=True)
        styles = {"color": "#4c55ff", "font-size": "20px"}
        self.graphWidget.setLabel("bottom", "Time", **styles)
        styles = {"color": "#66f0ff", "font-size": "20px"}
        leftLabel = "Non-Digital Channels ("
        for group in self.tdms.nondigital:
            leftLabel += group + ", "
        leftLabel = leftLabel[:-2] + ")"
        self.graphWidget.setLabel("left", leftLabel, **styles)
        self.graphWidget.plotItem.vb.setRange(xRange = (0, self.tdms.time_range))
        self.graphWidget.enableAutoRange(axis='y')
        self.graphWidget.setAutoVisible(y=True)

        self.p2 = pg.ViewBox()
        self.p2.setRange(yRange = (0 - len(self.tdms.digital_adjustment)*0.01*1.2, 1 + len(self.tdms.digital_adjustment)*0.01*1.2))
        self.graphWidget.showAxis('right')
        self.graphWidget.scene().addItem(self.p2)
        self.graphWidget.getAxis('right').linkToView(self.p2)
        self.graphWidget.getAxis('right').setTicks([[(1,"1"),(0,"0")]])
        self.p2.setXLink(self.graphWidget)
        rightLabel = "Digital Channels ("
        for group in self.tdms.digital:
            rightLabel += group + ", "
        rightLabel = rightLabel[:-2] + ")"
        self.graphWidget.getAxis('right').setLabel(rightLabel, **styles)

        self.vLine = pg.InfiniteLine(pos = self.tdms.time_range, movable=False, labelOpts = {'rotateAxis':(-1,0)},
                                    label = "Last Data Record \nat " + str(format(self.tdms.time_range, ",.2f")) + " seconds")
        font = QFont()
        font.setPixelSize(14)
        self.vLine.label.setFont(font)
        self.vLine.label.setPosition(0.84)
        self.graphWidget.addItem(self.vLine)

        self.graphWidget.plotItem.vb.sigXRangeChanged.connect(self.setYRange)

    def setYRange(self):
        self.graphWidget.enableAutoRange(axis='y')
        self.graphWidget.setAutoVisible(y=True)

    def add_to_plot(self, lineInfo):
        group = lineInfo[0]
        channel = lineInfo[1]
        color = lineInfo[2]
        shape = lineInfo[3]
        time = self.tdms.timesDict[group]
        channel_info = self.tdms.tdms_file[group][channel][:]
        np_channel_info = self.convert_to_np(channel_info)
        # print(groupText)
        if group in self.tdms.digital:
            np_channel_info = self.adjust_digital(channel, np_channel_info)
            plotDataItem = pg.PlotDataItem(x = self.convert_to_np(time), y = np_channel_info, symbolBrush = pg.mkBrush(color),
                                             symbol = shape, pen = pg.mkPen(color), name = group + ": " + channel)
            self.p2.addItem(plotDataItem)
            self.legend.addItem(plotDataItem, group + ": " + channel)
            # self.p2.setRange(xRange = (time[0], time[-1]))
        else:
            plotDataItem = self.graphWidget.plot(x = self.convert_to_np(time), y = np_channel_info, symbolBrush = pg.mkBrush(color),
                                             symbol = shape, pen = pg.mkPen(color), name = group + ": " + channel)
        self.p2.setGeometry(self.graphWidget.plotItem.vb.sceneBoundingRect())
        # self.graphWidget.enableAutoRange(pg.ViewBox.XYAxes)
        self.setInteraction(group, channel, plotDataItem, shape)

    def convert_to_np(self, data):
        return np.array(data, dtype = float)

    def adjust_digital(self, channel, np_channel_info):
        for i in range(len(np_channel_info)):
            if abs(float(np_channel_info[i]) - 1) < 1.0e-6: # 1 
                np_channel_info[i] += self.tdms.digital_adjustment[channel]
            else: # 0
                np_channel_info[i] -= self.tdms.digital_adjustment[channel]
        return np_channel_info

    def setInteraction(self, group, channel, plotDataItem, shape):
        label = QLabel(group + ":  " + channel) # group - channel
        self.interLayout.addWidget(label, self.numPlotted, 0)

        button = QPushButton('Choose Color', self)
        button.clicked.connect(partial(self.set_color, group, channel))
        self.interLayout.addWidget(button, self.numPlotted, 1)

        comboBox = QComboBox()
        [comboBox.addItems(['No Points', 'Circles', 'Squares', 'Triangles', 'Diamonds', 'Pluses'])]
        if shape is None:
            comboBox.setCurrentIndex(0)
        else:
            comboBox.setCurrentIndex(list(self.shapes.keys())[list(self.shapes.values()).index(shape)])
        comboBox.currentIndexChanged.connect(partial(self.set_shape, group, channel))
        self.interLayout.addWidget(comboBox, self.numPlotted, 2)

        self.plottedData[(group, channel)] = (plotDataItem, label, button, comboBox)

    def set_color(self, group, channel):
        color = QColorDialog.getColor()
        self.plottedData[(group,channel)][0].setSymbolBrush(color)
        self.plottedData[(group,channel)][0].setPen(color, width = 1)
    
    def set_shape(self, group, channel):
        shape_index = self.plottedData[(group, channel)][3].currentIndex()
        self.plottedData[(group,channel)][0].setSymbol(self.shapes[shape_index])

def main():
    tdms = ""
    plotsData = ""
    while tdms == "":
        file_to_open_tdms = input("Enter the tdms file name: ")
        try:
            tdms = TDMS_File(file_to_open_tdms)
        except:
            print("Make sure you entered a .tdms file!\n")
    while plotsData == "":
        plotFile = input("Enter the file containing the plot info: ")
        try:
            plotsData = Multiple_Plots_File(plotFile)
            #plotsData.debug()
        except:
            print("Make sure you entered a .txt file!\n")
    run_app(tdms, plotsData)

def run_app(tdms, plotsData):
    app = QApplication(sys.argv)
    main = MainWindow(tdms, plotsData)
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
