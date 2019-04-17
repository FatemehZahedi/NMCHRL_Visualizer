#!/usr/bin/python3

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                            QPushButton, QButtonGroup, QFileDialog,
                            QMessageBox, QSizePolicy)
from PyQt5.QtCore import QObject, QThread, pyqtSignal

import os
import sys
import pyqtgraph as pg
import socket
import threading
import time
import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas

class TwoDimSharedMemoryConsumer(QThread):

    SupplyFilteredData = pyqtSignal(np.ndarray)
    SupplyUnfilteredData = pyqtSignal(np.ndarray)

    def __init__(self, filterCoeffs, dtype, dtypeBytes, shm):
        # filterCoeffs is a list of 2 numpy arrays of Butterworth coefficients
        QThread.__init__(self)
        self._dataLenMax = 11
        self._dataUnfilt = np.zeros((2,self._dataLenMax))
        self._dataFilt = np.zeros((2,self._dataLenMax))
        self.SetFilter(filterCoeffs)
        self.SetDataType(dtype)
        self.SetDataTypeBytes(dtypeBytes)
        self.SetSharedMemory(shm)
        self._Timer = QtCore.QTimer()
        self._Timer.setInterval(1.0) # 1ms interval (1000Hz)
        self._Timer.timeout.connect(self.RunTask)

    def SetFilter(self, filterCoeffs):
        # filterCoeffs is a list of 2 numpy arrays of Butterworth coefficients
        self._filterNum = np.zeros(self._dataLenMax)
        self._filterDen = np.zeros(self._dataLenMax)
        self._filterNum[0:len(filterCoeffs[0])] = filterCoeffs[0]
        self._filterDen[0:len(filterCoeffs[1])] = filterCoeffs[1]

    def ProcessData(self, newData):
        # Shift data array contents for new data
        self._dataUnfilt[:,1:] = self._dataUnfilt[:,0:-1]
        self._dataFilt[:,1:] = self._dataFilt[:,0:-1]

        # Insert Data Into Unfiltered Array
        self._dataUnfilt[:,0] = newData

        # Filter data and insert into filtered array
        self._dataFilt[0,0] = (self._filterNum.dot(self._dataUnfilt[0,:]) -
                               self._filterDen[1:].dot(self._dataFilt[0,1:]))/self._filterDen[0]
        self._dataFilt[1,0] = (self._filterNum.dot(self._dataUnfilt[1,:]) -
                               self._filterDen[1:].dot(self._dataFilt[1,1:]))/self._filterDen[0]

    def SetDataType(self, dtype):
        self._dataType = dtype

    def SetDataTypeBytes(self, dtypeBytes):
        self._dataTypeBytes = dtypeBytes

    def SetSharedMemory(self, shm):
        self._shm = shm

    def ReadSharedMemory(self):
        nFloats = 2     #x and y coordinate
        data_bytes = self._shm.read(nFloats*self._dataTypeBytes)
        data_temp = np.frombuffer(data_bytes, dtype=self._dataType)
        return data_temp

    def RunTask(self):
        data_temp = self.ReadSharedMemory()
        self.ProcessData(data_temp)
        self.SupplyFilteredData(self._dataFilt[:,0])
        self.SupplyUnfilteredData(self._dataUnfilt[:,0])

    def StartTask(self):
        self._Timer.start()

    def StopTask(self):
        self._Timer.stop()


