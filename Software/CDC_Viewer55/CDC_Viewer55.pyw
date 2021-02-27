# -*- coding: utf-8 -*-
"""
Created on Mon Jul 16 10:52:04 2018

@author: Ben_Hannes
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QAction, QMessageBox
from PyQt5.Qt import Qt
from CDC_Viewer_gui55 import Ui_MainWindow

from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
#import numpy as np
import random
import time
import glob
import serial
import serial.tools.list_ports
import threading
import shutil

class AppWindow(QMainWindow, Ui_MainWindow):
    '''
    Main window class including GUI construction, plot build and
    animation
    '''
    # initiate global vaiables
    firststart = True
    serConnEx = False
    aquisMode = False
    timerMode = True
    timeActive = False
    autoActive = False
    manualTrigger = False
    acqui_first = True
    start_time = 0
    triggerCount = 0
    old_triggerCount = triggerCount
    viewLCD = 1
    am_cdc = 0
    last_Trigger = 2
    tri_sig = False
    name = "em"
    directory = "./Data/"
    old_directory = directory
    if not os.path.isdir(directory):
        os.makedirs(directory)
    filename_len = 2
    directory_len = 2
    TempDir = "./temp/"
    if not os.path.isdir(TempDir):
        os.makedirs(TempDir)
    date = time.strftime("%Y-%m-%d_%H-%M_")
    nameTempFile = "temp"
    seperator_data = ';'
    seperator_decimal = ","
    endTempFile = ".csv"
    headTempFile = "Time /s;CDC"
    


    
    def __init__(self):
        '''
        class constructor
        '''
        super().__init__()
        
        #setup windows
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("CDC-Viewer")
        
        #get size of window
        self.width_window = int(self.width())
        self.height_window = int(self.height())
        
        #config menubar
        self.mb_loadset = QAction('Load Settings', self)
        self.mb_loadset.triggered.connect(lambda: self.set_presets(True))
        self.mb_safeset = QAction('Without auto connection', self)
        self.mb_safeset.triggered.connect(lambda: self.safeset("all"))
        self.mb_safeset_auto = QAction('With auto connection', self)
        self.mb_safeset_auto.triggered.connect(lambda: self.safeset("SetAutoConnect"))
        
        self.mb_dateopt = QAction('Prepend Date to Filename', self, checkable=True)
        self.mb_dateopt.setChecked(True)
        
        self.menubar = self.menuBar()
        self.mbfile = self.menubar.addMenu('&File')
        self.mbfile.addAction(self.mb_dateopt)
        self.bsave = self.mbfile.addMenu("Safe current Settings")
        self.bsave.addAction(self.mb_safeset)
        self.bsave.addAction(self.mb_safeset_auto)
        self.mbfile.addAction(self.mb_loadset)
        
        # Read Default Values from GUI
        self.stopTimer  = self.ui.timeBox.value()*60
        self.currentRun = self.ui.autoCurrentNo.value()
        
        # generate list of available serial ports and display them in MultiBox
        self.serialRewrite()
        
        # connect events
        self.ui.btnRefresh.clicked.connect(self.serialRewrite) # Refresh-Button
        self.ui.btnConnect.clicked.connect(self.handleSerial) # Connect-Button
        
        # set No of Detectors
        self.ui.SensorNo.valueChanged.connect(self.handleDetectorNo) # check changes of SensorNo
        
        # Save Options
        self.ui.cboxAutosave.clicked.connect(self.disable_autosave) # disable Autosave checkbox
        self.ui.btnSave.clicked.connect(self.file_save) #SanpSave-Button
        self.ui.autoSetDirectory.clicked.connect(self.directory_autosave) # Select Directory-Button
        self.ui.autoDirectory.textChanged.connect(self.change_filename) # check changes of Directory
        self.ui.autoSetFilename.clicked.connect(self.file_autosave) # Set Filename-Button
        self.ui.autoFilename.textChanged.connect(self.change_filename) # check changes of Filename
        
        # Data acquisition
        self.ui.comboLiveView.activated.connect(self.addLiveView) # activate LiveView
        self.ui.btnacquisition.clicked.connect(self.acquisition) # Button Start acquisition
        self.ui.pbnTrigger.clicked.connect(self.handTrigger) # Trigger-Button
        self.ui.selectLCD.activated.connect(self.LCDoutput) #change detector signal ploted on LCD
        
        # Mode
        self.ui.rbtnAuto.clicked.connect(self.auto_mode) # Start/Stop-Trigger RadioButton
        self.ui.rbtnTime.clicked.connect(self.auto_mode) # Start-Trigger Stop-Time RadioButton
        self.ui.cboxRestart.stateChanged.connect(self.no_restart) # no restart Checkbox
        self.ui.autoSetNo.clicked.connect(self.Number_set) # Set Number Button
        self.ui.autoCurrentNo.valueChanged.connect(self.change_CurrentNo) # check changes of current Number
        self.ui.ToggleTrigger.clicked.connect(self.toggle_trigger) # Toggle-Button
        self.ui.timeSet.clicked.connect(self.time_set) # Set Time Button
        self.ui.timeBox.valueChanged.connect(self.change_timeBox) # check changes of time
        
        # Setup Axis rescale
        self.ui.setxmin.valueChanged.connect(self.setPlotDim)
        self.ui.setxmax.valueChanged.connect(self.setPlotDim)
        self.ui.setymin.valueChanged.connect(self.setPlotDim)
        self.ui.setymax.valueChanged.connect(self.setPlotDim)
        
        #Modify UI
        self.ui.autoDirectory.setStyleSheet("color: rgb(0, 128, 0);")
        self.ui.autoDirectory.setText(self.directory)
        self.ui.autoCurrentNo.setStyleSheet("color: rgb(0, 128, 0);")
        
        # Get Values from a File with Presets
        self.set_presets(False)

    def closeEvent(self, event):
        self.safeset("preset")
        if self.aquisMode == True :
            buttonReply = QMessageBox.question(self, 'Exit', "Really?", QMessageBox.Yes | QMessageBox.No)
            if buttonReply == QMessageBox.Yes:
                event.accept()
                self.safeset("preset")
            if buttonReply == QMessageBox.No:
                event.ignore()



    def handleSerial(self):
        '''
        Open/Close serial connection and display status
        in statusBar()
        '''
        # self.serConnEx is bool for serial open (true) or closed (false)
        if self.serConnEx == True:
            try: 
                self.ser.close()
                self.serConnEx = False
                self.acquibtn() # disallow acquisition
                self.ui.btnConnect.setText("Connect")
                self.ui.btnRefresh.setEnabled(True)
                self.statusBar().showMessage("Serial connection closed")
                
            except:
                self.statusBar().showMessage("Error closing serial connection!")
        else:
            try:
                portConn = self.ui.serialSlots.currentText()
                self.ser = serial.Serial(portConn, 19200, timeout=1)
                self.serConnEx = True
                self.acquibtn() # allow acquisition
                self.ui.btnConnect.setText("Disconnect")
                self.ui.btnRefresh.setEnabled(False)
                self.statusBar().showMessage("Serial connection opened")

            except:
                self.statusBar().showMessage("Error establishing serial connection!")

    def serialRewrite(self):
        self.ui.serialSlots.clear()
        ports = list(serial.tools.list_ports.comports())
        for element in ports:
            if element[1][:15] == "USB-SERIAL CH34":
                self.ui.serialSlots.addItem(element[0])
            


    def handleDetectorNo(self):
        # if self.am_cdc == 0:
            # self.mb_loadset.setEnabled(False)
            # self.ui.selectLCD.setEnabled(True)
        #self.ui.selectPlot.setEnabled(True)
        self.am_cdc = self.ui.SensorNo.value()
        self.acquibtn()
        self.ui.selectLCD.clear()
        for client in range(1, (self.am_cdc+1)):
            self.ui.selectLCD.addItem(str(client))
        self.setup_datapack() # setup datasets
        if int(self.ui.comboLiveView.currentText())!=0:
            self.set_plot() # generate plot
    
    def addLiveView(self): #add/delete LiveView
        self.hshow(int(self.ui.comboLiveView.currentText()))
        if self.am_cdc != 0: # block actions if no number of clients is set
            if self.firststart == True : #add plot if never a plot was created
                self.set_plot()
            elif self.plt_column == int(self.ui.comboLiveView.currentText()):
                pass
            elif int(self.ui.comboLiveView.currentText())== 0: #delete plot
                self.delete_plot()
                self.plt_column = 0
                self.resize(self.width_window, self.height())
            elif self.plt_column != 0: #delete plot and add new plot with different number of column 
                self.set_plot()
            elif int(self.ui.comboLiveView.currentText())!= 0: #adds a plot if ever a plot was created
                self.set_plot(True)
            
        
    def set_plot(self, reaktivate = False):
        if self.firststart == False and not reaktivate: #used in case of a change in the number of clients
            self.delete_plot()
        if self.firststart == True or reaktivate:
            self.resize(1200, self.height()) #enlarge window for plot
        self.firststart = False
        
        # generate figure instance with self.am_cdc subplots
        self.fig = plt.figure(constrained_layout=True)
        # self.fig, self.ax = plt.subplots(self.am_cdc, 1, squeeze=False)
        # plt.tight_layout()
        
        # generate canvas instance with navigationtoolbar
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # add instances to GUI window
        self.ui.plotArea.addWidget(self.toolbar)
        self.ui.plotArea.addWidget(self.canvas)
        #self.layout()
        
        # intialize am_cdc line objects (one for each axes)
        self.gs0 = gridspec.GridSpec(1, 1, figure=self.fig)
        self.plt_column = int(self.ui.comboLiveView.currentText())
        plt_rows = int(((self.am_cdc/self.plt_column)+0.9)//1) #round up to next int 
        self.gs1 = gridspec.GridSpecFromSubplotSpec(plt_rows, self.plt_column, subplot_spec=self.gs0[0])

        self.line = []
        self.ax = []
        for index in range(self.am_cdc):
            self.ax.append(self.fig.add_subplot(self.gs1[index]))
            self.linei, = self.ax[index].plot([], [], animated=True, lineWidth = 1)
            self.line.append(self.linei)
            self.ax[index].set_xlabel('Time /s')
            self.ax[index].set_ylabel('Reading /a.u.')
            self.ax[index].legend(['CDC ' + str(index+1)])
            
        
        # call animation class
        self.ani = FuncAnimation(self.fig, self.update, init_func=self.init, blit=True, interval = 200 , repeat=False)
        self.canvas.draw()

        self.ui.BoxPlot.setEnabled(True)
        self.ui.PlotFrame.show()

    def delete_plot(self):
        self.ani.event_source.stop() #stop animation function
        self.canvas.close()
        self.toolbar.deleteLater()
        self.canvas.deleteLater()
        self.ui.BoxPlot.setEnabled(False)
        self.ui.PlotFrame.hide()

    def setup_datapack(self): #generate / reset storage for data
        self.datapackx = [] #setup list for x-values
        self.datapacky = [] #setup list for y-values
        for client in range(0, self.am_cdc):  # generate fist dimension of datapackx/y with size self.am_cdc
            self.datapackx.append([])
            self.datapacky.append([])

    def init(self):
        '''
        init-function for plot animation 
        '''
        #read values from UI for plot
        self.hshow("Init")
        xmin = self.ui.setxmin.value()
        xmax = self.ui.setxmax.value()
        ymin = self.ui.setymin.value()
        ymax = self.ui.setymax.value()
        for index in range(self.am_cdc): # setup plot view
            self.ax[index].set_xlim( xmin, xmax)
            self.ax[index].set_ylim( ymin, ymax)
            # self.ax[index].grid()
            
        # self.canvas.draw()
        return self.line

    def update(self, frame):
        '''
        update-function for plot animation, gets called
        frequently by plot-animation class
        '''
        try:
            for client in range(0, self.am_cdc):
                data_minlen = min(len(self.datapackx[client]),len(self.datapacky[client]))-1 #make sure that the shape fits the shorter datapack
                self.line[client].set_data(self.datapackx[client][0:data_minlen], self.datapacky[client][0:data_minlen])
            # self.hshow(self.line)
            return self.line
        except:
            self.hshow("error")

    def acquisition(self):
        if self.acqui_first == True:
            self.acqui_first = False;
            self.mb_loadset.setEnabled(False)
            self.ui.selectLCD.setEnabled(True)
            self.acqui_first
        '''
        start/stop of acquisition mode (=population of result-register with data)
        '''
        
        #self.aquisMode is bool for acquisition is acive (true) or inactive (false)
        if self.aquisMode == False:
            self.aquisMode = True
            self.ui.btnConnect.setEnabled(False) # disallow Disconnect
            self.ui.SensorNo.setEnabled(False)
            self.ui.serialSlots.setEnabled(False)
            self.file_control('w') #Create Temp-Data
            self.setup_datapack() # reset result-draw-register
            self.start_time = time.time() # save start-time as reference
            # start thread for data receiving from serial port
            self.th = threading.Thread(target = self.populateResutlist)
            self.th.setDaemon(True)
            self.th.start() 
            self.statusBar().showMessage("Aquiring data ...")
            self.ui.btnacquisition.setText("Stop acquisition")
            self.ui.pbnTrigger.setEnabled(True)
        else:
            self.aquisMode = False
            self.ui.btnConnect.setEnabled(True) # allow Disconnect
            self.ui.SensorNo.setEnabled(True)
            self.ui.serialSlots.setEnabled(True)
            self.file_control('c') #Close Temp-Data
            self.statusBar().showMessage("Data acquisition stopped.")
            self.ui.btnacquisition.setText("Start acquisition")
            self.ui.pbnTrigger.setEnabled(False)
            
    def populateResutlist(self):
        '''
        Receive data from serial port, display them in LCD-box and append
        new data to result-register
        '''
        trigger_stop = False
        saveFile = False
        reset = False
        saveCount = []  #generate counter and storange for temp data
        saveStr = []
        for i in range(self.am_cdc):
            saveCount.append(0)
            saveStr.append("")
        while (self.aquisMode == True and trigger_stop == False):
            try:
                receive_raw = self.ser.readline().decode() # decode raw-data
                detector_id = str(receive_raw)
                # self.hshow(receive_raw)
                # self.hshow(detector_id[0:3])
                sveTime = round(time.time() - self.start_time,2) # time since Trigger-Event
                # self.ui.lcdTime.display('{:.1f}'.format(sveTime))
                
                if str(detector_id[0:3]) == "Tri":  #for Prince: Tri1 = Start/Stop-Trigger ##for CE-MS (Agilent) Trig1= Start-Trigger Trig2=Stop-Trigger 
                    self.hshow("******")
                    self.hshow(detector_id)
                    self.hshow("******")
                    if (self.last_Trigger == 1 and self.triggerCount % 2 == 1) or str(detector_id[0:4]) == "Tri1":
                        self.tri_sig = True
                        self.last_Trigger = 2
                    if str(detector_id[0:4]) == "Tri1":
                        self.last_Trigger = 1
                    self.hshow("Last-Trigger: ")
                    self.hshow(self.last_Trigger)
                    if detector_id[4:5] == ";": # Trigger only from master device possible
                        self.tri_sig = False
                
                if ((self.tri_sig == True and self.ui.extTrigger.isChecked() == True) or (self.timeActive == True and sveTime > self.stopTimer and self.triggerCount % 2 == 1) or self.manualTrigger == True):
                    self.hshow(self.triggerCount) # Ausgabe der Anzahl an Triggern
                    self.tri_sig = False
                    if self.ui.cboxAutosave.isChecked():
                        self.triggerCount = self.triggerCount+1
                        reset = True
                    elif (self.timeActive == True and sveTime > self.stopTimer and self.triggerCount % 2 == 1): # Save File in Time Mode after StopTime
                        saveFile = True
                        if not self.ui.cboxRestart.isChecked(): # disable automatic restarting in Time Mode
                            self.timeActive = False
                        self.hshow("Save_Time Mode")
                    elif (self.timeActive == True and ((not self.manualTrigger) or (self.manualTrigger and self.ui.cboxRestart.isChecked()))): # Block extTrigger in Time Mode and allow Reset with Trigger-Button if no_restart is not set
                        self.hshow("###################Trigger disabled###################")    
                    elif (self.timeMode == True and self.triggerCount % 2 == 0): # Start trigger in Time Mode
                        self.hshow("###################Trigger Time Mode###################")
                        self.timeActive = True
                        reset = True
                        if self.ui.cboxRestart.isChecked(): # Disable Trigger-Button after first start if no_restart is activated
                            self.ui.pbnTrigger.setEnabled(False)
                    # elif (self.autoActive == True and self.triggerCount % 2 == 1): # Save File in Start/Stop-Mode
                    elif (self.triggerCount % 2 == 1): # Save File in Start/Stop-Mode or with Stop-Button in Time-Mode
                        self.hshow("Save_Start-Stop Mode")
                        saveFile = True
                    else:   # Start-Trigger in Start/Stop-Mode
                        self.hshow("###################Trigger Start/Stopp###################")
                        reset = True
                    if saveFile == True:
                        saveFile = False
                        self.autoSave()
                        self.triggerCount = self.triggerCount+1 #change number of trigger signals
                        self.currentRun = self.currentRun + 1 #change  number of runs
                        self.ui.autoCurrentNo.setValue(self.currentRun) #push number of runs to gui
                        trigger_stop = True
                        self.aquisMode = False
                        self.acquisition()
                    if reset == True:
                        reset = False
                        self.triggerCount = self.triggerCount+1 #change number of trigger signals
                        trigger_stop = True
                        self.aquisMode = False
                        self.acquisition()
                elif str(detector_id[0:3]) == "CDC":
                    trigger_event,tempbat,calib,receive_2 = receive_raw.split(";")
                    receive = round((((int(receive_2)-8388608)*4096)/16777216)+(int(calib)*(21000/(128)-91.450)),3) #conversion raw-data to fF round((((int(receive_2)-(2**23))*4096)/(2**24))+(int(calib)*(21000/(2**7)-91.450)),3)
                    voltage = round(int(tempbat)*0.0145,2)
                    index_cdc = int(detector_id[3:4])-1 #read number of detector and calculate index
                    # self.hshow(index_cdc)
                    if 0 <= index_cdc < self.am_cdc :
                        self.datapackx[index_cdc].append(sveTime) #append time since trigger to list for plot
                        self.datapacky[index_cdc].append(receive) #append signal since trigger to list for plot
                        try: 
                            saveStr[index_cdc] = saveStr[index_cdc] + str(sveTime) + self.seperator_data + str(receive) + "\n" #append data temp data
                            saveCount[index_cdc] += 1
                            if(saveCount[index_cdc]%20 == 0):   #save tempdata every 20th time
                                saveStr[index_cdc] = saveStr[index_cdc].replace(".", self.seperator_decimal)
                                self.d[index_cdc].write(saveStr[index_cdc])
                                saveStr[index_cdc] = ""
                                # print("saved")
                        except:
                            pass
                        if index_cdc == self.viewLCD-1:
                            self.ui.lcdSerRead.display('{:.3f}'.format(receive)) # Display sensor value in LCD
                            self.ui.lcdVoltage.display('{:.2f}'.format(voltage)) # Display sensor value in LCD
                            self.ui.lcdTime.display('{:.1f}'.format(sveTime))
                else:
                    self.hshow(receive_raw)
                self.manualTrigger = False
                if(not self.ui.cboxAutosave.isChecked() or old_triggerCount != triggerCount):
                    if(self.triggerCount % 2 == 0):
                        self.ui.pbnTrigger.setText("Inject")
                        self.ui.lbRun.setText("Next run")
                    else:
                        self.ui.pbnTrigger.setText("Stop run")
                        self.ui.lbRun.setText("Current run")
            except:
                pass
            #    self.hshow("error_pop")
            #    self.aquisMode = True
            #    self.acquisition()
            #    self.handleSerial()
        #self.file_control('c')
        
    def setPlotDim(self):
        '''
        rescale plot dimensions according to parameters from GUI
        '''
        self.hshow("setPlotDim")
        if self.am_cdc != 0 and int(self.ui.comboLiveView.currentText()) != 0:
            xmin = self.ui.setxmin.value()
            xmax = self.ui.setxmax.value()
            ymin = self.ui.setymin.value()
            ymax = self.ui.setymax.value()
            for index in range(self.am_cdc):
                self.ax[index].set_xlim( xmin, xmax)
                self.ax[index].set_ylim( ymin, ymax)
                # self.ax[index].grid()
            self.canvas.draw()

    def directory_autosave(self):
        self.directory = QFileDialog.getExistingDirectory(self, 'Select Directory',self.ui.autoDirectory.text()) + "/"
        if self.directory != "/":
            self.ui.autoDirectory.setText(self.directory)
            self.ui.autoDirectory.setStyleSheet("color: rgb(0, 128, 0);")
        
    def file_autosave(self):
        self.name = self.ui.autoFilename.text()
        self.ui.autoFilename.setStyleSheet("color: rgb(0, 128, 0);")
        # self.autoMode = True
        self.toggle_mode()
        self.acquibtn()
        # self.ui.autoFilename.setText(self.name)
     
    def change_filename(self):
        if self.name != self.ui.autoFilename.text():
            self.ui.autoFilename.setStyleSheet("color: rgb(0, 0, 0);")
        else:
            self.ui.autoFilename.setStyleSheet("color: rgb(0, 128, 0);")
        if len(self.ui.autoFilename.text()) > self.filename_len and len(self.ui.autoDirectory.text()) > self.directory_len:
            self.ui.autoSetFilename.setEnabled(True)
        else:
            self.ui.autoSetFilename.setEnabled(False)

    def file_save(self):
        '''
        Open SaveFile dialog, store data in file
        '''
        name = QFileDialog.getSaveFileName(self, 'Save File')
        for i in range(0,self.am_cdc):
            cdcNo = i+1;
            temp_name = str(name[0]) + '_D' + str(cdcNo) + '.csv'
            sf=open(temp_name, 'w')
            sf.write(str(self.headTempFile+ str(cdcNo) + ' /a.u.\n'))
            for p in range(0, len(self.datapackx[i])):
                # self.hshow(self.datapackx[i])
                saveStrSnap = str(self.datapackx[i][p]) + self.seperator_data + str(self.datapacky[i][p]) + '\n'
                sf.write(saveStrSnap.replace(".",self.seperator_decimal))
            sf.close()

    def autoSave(self):
        date = time.strftime("%Y-%m-%d_") #save date for autosave data
        for i in range(0, self.am_cdc):
            if(self.mb_dateopt.isChecked() == True):
                file_link = self.directory + date +self.name + '_R'+ str(self.currentRun) + '_D' +str(i+1) + self.endTempFile
            else:
                file_link = self.directory + self.name + '_R'+ str(self.currentRun) + '_D' +str(i+1) + self.endTempFile
            self.hshow(file_link)
            self.d[i].close()
            shutil.copy(self.tempfiles[i], file_link)
        self.file_control('w')
        
    def time_set(self): # process set action in timer box 
        self.stopTimer = self.ui.timeBox.value()*60 # convert min to seconds
        self.ui.timeBox.setStyleSheet("color: rgb(0, 128, 0);") # change color to green to visualise accepted change
        self.ui.rbtnTime.setEnabled(True) #enable Radiobutton for Stop-Time Option
        self.ui.cboxRestart.setEnabled(True) #enable checkbox for disable restart by trigger after time-stop
        if self.stopTimer == 0.0: # change to Start/Stop-Mode in case of a 0 min timer
            self.ui.rbtnAuto.setChecked(True)
            self.auto_mode()
            self.ui.rbtnTime.setEnabled(False)
            self.ui.cboxRestart.setEnabled(False)
        self.hshow(self.stopTimer)
        
    def Number_set(self):
        self.currentRun = self.ui.autoCurrentNo.value() # process set action in current run box 
        self.ui.autoCurrentNo.setStyleSheet("color: rgb(0, 128, 0);")
        self.hshow(self.currentRun)
            
    def auto_mode(self):
        if self.ui.rbtnTime.isChecked() : # Activate Trigger/Time-Mode
            self.timeMode = True
            self.autoActive = False
            self.triggerCount = 0
            self.ui.cboxRestart.setEnabled(True)
            self.hshow("Time Mode true")
            self.ui.ToggleTrigger.setEnabled(False)
        if self.ui.rbtnAuto.isChecked(): # Activate Trigger Start/Stop-Mode
            self.timeMode = False
            self.timeActive = False
            self.autoActive = True
            self.hshow("Auto Mode true")
            self.triggerCount = 0
            self.ui.cboxRestart.setChecked(False)
            self.ui.cboxRestart.setEnabled(False)
            self.ui.ToggleTrigger.setEnabled(True)
            
            
    def toggle_mode(self,b=True):
        self.acquibtn() # Button Start acquisition
        self.ui.modeBox.setEnabled(b)
        self.ui.autoCurrentNo.setValue(self.currentRun)
        if self.ui.rbtnTime.isChecked() :
            self.ui.ToggleTrigger.setEnabled(False)
        self.hshow(self.stopTimer)
        if self.stopTimer == 0.0 and b:
            self.ui.rbtnAuto.setChecked(True)
            self.auto_mode()
            self.ui.rbtnTime.setEnabled(False)
            self.ui.cboxRestart.setEnabled(False)
            
    
    def toggle_trigger(self):
        self.triggerCount = self.triggerCount+1
        
    def handTrigger(self):
        self.manualTrigger = True
        
    def disable_autosave(self):
        if self.ui.cboxAutosave.isChecked():
            if(self.aquisMode == True and not(self.timeMode == False and self.autoActive == False)):
                self.acquisition()
            self.hshow("disable_autosave")
            self.timeMode = False
            self.timeActive = False
            self.autoActive = False
            self.triggerCount = 0
            self.ui.cboxRestart.setChecked(False)
            self.ui.pbnTrigger.setText("Reset")
            self.toggle_mode(False)
            b2 = False
        else:
            self.ui.pbnTrigger.setText("Inject")
            if len(self.ui.autoDirectory.text()) > self.directory_len and self.name != "em":
                self.toggle_mode(True)
            if(self.aquisMode == True):
                self.acquisition()
            b2 = True
        self.ui.autoSetDirectory.setEnabled(b2) # Select Directory-Button
        self.ui.autoDirectory.setEnabled(b2) # check changes of Directory
        self.ui.autoSetFilename.setEnabled(b2) # Set Filename-Button
        self.ui.autoFilename.setEnabled(b2) # check changes of Filename
        
    def no_restart(self):
        self.hshow("no_restart")
        if not self.ui.cboxRestart.isChecked():
            self.timeActive = False
            self.ui.pbnTrigger.setEnabled(True)
    
    def change_CurrentNo(self):
        self.hshow("change_CurrentNo")
        if self.currentRun != self.ui.autoCurrentNo.value():
            self.ui.autoCurrentNo.setStyleSheet("color: rgb(0, 0, 0);")
        else:
            self.ui.autoCurrentNo.setStyleSheet("color: rgb(0, 128, 0);")
            
    def change_SensorNo(self):
        self.handleDetectorNo()
        self.hshow("change_SensorNo")
        if self.am_cdc != self.ui.SensorNo.value():
            self.ui.SensorNo.setStyleSheet("color: rgb(0, 0, 0);")
        else:
            self.ui.SensorNo.setStyleSheet("color: rgb(0, 128, 0);")
    
    
    def change_timeBox(self):
        self.hshow("change_timeBox")
        if self.stopTimer != self.ui.timeBox.value()*60:
            self.ui.timeBox.setStyleSheet("color: rgb(0, 0, 0);")
        else:
            self.ui.timeBox.setStyleSheet("color: rgb(0, 128, 0);")
     
    def acquibtn(self):
        if self.serConnEx == True and self.am_cdc != 0 and ((len(self.ui.autoFilename.text()) > self.filename_len and len(self.ui.autoDirectory.text()) > self.directory_len and self.name != "em") or self.ui.cboxAutosave.isChecked()) :
            self.ui.btnacquisition.setEnabled(True)
        else:
            self.ui.btnacquisition.setEnabled(False)
            
            
    def LCDoutput(self):
        self.viewLCD = int(self.ui.selectLCD.currentText())
        self.ui.lcdSerRead.display('{:.3f}'.format(0))
        self.ui.lcdTime.display('{:.1f}'.format(0))
        
        
    def file_control(self, way):
        if way in ['w', 'a'] :
            self.tempfiles = []
            self.d=[]
            self.hshow("reset-temp")
            dateTemp = time.strftime("%Y-%m-%d_%H-%M-%S") #save date for temp data
            for i in range(0,self.am_cdc):
                cdcNo = i+1;
                self.tempfiles.append(self.TempDir+dateTemp+self.nameTempFile+"_D"+str(cdcNo)+ self.endTempFile)
                self.d.append(open(self.tempfiles[i], way))
                if way == 'w':
                    self.d[i].write(str(self.headTempFile+ str(cdcNo) + ' /a.u.\n'))
        if way == 'c':
            self.tempfiles = []
            for i in range(0,self.am_cdc):
                self.d[i].close()
        self.hshow(self.tempfiles)
        self.hshow("file_control")
# start application#

    def set_presets(self, manuel_presetfile):
        # Get Values from a File with Presets
        if(manuel_presetfile):
            setfile =  QFileDialog.getOpenFileName(self, 'Open file', '',"Preset Files (*.txt)")
            setfile = setfile[0]
            self.hshow(setfile)
        else:
            setfile = "preset.txt"
        try:
            if self.serConnEx == True :
                self.handleSerial()
            self.mb_dateopt.setChecked(True)
            self.ui.extTrigger.setChecked(True)
            presets_raw = open(setfile).readlines()
            presets = []
            for pset in presets_raw:
                presets.append(pset.split("="))
            for element in presets:
                if element[0] == "SensorNo":
                    self.ui.SensorNo.setValue(int(element[1].strip()))
                    self.handleDetectorNo()
                if element[0] == "LiveView":
                    index = self.ui.comboLiveView.findText(element[1].strip(), Qt.MatchFixedString)
                    if int(index) != -1:
                        self.ui.comboLiveView.setCurrentIndex(index)
                        self.addLiveView()
                if element[0] == "Port":
                    index = self.ui.serialSlots.findText(element[1].strip(), Qt.MatchFixedString)
                    if int(index) != -1:
                        self.ui.serialSlots.setCurrentIndex(index)
                if element[0] == "AutoConnect" and element[1].strip()=="True":
                    self.handleSerial()
                if element[0] == "autoDirectory" and os.path.isdir(element[1].strip()):
                    self.ui.autoDirectory.setText(element[1].strip())
                    self.directory = element[1].strip()
                    self.ui.autoDirectory.setStyleSheet("color: rgb(0, 128, 0);")
                    self.old_directory = element[1].strip()
                    # if not os.path.isdir(element[1].strip()):
                        # os.makedirs(element[1].strip())
                if element[0] == "autoFilename":
                    self.ui.autoFilename.setText(element[1].strip())
                    self.file_autosave()
                if element[0] == "prependDate" and element[1].strip()=="False":
                        self.mb_dateopt.setChecked(False)
                if element[0] =="extTrigger" and element[1].strip()=="False":
                        self.ui.extTrigger.setChecked(False)
                if element[0] == "timeBox" :
                    self.ui.timeBox.setValue(float(element[1].strip()))
                    self.time_set()
                    self.ui.rbtnTime.setChecked(True)
                    self.auto_mode()
                if element[0] == "setxmin" :
                    self.ui.setxmin.setValue(int(element[1].strip()))
                if element[0] == "setxmax" :
                    self.ui.setxmax.setValue(int(element[1].strip()))
                if element[0] == "setymin" :
                    self.ui.setymin.setValue(int(element[1].strip()))
                if element[0] == "setymax" :
                    self.ui.setymax.setValue(int(element[1].strip()))
        except:
            pass

    def safeset(self,opt):
        '''
        Open SaveFile dialog, store Settings in file
        '''
        #auto=True --> Loading Preset-File set Client Number automatically
        if(opt=="preset"):
            temp_name = "preset.txt"
        else:
            name = QFileDialog.getSaveFileName(self, 'Save Setting File',"preset_","Data (*.txt)")
            temp_name = str(name[0])
        try:
            filename = temp_name.split("/")
            sf=open(temp_name, 'w')
            sf.write("Settings: ")
            sf.write(filename[-1] + "\n")
            sf.write("SensorNo=")
            sf.write(str(self.ui.SensorNo.value()) + "\n")
            sf.write("LiveView=")
            sf.write(self.ui.comboLiveView.currentText() + "\n")
            sf.write("Port=")
            sf.write(self.ui.serialSlots.currentText() + "\n")
            if(opt=="SetAutoConnect"):
                sf.write("AutoConnect=True\n")
            sf.write("autoDirectory=")
            if(opt=="all" or opt=="SetAutoConnect" or self.old_directory == self.directory):
                sf.write(self.ui.autoDirectory.text() + "\n")
            else:
                dirBase = self.ui.autoDirectory.text().rfind("/",0,-1) #erase last folder
                sf.write(self.ui.autoDirectory.text() [0:dirBase] + "/\n")
            if(opt=="all" or opt=="SetAutoConnect"):
                sf.write("autoFilename=")
                sf.write(self.ui.autoFilename.text() + "\n")
            if(self.mb_dateopt.isChecked()!=True):
                sf.write("prependDate=False\n")
            if(self.ui.extTrigger.isChecked() != True):
                sf.write("extTrigger=False\n")
            if(self.ui.rbtnTime.isChecked() == True):
                sf.write("timeBox=")
                sf.write(str(self.ui.timeBox.value()) + "\n")
            sf.write("setxmin=")
            sf.write(str(self.ui.setxmin.value()) + "\n")
            sf.write("setxmax=")
            sf.write(str(self.ui.setxmax.value()) + "\n")
            sf.write("setymin=")
            sf.write(str(self.ui.setymin.value()) + "\n")
            sf.write("setymax=")
            sf.write(str(self.ui.setymax.value()))
            sf.close()
        except:
            pass
            
    def hshow(self, data):
        if False:
            print(data)
        
app = QApplication(sys.argv)
w = AppWindow()
w.show()
sys.exit(app.exec_())

