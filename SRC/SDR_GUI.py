# -*- coding: utf-8 -*-
"""
Created on Sun May  1 16:45:51 2022

@author: KOelschlaeger
"""

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import messagebox as msg
from threading import Thread
from MySDR.MySDR import * # was SDR but apparently that is a namespace collision!?!


Modes = ('AM', 'LSB', 'USB', 'CW')
Target = ('Line', 'Speaker', 'Both')
AGCModes = ('Slow', 'Medium', 'Fast')

class FormattedDouble(tk.DoubleVar):
    def to_string(self):
        return "{:.0}".format(self.get())
    
    def __str__(self):
        return "{:.0}".format(self.get())

class SDR_GUI():    # Was GUI but apparently that is a namespace collision!?!
    # Initializer
    def __init__(self):
        # Initialize internal variables
        self.VFO = 0.5
        self.Mode = 0
        self.Filter = 3000
        self.ModeSelected = 0   # AM
        self.AGC = 1            # 'Medium'
        self.Linked = 0
        
        # Create SDR instance
        #self.sdr = MySDR('COM3')
        self.sdr = MySDR('/dev/tty.usbserial-AB0N3GLA')

        # Create window instance
        self.win = tk.Tk()
        
        # Set window title
        self.win.title('RX320')
        
        # Enable/Disable resizing in X, Y directions
        self.win.resizable(True, True)
        
        # Create all the GUI Widgets
        self.CreateWidgets()
        
    def Button_OnClick(self):
        self.VFO = self.VFOFreqInput.get()
        
    # Mode Radio Button
    def RadioButtonMode_SelectedIndexChanged(self):
        self.Mode = self.ModeVar.get()
        self.ModeText.set(Modes[self.Mode])
        self.sdr.SetMode(Modes[self.Mode])
        
    def RadioButtonAGC_SelectedIndexChanged(self):
        self.AGC = self.AGCMode.get()
        self.sdr.SetAGC(AGCModes[self.AGC])
        self.AGCModeText.set(AGCModes[self.AGC])
        self.AGCMode.set(self.AGC)
        
    def _quit(self):
        # Check if serial port still in use
        if self.sdr.Connected:
            self._disconnect()
        self.win.quit()
        self.win.destroy()
        sys.exit()
    
    def _about(self):
        # MessageBox creates an extra parent window that we need to suppress
        root = tk.Tk()
        root.withdraw()
        msg.showinfo('About RX320', 'A GUI for the Ten-Tec RX320\nDeveloped by Karl Oelschlaeger\nCopyright 2022, Creative Commons 2.0')
        
    def _connect(self):
        # SerialThread is linked to sdr.Connect() and will be started as a daemon
        self.MySerialThread = Thread(target=self.sdr.Connect)
        self.MySerialThread.start()
        
    def _disconnect(self):
        self.sdr.Disconnect()
        
    def _updateProgressBar(self):
        self.ProgressBar["value"] = self.sdr.sdr.RSI
        sleep(0.250)
        
    def ButtonMute_OnClick(self):
        self.SpeakerLevel.set(-96)
        self.LineLevel.set(-96)
        self.sdr.SetAttenuation(63, 'Both')
        
    def CheckBoxLink_OnCheckChange(self):
        self.Linked = self.LevelLink.get()
        if self.Linked:
            Min = min(self.SpeakerLevel.get(), self.LineLevel.get())
            self.SpeakerLevel.set(Min)
            self.LineLevel.set(Min)
            
    def SliderLineLevel_OnValueChange(self, value):
        if self.Linked:
            self.SpeakerLevel.set(value)
        
    def SliderSpeakerLevel_OnValueChange(self, value):
        if self.Linked:
            self.LineLevel.set(value)
        
    def CreateWidgets(self):
        # TK binding variables
        self.ModeText = tk.StringVar()
        self.ModeText.set(Modes[self.Mode])
        self.ModeVar = tk.IntVar()
        self.ModeVar.set(self.Mode)             # Defaults to AM
        self.FilterFreq = tk.IntVar()
        self.FilterFreq.set(8000)       # Defaults to 8 kHz filter
        self.VFOFreqInput = tk.DoubleVar()
        self.VFOFreqInput.set(0.5)         # Defaults to 500 kHz VFO
        self.AGCModeText = tk.StringVar()
        self.AGCModeText.set(AGCModes[self.AGC])
        self.AGCMode = tk.IntVar()
        self.AGCMode.set(self.AGC)
        self.LevelLink = tk.BooleanVar()
        self.LevelLink.set(0)
        self.LineLevel = tk.IntVar()
        self.LineLevel.set(-96)
        self.SpeakerLevel = tk.IntVar()
        self.SpeakerLevel.set(-96)
        
        # Status Frame
        StatusFrame = ttk.LabelFrame(self.win, text='Status')
        StatusFrame.grid(column=0, row=0, 
                         columnspan=5, rowspan=2, 
                         padx=5, pady=5,
                         sticky=tk.NW)
        
        ttk.Label(StatusFrame, 
                  textvariable=self.ModeText,
                  width=8,
                  anchor=tk.W
                  ).grid(column=0, row=0)
        ttk.Label(StatusFrame, 
                  textvariable=self.AGCModeText, 
                  width=8, anchor=tk.W
                  ).grid(column=0, row=1)
        ttk.Label(StatusFrame, 
                  textvariable=self.VFOFreqInput, 
                  font=('Helvetica Bold', 18),
                  width=8,
                  anchor=tk.E
                  ).grid(column=1, row=0, columnspan=3, rowspan=2)
        ttk.Label(StatusFrame, 
                  textvariable=self.FilterFreq,
                  width=6,
                  anchor=tk.E
                  ).grid(column=4, row=0)
        
        # Static Labels
        # FreqInputLabel = ttk.Label(self.win, text='Center Frequency:')
        # FreqInputLabel.grid(column=0, row=0)
        
        # VFO and Filter
        VFOFrame = ttk.LabelFrame(self.win, text='VFO')
        VFOFrame.grid(column=2, row=2, columnspan=2, rowspan=2, padx=5, pady=5)
        
        # VFO
        FreqEntered = ttk.Entry(VFOFrame, width=12, textvariable=self.VFOFreqInput)
        FreqEntered.grid(column=2, row=2)
        FreqEntered.focus()
        action = ttk.Button(VFOFrame, text='Set', command=self.Button_OnClick)
        action.grid(column=3, row = 2)
        
        # Filter Selection
        FilterFreqSelected = ttk.Combobox(VFOFrame, 
                                          width=16, 
                                          textvariable=self.FilterFreq, 
                                          state='readonly')
        FilterFreqSelected['values'] = ( 300,  330,  375,  450,  525,  600,
                                         675,  750,  900, 1050, 1200, 1350,
                                        1500, 1650, 1800, 1950, 2100, 2250,
                                        2400, 2550, 2700, 2850, 3000, 3300,
                                        3600, 3900, 4200, 4800, 5100, 5400,
                                        5700, 6000, 8000)
        FilterFreqSelected.grid(column=2, row=3, columnspan=2, sticky=tk.W)
                
        # Level Controls
        LevelFrame = ttk.LabelFrame(self.win, text='Levels')
        LevelFrame.grid(column=0, row=2, 
                        rowspan=6, columnspan=2, 
                        padx=5, pady=5, 
                        sticky=tk.N)
        LineSlider = ttk.Scale(LevelFrame, 
                               from_=0, to=-96, 
                               orient='vertical', 
                               variable=self.LineLevel, 
                               command=self.SliderLineLevel_OnValueChange)
        LineSlider.grid(column=0, row=3, rowspan=3)
        SpeakerSlider = ttk.Scale(LevelFrame, 
                                  from_=0, to=-96, 
                                  orient='vertical', 
                                  variable=self.SpeakerLevel, 
                                  command=self.SliderSpeakerLevel_OnValueChange)
        SpeakerSlider.grid(column=1, row=3, rowspan=3)
        LineLabelUpper = ttk.Label(LevelFrame, text='0 dB')
        LineLabelUpper.grid(column=0, row=2)
        LineLabelLower = ttk.Label(LevelFrame, text='-96 dB')
        LineLabelLower.grid(column=0, row=6)
        SpeakerLabelUpper = ttk.Label(LevelFrame, text='0 dB')
        SpeakerLabelUpper.grid(column=1, row=2)
        SpeakerLabelLower = ttk.Label(LevelFrame, text='-96 dB')
        SpeakerLabelLower.grid(column=1, row=6)
        CheckBoxLink = ttk.Checkbutton(LevelFrame, 
                                       text='Link', 
                                       variable=self.LevelLink, 
                                       command=self.CheckBoxLink_OnCheckChange)
        CheckBoxLink.grid(column=0, row=7, columnspan=2)
        ButtonMute = ttk.Button(LevelFrame, text='Mute', command=self.ButtonMute_OnClick)
        ButtonMute.grid(column=0, row=8, columnspan=2)
        
        # DeMod Mode
        ModeFrame = ttk.LabelFrame(self.win, text='Mode')
        ModeFrame.grid(column=2, row=4, 
                       rowspan=4, 
                       padx=5, pady=5, 
                       sticky=tk.NW)
        for index in range(len(Modes)):    
            RadioButton = tk.Radiobutton(ModeFrame, text=Modes[index], variable=self.ModeVar, value=index, command=self.RadioButtonMode_SelectedIndexChanged)
            RadioButton.grid(column=2, row=index+4, sticky=tk.W)
        
        # AGC Mode
        AGCFrame = ttk.LabelFrame(self.win, text='AGC')
        AGCFrame.grid(column=3, row=4, 
                      rowspan=3, 
                      padx=5, pady=5, 
                      sticky=tk.NE)
        for index in range(len(AGCModes)):
            RadioButton = tk.Radiobutton(AGCFrame, text=AGCModes[index], variable=self.AGCMode, value=index, command=self.RadioButtonAGC_SelectedIndexChanged)
            RadioButton.grid(column=3, row=index+4, sticky=tk.W)
        
        # Amplitude Display
        AmpFrame = ttk.LabelFrame(self.win, text='Amp')
        AmpFrame.grid(column=4, row=2, 
                      rowspan=6, 
                      padx=5, pady=5,
                      sticky=tk.NW)
        self.ProgressBar = ttk.Progressbar(AmpFrame, orient='vertical', length=80, mode='determinate')
        self.ProgressBar.grid(column=4, row=2, padx=5)
        
        # Main Menu
        MenuBar = Menu(self.win)
        self.win.config(menu=MenuBar)
        
        FileMenu = Menu(MenuBar, tearoff=0)
        FileMenu.add_command(label='Connect', command=self._connect)
        FileMenu.add_command(label='Disconnect', command=self._disconnect)
        FileMenu.add_command(label='Preferences')
        FileMenu.add_separator()
        FileMenu.add_command(label='Exit', command=self._quit)
        
        HelpMenu = Menu(MenuBar, tearoff=0)
        HelpMenu.add_command(label='About', command=self._about)
        
        MenuBar.add_cascade(label='File', menu=FileMenu)
        MenuBar.add_cascade(label='Help', menu=HelpMenu)

if __name__ == "__main__":
    # Start GUI
    # gui = GUI_Playground()
    gui = SDR_GUI()
    gui.win.mainloop()
        