class MainWindow(QMainWindow):

    # Class Data

    _ipAddressStr = None
    _emgCommPort = 50040
    _emgDataPort = 50041
    _socketTimeout = 1.0 #seconds

    _emgDataThreadActive = False
    _emgCommThreadActive = False

    _emgDataQueue = deque(maxlen=5000)

    _emgServerAddress = None
    _activeEmgSensors = []
    _emgSensors = [] # filled in constructor
    _emgConnected = False
    _emgDataSourceDict = {
                         'EMG_CLIENT': 0,
                         'EMG_IPC'   : 1
                         }
    _emgDataSource = None

    _PlotTimer = None

    _threadname_emgdatarecv = "THREAD_EMGDATARECV"
    _threadname_emgcommrecv = "THREAD_EMGCOMMRECV"


    # Shared Memory Class Data
    _filterCoeffs = {
                    'nofilter': [np.array([1]),np.array([1])],
                    'defaultfilter': [np.array([1,2]),np.array([3,4,5])],
                    'customfilter': [np.array([1]),np.array([1])]
                    }
    _shmFile = None
    _shmKey = None

    _coordinatesUnfiltered = np.zeros(2)
    _coordinatesFiltered = np.zeros(2)

    _dataType = None
    _dataTypeBytes = None
    _shm = None
    _filter = None
    _SharedMemoryThread = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.showMaximized()
        uic.loadUi('visualizer_app.ui', self)

        self.InitTabWidgetSlots()
        self.InitTwoDimPlotTab()
        self.InitializeEmgTab()

        self.show()

    def InitTabWidgetSlots(self):
        self.tabWidget.currentChanged.connect(self.PrintTabName)

    def PrintTabName(self):
        print(self.tabWidget.currentWidget().objectName())

    def InitTwoDimPlotTab(self):
        self.Init2DPlot()
        self.Init2DButtons()
        self.Init2DPlotTimer()

    def Init2DPlot(self):
        circle1 = plt.Circle((0.5, 0.5), 0.2, color='r')
        self._plot2d = FigureCanvas(Figure(figsize=(10,10), tight_layout=True))
        self.horizontallayout_2d.insertWidget(2,self._plot2d)
        self._plot2dax = self._plot2d.figure.subplots()
        self._plot2dax.add_artist(circle1)

    def Init2DPlotTimer(self):
        self._plot2dTimer = QtCore.QTimer()
        self._plot2dTimer.setInterval(20) #20ms
        self._plot2dTimer.timeout.connect(self.Update2DPlot)


    def Init2DButtons(self):
        # Connect Pushbutton Clicked Signals to Slots
        self.btn_selectshmfile.clicked.connect(self.SelectShmFile)
        self.btn_connect2ddata.clicked.connect(self.Connect2DData)
        self.btn_selectfilterfile.clicked.connect(self.SelectFilterFile)
        self.btn_2dplotstart.clicked.connect(self.Start2DPlot)
        self.btn_2dplotstop.clicked.connect(self.Stop2DPlot)

        # Create radiobutton group for filters and add buttons
        self.rbtngroup_filter = QButtonGroup()
        self.rbtngroup_filter.addButton(self.rbtn_nofilter)
        self.rbtngroup_filter.addButton(self.rbtn_defaultfilter)
        self.rbtngroup_filter.addButton(self.rbtn_customfilter)

        # Connect radiobutton clicked signal to slot and set 'No Filter' as default button
        self.rbtngroup_filter.buttonClicked.connect(self.Set2DDataFilter)
        self.rbtn_nofilter.setChecked(True)
        self.rbtn_nofilter.click()

        # Create radiobutton group for shm data io data types
        self.rbtngroup_datatype = QButtonGroup()
        self.rbtngroup_datatype.addButton(self.rbtn_int32_t)
        self.rbtngroup_datatype.addButton(self.rbtn_uint32_t)
        self.rbtngroup_datatype.addButton(self.rbtn_int64_t)
        self.rbtngroup_datatype.addButton(self.rbtn_uint64_t)
        self.rbtngroup_datatype.addButton(self.rbtn_float32)
        self.rbtngroup_datatype.addButton(self.rbtn_float64)

        # Connect radiobutton clicked signal to slot and set 'No Filter' as default button
        self.rbtngroup_datatype.buttonClicked.connect(self.SetDataType)
        self.rbtn_float32.setChecked(True)
        self.rbtn_float32.click()

        # Connect Buttons to Start Shm Thread Task
        self.btn_shmthreadstart.clicked.connect(self.StartShmThreadTask)
        self.btn_shmthreadstop.clicked.connect(self.StopShmThreadTask)

    def StartShmThreadTask(self):

        # Disable Buttons For Data IO Buttons
        widgetlist = [self.btn_selectshmfile,
                      self.btn_selectfilterfile,
                      self.btn_connect2ddata,
                      self.btn_shmthreadstart]

        for rbtn in self.rbtngroup_filter.buttons():
            if not rbtn.isChecked():
                rbtn.setEnabled(False)

        for rbtn in self.rbtngroup_datatype.buttons():
            if not rbtn.isChecked():
                rbtn.setEnabled(False)

        for widget in widgetlist:
            widget.setEnabled(False)

        self.btn_shmthreadstop.setEnabled(True)

        if (self._SharedMemoryThread is not None):
            self._SharedMemoryThread.StartTask()

    def StopShmThreadTask(self):
        widgetlist = [self.btn_selectshmfile,
                      self.btn_selectfilterfile,
                      self.btn_connect2ddata,
                      self.btn_shmthreadstart]

        for rbtn in self.rbtngroup_filter.buttons():
            rbtn.setEnabled(True)

        for rbtn in self.rbtngroup_datatype.buttons():
            rbtn.setEnabled(True)

        for widget in widgetlist:
            widget.setEnabled(True)

        self.btn_shmthreadstop.setEnabled(False)

        if (self._SharedMemoryThread is not None):
            self._SharedMemoryThread.StopTask()

    def Update2DFilteredData(self, data):
        self._coordinatesFiltered = data

    def Update2DUnfilteredData(self, data):
        self._coordinatesUnfiltered = data

    def Connect2DData(self):

        # Connect shared memory
        self.ConnectSharedMemory()

        # Check Dependencies for TwoDimSharedMemoryConsumer
        msg = ""
        dependenciesNotMet = False
        if (self._dataType is None):
            msg += "Data Type Not Set\n"
            dependenciesNotMet = True
        if (self._dataTypeBytes is None):
            msg += "Data Type Bytes Not Set\n"
            dependenciesNotMet = True
        if (self._shm is None):
            msg += "Shared Memory Not Set\n"
            dependenciesNotMet = True
        if (self._filter is None):
            msg += "Filter Not Set"
            dependenciesNotMet = True
        if (dependenciesNotMet):
            msgbox = QMessageBox(text=msg)
            msgbox.exec_()
            return

        self._SharedMemoryThread = TwoDimSharedMemoryConsumer(self._filter,
                                                              self._dataType,
                                                              self._dataTypeBytes,
                                                              self._shm)
        self._SharedMemoryThread.SupplyFilteredData.connect(self.Update2DFilteredData)
        self._SharedMemoryThread.SupplyUnfilteredData.connect(self.Update2DUnfilteredData)
        self._SharedMemoryThread.StartTimer()


    def DisconnectSharedMemory(self):
        sysv_ipc.remove_shared_memory(self._shm.id)

    def SetButterworthCoeffsLabel(self, filterStr):
        coeffs = self._filterCoeffs[filterStr]
        numCoeffs = coeffs[0]
        denCoeffs = coeffs[1]
        msg = "Numerator:   {}\nDenominator: {}".format(numCoeffs, denCoeffs)
        self.lbl_buttercoefficients.setText(msg)

    def SetDataType(self, rbtn):
        btnname = rbtn.objectName()
        if (btnname == "rbtn_int32_t"):
            self._dataType = np.intc
            self._dataTypeBytes = 4 #bytes
        elif (btnname == "rbtn_uint32_t"):
            self._dataType = np.uintc
            self._dataTypeBytes = 4 #bytes
        elif (btnname == "rbtn_int64_t"):
            self._dataType = np.int_
            self._dataTypeBytes = 8 #bytes
        elif (btnname == "rbtn_uint64_t"):
            self._dataType = np.uint
            self._dataTypeBytes = 8 #bytes
        elif (btnname == "rbtn_float32"):
            self._dataType = np.single
            self._dataTypeBytes = 4 #bytes
        elif (btnname == "rbtn_float64"):
            self._dataType = np.double
            self._dataTypeBytes = 8 #bytes

    def Set2DDataFilter(self, rbtn):
        # Change Butterworth Coefficient Labels
        btnname = rbtn.text()
        if (btnname == "No Filter"):
            filterStr = 'nofilter'
        elif (btnname == "Default"):
            filterStr = 'defaultfilter'
        elif (btnname == "Custom"):
            filterStr = 'customfilter'
        self.SetButterworthCoeffsLabel(filterStr)

        # Set filter
        self._filter = self._filterCoeffs[filterStr]

        # Set filter in 2D shared memory thread
        if (self._SharedMemoryThread is not None):
            self._SharedMemoryThread.SetFilter(self._filter)

    def Start2DPlot(self):
        res = self.SetPlotBorders()
        if (res == 1):
            return

        widgetlist = [self.lineedit_xmin,
                      self.lineedit_xmax,
                      self.lineedit_ymin,
                      self.lineedit_ymax]

        for widget in widgetlist:
            widget.setEnabled(False)

        self._plot2dTimer.start()

    def Update2DPlot(self):
        print(self._coordinatesFiltered)

    def Stop2DPlot(self):
        widgetlist = [self.lineedit_xmin,
                      self.lineedit_xmax,
                      self.lineedit_ymin,
                      self.lineedit_ymax]

        for widget in widgetlist:
            widget.setEnabled(True)

    def SetPlotBorders(self):
        try:
            xmin = float(self.lineedit_xmin.text())
            xmax = float(self.lineedit_xmax.text())
            ymin = float(self.lineedit_ymin.text())
            ymax = float(self.lineedit_ymax.text())
            self._plot2dax.set_xlim(xmin,xmax)
            self._plot2dax.set_ylim(ymin,ymax)
            self._plot2dax.figure.canvas.draw()
            return 0
        except ValueError as err:
            msg = "Plot Border Input Could Not Be Converted To A Number"
            msgbox = QMessageBox(text=msg)
            msgbox.exec_()
            return 1

    def SelectShmFile(self):
        #Open filedialog box
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(directory=os.getcwd(), options=options)
        self._shmFile = filename
        self.lbl_shmfile.setText("FD: {}".format(self._shmFile))

    def SelectFilterFile(self):
        #Open filedialog box
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(directory=os.getcwd(), options=options)

        # Check if choosen item is a file, exit if not a file
        if (not os.path.isfile(filename)):
            if (len(filename) == 0):
                msg = "File: "
            else:
                msg = "File: Choosen Item Not a File"
            self.lbl_filterfile.setText(msg)
            return

        # Check that file has exactly 2 lines
        with open(filename) as f:
            for i,l in enumerate(f):
                pass
        linecount = i + 1
        if (linecount != 2):
            msg = "Error: File Did Not Contain Exactly 2 Lines"
            self.lbl_filterfile.setText(msg)
            return

        # Get coefficients
        temp = []
        f = open(filename)
        for line in f:
            coeffs = np.fromstring(line,sep=',')
            if (len(coeffs) == 0):
                msg = "Import Error: Check Butterworth Coefficient File"
                self.lbl_filterfile.setText(msg)
                f.close()
                return
            elif (len(coeffs) > 11):
                msg = "Import Error: Inputted Filter Greater Than 10th Order"
                self.lbl_filterfile.setText(msg)
                f.close()
                return
            temp.append(coeffs)

        # Set coefficients, lbls
        self._filterfile = filename
        [dir, fname] = os.path.split(filename)
        self._filterCoeffs['customfilter'] = temp

        self.lbl_filterfile.setText("File: {}".format(fname))
        self.rbtn_customfilter.setChecked(True)
        self.rbtn_customfilter.click()

    def ConnectSharedMemory(self):
        if (self._shmFile == None):
            msg = "Status: FD Not Chosen, Can't Connect"
            self.lbl_statusshmstream.setText(msg)
            return
        self._shmKey = sysv_ipc.ftok(self._shmFile, 255)
        self._shm = sysv_ipc.SharedMemory(self._shmKey, sysv_ipc.IPC_CREX)

    def InitializeEmgTab(self):
        self.InitEmgSockets()
        self.InitEmgButtons()
        self.InitEmgPlot()
        self.InitEmgLines()
        self.InitEmgPlotTimer()

    def InitEmgSockets(self):
        # Set socket timeouts
        self._emgCommSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._emgDataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._emgCommSocket.settimeout(self._socketTimeout)
        self._emgDataSocket.settimeout(self._socketTimeout)

        # Fill emg data queue with zeros
        temp = np.zeros(16)
        for i in range(0,5000):
            self._emgDataQueue.append(temp)

    def ConnectDataIO(self):
        if (self._emgDataSource == self._emgDataSourceDict['EMG_CLIENT']):
            ip_address = str(self.lineedit_ipaddress.text())
            if (ip_address != ""):
                self.lineedit_ipaddress.setText("")
                self.SetIPAddress(ip_address)
                emgCommPortConnected = self.ConnectEmgCommPort()
                emgDataPortConnected = self.ConnectEmgDataPort()

                # Start Threads for Reading EMG Communication and Data ports continuously
                if emgCommPortConnected:
                    self.StartCommReadThread()
                if emgDataPortConnected:
                    self.StartDataReadThread()
                msg = "Status: Connected\nIP: {}".format(self._ipAddressStr)
            else: #lineedit_ipaddress empty
                msg = "Input An IP Address"
            self.PrintToStatusLabel(msg)
        elif (self._emgDataSource == self._emgDataSourceDict['EMG_IPC']):
            pass

    def StartCommReadThread(self):
        # Stop EMG Comm Thread if its open
        self.StopCommReadThread()

        # Start EMG Comm Thread
        t = threading.Thread(target=self.ReadEmgCommForever, name=self._threadname_emgcommrecv, daemon=True)
        t.start()

    def StopCommReadThread(self):
        activeThreads = threading.enumerate() # returns list of active threads

        for t in activeThreads:
            if (t.name == self._threadname_emgcommrecv):
                self._emgCommThreadActive = False # this will force an end of the method the thread is running
                break

    def StartDataReadThread(self):
        # Stop EMG Data Thread if its open
        self.StopDataReadThread()

        # Start EMG Data Thread
        t = threading.Thread(target=self.ReadEmgDataForever, name=self._threadname_emgdatarecv, daemon=True)
        t.start()

    def StopDataReadThread(self):
        activeThreads = threading.enumerate() # returns list of active threads

        for t in activeThreads:
            if (t.name == self._threadname_emgdatarecv):
                self._emgDataThreadActive = False # this will force an end of the method the thread is running
                break

    def InitEmgButtons(self):
        self._emgSensors = [self.btn_emg1,
                           self.btn_emg2,
                           self.btn_emg3,
                           self.btn_emg4,
                           self.btn_emg5,
                           self.btn_emg6,
                           self.btn_emg7,
                           self.btn_emg8]
        # Add EMG Buttons to Layout
        for btn in self._emgSensors:
            btn.toggled.connect(self.UpdateActiveEmgList)

        # Make Data IO Button Group
        self._emgServerWidgetList = [self.groupbox_emgserver,
                                     self.lbl_ip,
                                     self.lbl_serverterminal,
                                     self.lineedit_ipaddress,
                                     self.lineedit_servercmd,
                                     self.btn_sendservercmd,
                                     self.textedit_serverreplywindow]
        self._emgIpcWidgetList = [self.groupbox_emgipc,
                                  self.btn_choosemqfd,
                                  self.lbl_mqfd]

        self.emgdataio_rbtngroup = QButtonGroup()
        self.emgdataio_rbtngroup.addButton(self.rbtn_emgserver)
        self.emgdataio_rbtngroup.addButton(self.rbtn_emgipc)
        self.emgdataio_rbtngroup.buttonClicked.connect(self.EmgDataIoRbtnSlot)
        self.rbtn_emgserver.setChecked(True)
        self.rbtn_emgserver.click()

        # Activate/Deactivate EMGs
        self.btn_connectemgio.clicked.connect(self.ConnectDataIO)
        self.btn_sendservercmd.clicked.connect(self.SendEmgCommand)
        self.btn_plotstart.clicked.connect(self.StartEmgPlot)
        self.btn_plotstop.clicked.connect(self.StopEmgPlot)

    def EmgDataIoRbtnSlot(self, rbtn):
        rbtnname = rbtn.objectName()
        if (rbtnname == "rbtn_emgserver"):
            for widget in self._emgIpcWidgetList:
                widget.setEnabled(False)
            for widget in self._emgServerWidgetList:
                widget.setEnabled(True)
            self._emgDataSource = self._emgDataSourceDict['EMG_CLIENT']
        elif (rbtnname == "rbtn_emgipc"):
            for widget in self._emgIpcWidgetList:
                widget.setEnabled(True)
            for widget in self._emgServerWidgetList:
                widget.setEnabled(False)
            self.StopCommReadThread()
            self.StopDataReadThread()
            self._emgDataSource = self._emgDataSourceDict['EMG_IPC']
            # self.PrintToEmgStatusLabel("Status: Disconnected")
        else:
            print("Neither button was chosen...")

    def PrintToEmgStatusLabel(self, msg):
        self.lbl_statusemgio.setText(msg)

    def UpdateActiveEmgList(self):
        temp = []
        i = 1
        for btn in self._emgSensors:
            if (btn.isChecked()):
                temp.append(i)
            i += 1
        self._activeEmgSensors = temp

    def InitEmgPlot(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        xAxisItem = pg.AxisItem(orientation='bottom', showValues=True)
        yAxisItem = pg.AxisItem(orientation='left', showValues=True)
        self._plotWidget = pg.GraphicsLayoutWidget()
        self._plt = self._plotWidget.addPlot(row=0,
                                             col=0,
                                             rowspan=1,
                                             colspan=1,
                                             axisItems={'left': yAxisItem,
                                                        'bottom': xAxisItem})
        data = np.array(self._emgDataQueue)
        emgSamplesPerSec = 2000
        Ts = 1.0/emgSamplesPerSec
        [rows, cols] = data.shape
        self._plt.setRange(xRange=(0,rows*Ts), yRange=(-0.002,0.002), padding=0.0)
        self._plt.show()
        self.horizontallayout_emg.addWidget(self._plotWidget)


    def InitEmgLines(self):
        lineColors = [
                      (255,   0,   0), # Red
                      (  0, 255,   0), # Green
                      (  0,   0, 255), # Blue
                      (255, 255,   0), # Yellow
                      (  0, 255, 255), # Cyan
                      (255,   0, 255), # Pink
                      (128,   0, 128), # Purple
                      (  0, 128, 128), # Blue Steel
                      ]
        self._emgLines = []
        emgNum = 1
        for lc in lineColors:
            pen = pg.mkPen(color=lc, width=3, style=QtCore.Qt.SolidLine)
            line = pg.PlotCurveItem(name="EMG{}".format(emgNum))
            line.setPen(pen)
            self._emgLines.append(line)
            emgNum += 1

    def InitEmgPlotTimer(self):
        refreshRate = 20.0
        Ts = 1.0/refreshRate
        self._plotTimer = QtCore.QTimer()
        self._plotTimer.timeout.connect(self.UpdateEmgPlot)

    def StartEmgPlot(self):
        self._plotTimer.start(0)

    def StopEmgPlot(self):
        self._plotTimer.stop()

    def UpdateEmgPlot(self):
        # get lines that are being plotted
        plotchildren =  self._plt.getViewBox().allChildren()

        # Sensor data
        data = np.array(self._emgDataQueue)
        [rows, cols] = data.shape

        #Sample Time for Time Data
        emgSamplesPerSec = 2000
        Ts = 1/emgSamplesPerSec

        # Update Sensor Data In Plot
        nSensors = 8
        for iSensor in range(1, nSensors+1):
            if iSensor in self._activeEmgSensors:
                # If sensor is active, update data and add line to plot if necessary
                self._emgLines[iSensor-1].setData(x=np.arange(start=0, stop=rows)*Ts,
                                               y=data[:,iSensor-1])
                if self._emgLines[iSensor-1] not in plotchildren:
                    self._plt.addItem(self._emgLines[iSensor-1])
            else:
                # If sensor is inactive, and it is currently being plotted, disable it
                if self._emgLines[iSensor-1] in plotchildren:
                    self._plt.removeItem(self._emgLines[iSensor-1])

        # Update Plot Ranges and Re-plot
        self._plt.update()

    def CloseSockets(self):
        #Close sockets
        self._emgCommSocket.close()
        self._emgDataSocket.close()

    def SetIPAddress(self, ip_address):
        self._ipAddressStr = ip_address

    def ConnectEmgCommPort(self):
        try:
            self._emgCommSocket.connect((self._ipAddressStr, self._emgCommPort))
            return True #return normally
        except socket.timeout:
            errmsg = "Timeout Occured During Attempt\nto Connect to Comm Port"
            self.PrintToStatusLabel(errmsg)
            return False #return with error

    def ConnectEmgDataPort(self):
        try:
            self._emgDataSocket.connect((self._ipAddressStr, self._emgDataPort))
            return True #return normally
        except socket.timeout:
            errmsg = "Timeout Occured During Attempt\nto Connect to Data Port"
            self.PrintToStatusLabel(errmsg)
            return False #return with error

    def ReadEmgCommForever(self):
        self._emgCommSocket.setblocking(False)

        bEmgResponse = ""
        emgResponse = ""
        self._emgCommThreadActive = True
        while (self._emgCommThreadActive):
            try:
                # Check for bytes available
                bytesAvailable = len(self._emgCommSocket.recv(256, socket.MSG_PEEK))
                # If bytes are available, that means the server response has arrived.
                # Get emg server response, change from byte string to string. Then
                # append it to the textedit widget
                if (bytesAvailable >= 0):
                    bEmgResponse = self._emgCommSocket.recv(256, 0)
                    emgResponse = bEmgResponse.decode()
                    self._textedit_emgserverreplywindow.append(emgResponse)
                    bEmgResponse = ""
                    emgResponse = ""
                else:
                    time.sleep(0.1)
            except BlockingIOError:
                time.sleep(0.1)
            except ConnectionResetError:
                self.PrintToStatusLabel("Status: Disconnected\nDelsys Base Reset")
                break

    def ReadEmgDataForever(self):
        self._emgDataSocket.setblocking(False)

        SZ_DATA_EMG = 64 #take data in 64 byte segments
        self._emgDataThreadActive = True
        while (self._emgDataThreadActive):
            try:
                if (len(self._emgDataSocket.recv(SZ_DATA_EMG, socket.MSG_PEEK)) >= SZ_DATA_EMG):
                    bEmgData = self._emgDataSocket.recv(SZ_DATA_EMG, 0) # get 64 bytes of data
                    emgData = np.frombuffer(bEmgData, dtype=np.single)
                    self._emgDataQueue.append(emgData)
            except BlockingIOError:
                continue
            except ConnectionResetError:
                self.PrintToStatusLabel("Status: Disconnected\nDelsys Base Reset")
                break

    def PrintToStatusLabel(self, msg):
        self._lbl_statusemgio.setText(msg)

    def SendEmgCommand(self):
        commandStr = str(self._lineedit_servercmd.text())
        self._lineedit_servercmd.setText("")
        if len(commandStr) != 0:
            commandStr += "\r\n\r\n"
            bCommandStr = str.encode(commandStr)
            self._emgCommSocket.send(bCommandStr)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
