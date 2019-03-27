#!/usr/bin/python3

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QButtonGroup
from PyQt5.QtCore import QObject

import sys
import pyqtgraph as pg
import socket
import threading
import time
import numpy as np
from collections import deque

class TwoDimensionPlot:

    def __init__(self, widget_list):
        for i in widget_list:
            print(i, widget_list[i])

class EmgClient:

    # Class Data
    _lineedit_ipaddress = None
    _lbl_statusemgio = None
    _textedit_emgserverreplywindow = None
    _lineedit_servercmd = None

    _ipAddressStr = None
    _emgCommPort = 50040
    _emgDataPort = 50041
    _emgCommSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _emgDataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _socketTimeout = 1.0 #seconds

    _emgDataThreadActive = False
    _emgCommThreadActive = False

    _emgDataQueue = deque(maxlen=5000)


    def __init__(self, lineedit_ipaddress, lbl_statusemgio, textedit_serverreplywindow, lineedit_servercmd):
        # Set a few QWidgets as class data for interaction with interface
        self._lineedit_ipaddress = lineedit_ipaddress
        self._lbl_statusemgio = lbl_statusemgio
        self._textedit_emgserverreplywindow = textedit_serverreplywindow
        self._lineedit_servercmd = lineedit_servercmd
        textedit_serverreplywindow

        # Set socket timeouts
        self._emgCommSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._emgDataSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._emgCommSocket.settimeout(self._socketTimeout)
        self._emgDataSocket.settimeout(self._socketTimeout)

        # Fill emg data queue with zeros
        temp = np.zeros(16)
        for i in range(0,5000):
            self._emgDataQueue.append(temp)

    def __del__(self):
        self.CloseSockets()

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




class MainWindow(QMainWindow):

    # Class Data
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


    def __init__(self):
        super(MainWindow, self).__init__()
        self.setGeometry(0, 0, 1000, 600)
        uic.loadUi('visualizer_app.ui', self)
        self.show()
        self.InitializeEmgTab()
        self.InitializeTwoDimPlotTab()

    def InitializeTwoDimPlotTab(self):
        widget_list = {
                       self.btn_selectshmfile.objectName(): self.btn_selectshmfile,
                       self.lbl_shmfile.objectName(): self.lbl_shmfile,
                       self.btn_connect2ddata.objectName(): self.btn_connect2ddata,
                       self.lbl_statusshmstream.objectName(): self.lbl_statusshmstream,
                       self.btn_selectfilterfile.objectName(): self.btn_selectfilterfile,
                       self.lbl_filterfile.objectName(): self.lbl_filterfile,
                       self.rbtn_nofilter.objectName(): self.rbtn_nofilter,
                       self.rbtn_defaultfilter.objectName(): self.rbtn_defaultfilter,
                       self.rbtn_customfilter.objectName(): self.rbtn_customfilter,
                       self.lbl_buttercoefficients.objectName(): self.lbl_buttercoefficients,
                       self.btn_2dplotstart.objectName(): self.btn_2dplotstart,
                       self.btn_2dplotstop.objectName(): self.btn_2dplotstop
                       }
        TwoDimensionPlot(widget_list)

    def InitializeEmgTab(self):
        self._emgClient = EmgClient(self.lineedit_ipaddress,
                                    self.lbl_statusemgio,
                                    self.textedit_serverreplywindow,
                                    self.lineedit_servercmd)
        self.InitEmgPlot()
        self.InitializeEmgButtons()
        self.InitEmgLines()
        self.InitEmgPlotTimer()

    def ConnectDataIO(self):
        if (self._emgDataSource == self._emgDataSourceDict['EMG_CLIENT']):
            ip_address = str(self.lineedit_ipaddress.text())
            if (ip_address != ""):
                self.lineedit_ipaddress.setText("")
                self._emgClient.SetIPAddress(ip_address)
                emgCommPortConnected = self._emgClient.ConnectEmgCommPort()
                emgDataPortConnected = self._emgClient.ConnectEmgDataPort()

                # Start Threads for Reading EMG Communication and Data ports continuously
                if emgCommPortConnected:
                    self.StartCommReadThread()
                if emgDataPortConnected:
                    self.StartDataReadThread()
                msg = "Status: Connected\nIP: {}".format(self._emgClient._ipAddressStr)
            else: #lineedit_ipaddress empty
                msg = "Input An IP Address"
            self._emgClient.PrintToStatusLabel(msg)
        elif (self._emgDataSource == self._emgDataSourceDict['EMG_IPC']):
            pass

    def StartCommReadThread(self):
        # Stop EMG Comm Thread if its open
        self.StopCommReadThread()

        # Start EMG Comm Thread
        t = threading.Thread(target=self._emgClient.ReadEmgCommForever, name=self._threadname_emgcommrecv, daemon=True)
        t.start()

    def StopCommReadThread(self):
        activeThreads = threading.enumerate() # returns list of active threads

        for t in activeThreads:
            if (t.name == self._threadname_emgcommrecv):
                self._emgClient._emgCommThreadActive = False # this will force an end of the method the thread is running
                break

    def StartDataReadThread(self):
        # Stop EMG Data Thread if its open
        self.StopDataReadThread()

        # Start EMG Data Thread
        t = threading.Thread(target=self._emgClient.ReadEmgDataForever, name=self._threadname_emgdatarecv, daemon=True)
        t.start()

    def StopDataReadThread(self):
        activeThreads = threading.enumerate() # returns list of active threads

        for t in activeThreads:
            if (t.name == self._threadname_emgdatarecv):
                self._emgClient._emgDataThreadActive = False # this will force an end of the method the thread is running
                break

    def InitializeEmgButtons(self):
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
        self.btn_sendservercmd.clicked.connect(self._emgClient.SendEmgCommand)
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
        data = np.array(self._emgClient._emgDataQueue)
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
        data = np.array(self._emgClient._emgDataQueue)
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



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
