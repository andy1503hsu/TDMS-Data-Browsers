from nptdms import TdmsFile
from PyQt5.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QMainWindow, QApplication, QCheckBox, QComboBox, QPushButton, QColorDialog, QLabel, QScrollArea
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
                for data in channel[:]:
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
    
    def editDigital(self): # make the digital plots more asymptomic
        for digital_group in self.digital:
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

class MainWindow(QMainWindow):

    def __init__(self, tdms):
        super(MainWindow, self).__init__()
        self.tdms = tdms

        self.legendFontSize = 8

        self.setGeometry(200,100,1600,900)
        self.setWindowTitle("TREL TDMS Data Visualization: " + tdms.file_name)

        self.graphWidget = pg.PlotWidget()
        self.initGraphWidget()

        layout = QGridLayout()
        layout.addWidget(self.graphWidget, 0,0,8, 1)

        widthOfRight = 300

        label = QLabel("Groups within tdms file: \n (contained in drop-down menu)")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedSize(widthOfRight,45)
        label.setStyleSheet("border: 1px solid black")
        layout.addWidget(label, 0, 1)

        self.comboBox = QComboBox(self)
        layout.addWidget(self.comboBox, 1,1)

        spacer = QLabel()
        spacer.setFixedSize(widthOfRight,10)
        layout.addWidget(spacer, 2, 1)

        label2 = QLabel("Channels within selected group: \n Use checkboxes to plot/unplot \n Legend is in top left corner")
        label2.setAlignment(Qt.AlignCenter)
        label2.setFixedSize(widthOfRight,55)
        label2.setStyleSheet("border: 1px solid black")
        layout.addWidget(label2, 3, 1)

        self.buttonLayout = QVBoxLayout()
        self.buttonLayout.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setMaximumSize(widthOfRight,250)

        self.buttonWidget = QWidget()
        self.buttonWidget.setLayout(self.buttonLayout)
        scroll.setWidget(self.buttonWidget)
        layout.addWidget(scroll, 4, 1)

        spacer2 = QLabel()
        spacer2.setFixedSize(widthOfRight,10)
        layout.addWidget(spacer2, 5, 1)

        label3 = QLabel("**Interactions** \n First Column: Plotted Channels \n Second Column: Customize Color \n Third Column (Drop-Down Menu): Customize Points")
        label3.setAlignment(Qt.AlignCenter)
        label3.setFixedSize(widthOfRight,90)
        label3.setStyleSheet("border: 1px solid black")
        layout.addWidget(label3, 6, 1)

        scroll2 = QScrollArea()
        scroll2.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll2.setWidgetResizable(True)
        scroll2.setMaximumSize(widthOfRight,250)

        self.interLayout = QGridLayout()
        self.interLayout.setAlignment(Qt.AlignTop)
        self.interaction = QWidget()
        self.interaction.setLayout(self.interLayout)
        scroll2.setWidget(self.interaction)
        layout.addWidget(scroll2, 7,1)

        self.initComboBox()
        self.setButtonLayout(self.tdms.tdms_file.groups()[0].name)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.plottedData = {}
        self.show()

    def initComboBox(self):
        for group in self.tdms.tdms_file.groups():
            self.comboBox.addItem(group.name)
        self.comboBox.setMinimumContentsLength(25)
        self.comboBox.currentIndexChanged.connect(self.comboBoxChange)

    def comboBoxChange(self):
        # print("Current selection:", self.comboBox.currentText())
        self.changeButtons(self.comboBox.currentText())

    def changeButtons(self, groupText):
        for i in reversed(range(self.buttonLayout.count())): # deletes all checkBoxes
            self.buttonLayout.itemAt(i).widget().deleteLater()
        self.setButtonLayout(groupText)
    
    def setButtonLayout(self, groupText):
        for channel in self.tdms.tdms_file[groupText].channels():
            if channel.name == "time": continue
            checkBox = QCheckBox(channel.name)
            try:
                self.plottedData[(groupText,channel.name)]
                checkBox.setChecked(True)
            except:
                print(end='') #do nothing
            self.buttonLayout.addWidget(checkBox)
            checkBox.stateChanged.connect(partial(self.clicked, groupText, channel.name))

    def clicked(self, groupText, channel):
        if (groupText, channel) in list(self.plottedData.keys()): # used to be in selected, now deselected
            plotInfo = self.plottedData.pop((groupText, channel))
            if groupText in self.tdms.digital:
                self.p2.removeItem(plotInfo[0])
                self.legend.removeItem(plotInfo[0])
            else:
                self.graphWidget.removeItem(plotInfo[0])
            plotInfo[1].deleteLater()
            plotInfo[2].deleteLater()
            plotInfo[3].deleteLater()
        else: 
            plotItem = self.add_to_plot(groupText, channel)
            self.plottedData[(groupText, channel)] = plotItem
            self.j += 1
            self.setInteraction(groupText, channel, plotItem, self.j)

    def initGraphWidget(self):
        self.j = -1
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
        self.p2.setRange(yRange = (0 - len(self.tdms.digital_adjustment)*0.01*1.2 , 1+ len(self.tdms.digital_adjustment)*0.01*1.2 ))
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

    def add_to_plot(self, groupText, channelText):
        time = self.tdms.timesDict[groupText]
        channel_info = self.tdms.tdms_file[groupText][channelText][:]
        np_channel_info = self.convert_to_np(channel_info)
        # print(groupText)
        if groupText in self.tdms.digital:
            np_channel_info = self.adjust_digital(channelText, np_channel_info)
            plotDataItem = pg.PlotDataItem(x = self.convert_to_np(time), y = np_channel_info, symbolBrush = pg.mkBrush('r'),
                                             symbol = None, pen=pg.mkPen('r', width = 1), name = groupText + ": " + channelText)
            self.p2.addItem(plotDataItem)
            self.legend.addItem(plotDataItem, groupText + ": " + channelText)
        else:
            plotDataItem = self.graphWidget.plot(x = self.convert_to_np(time), y = np_channel_info, symbolBrush = pg.mkBrush('r'),
                                             symbol = None, pen=pg.mkPen('r', width = 1), name = groupText + ": " + channelText)
        self.p2.setGeometry(self.graphWidget.plotItem.vb.sceneBoundingRect())
        return plotDataItem

    def convert_to_np(self, data):
        return np.array(data, dtype = float)
    
    def adjust_digital(self, channel, np_channel_info):
        for i in range(len(np_channel_info)):
            if abs(float(np_channel_info[i]) - 1) < 1.0e-6: # 1 
                np_channel_info[i] += self.tdms.digital_adjustment[channel]
            else: # 0
                np_channel_info[i] -= self.tdms.digital_adjustment[channel]
        return np_channel_info

    def setInteraction(self, group, channel, plotDataItem, i):
        label = QLabel(group + ":  " + channel) # group - channel
        self.interLayout.addWidget(label, i, 0)

        button = QPushButton('Choose Color', self)
        button.clicked.connect(partial(self.set_color, group, channel))
        self.interLayout.addWidget(button, i, 1)

        comboBox = QComboBox()
        [comboBox.addItems(['No Points', 'Circles', 'Squares', 'Triangles', 'Diamonds', 'Pluses'])]
        self.shapes = { 0 : None, 1 : 'o', 2 : 's', 3 : 't', 4 : 'd', 5: '+'}
        comboBox.setCurrentIndex(0)
        comboBox.currentIndexChanged.connect(partial(self.set_shape, group, channel))
        self.interLayout.addWidget(comboBox, i, 2)

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
    while tdms == "":
        file_to_open = input("Enter the tdms file name: ")
        #try:
        tdms = TDMS_File(file_to_open)
        #except:
        #    print("Make sure you entered a tdms file!\n")
    run_app(tdms)

def run_app(tdms):
    app = QApplication(sys.argv)
    main = MainWindow(tdms)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
