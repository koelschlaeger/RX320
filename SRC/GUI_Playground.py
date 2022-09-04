# -*- coding: utf-8 -*-
"""
Created on Tue May  3 18:07:28 2022

@author: KOelschlaeger
"""

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import messagebox as msg
from threading import Thread
from time import sleep

Modes = ('AM', 'LSB', 'USB', 'CW')
Target = ('Line', 'Speaker', 'Both')

class Demo():
    def demoMethod(self):
        print('Demo Thread Started...\r')
        while self.LoopEnabled:
            print('Demo Thread Running...\r')
            sleep(10)
        
    def stopLoop(self):
        self.LoopEnabled = False
        
    def startLoop(self):
        self.LoopEnabled = True

class GUI_Playground():
    def __init__(self):
        # Create window instance
        self.win = tk.Tk()
        
        # Set window title
        self.win.title('RX320')
        
        # Enable/Disable resizing in X, Y directions
        self.win.resizable(True, True)
        
        self.demo = Demo()
        
        # Create all the GUI Widgets
        self._createWidgets()

    def _quit(self):
        self.win.quit()
        self.win.destroy()
        sys.exit()
    
    def _about(self):
        # MessageBox creates an extra parent window that we need to suppress
        root = tk.Tk()
        root.withdraw()
        msg.showinfo('About RX320', 'A GUI for the Ten-Tec RX320\nDeveloped by Karl Oelschlaeger\nCopyright 2022, Creative Commons 2.0')
        
    def _connect(self):
        self.run_thread = Thread(target=self.demo.demoMethod)
        self.run_thread.start()
        print(self.run_thread)
        
    def Button_OnClick(self):
        self.VFO = self.VFOFreqInput.get()
        
    # Mode Radio Button
    def RadioButtonMode_SelectedIndexChanged(self):
        self.ModeSelected = self.ModeVar.get()
        self.sdr.SetMode(Modes[self.ModeSelected])
        
    def Button_Start(self):
        self.demo.startLoop()
        
    def Button_Stop(self):
        self.demo.stopLoop()
    
    def _createWidgets(self):
        # TK binding variables
        self.ModeVar = tk.IntVar()
        self.ModeVar.set(0)             # Defaults to AM
        self.FilterFreq = tk.IntVar()
        self.FilterFreq.set(8000)       # Defaults to 8 kHz filter
        self.VFOFreqInput = tk.DoubleVar()
        self.VFOFreqInput.set(0.5)         # Defaults to 500 kHz VFO
        
        # Static Labels
        FreqInputLabel = ttk.Label(self.win, text='Center Frequency:')
        FreqInputLabel.grid(column=0, row=0)
        
        FreqEnteredLabel = ttk.Label(self.win, textvariable=self.VFOFreqInput)
        FreqEnteredLabel.grid(column=0, row=2)
        
        
        FreqEntered = ttk.Entry(self.win, width=16, textvariable=self.VFOFreqInput)
        FreqEntered.grid(column=0, row=1)
        FreqEntered.focus()
        
        
        FilterFreqSelected = ttk.Combobox(self.win, width=16, textvariable=self.FilterFreq, state='readonly')
        FilterFreqSelected['values'] = ( 300,  330,  375,  450,  525,  600,
                                         675,  750,  900, 1050, 1200, 1350,
                                        1500, 1650, 1800, 1950, 2100, 2250,
                                        2400, 2550, 2700, 2850, 3000, 3300,
                                        3600, 3900, 4200, 4800, 5100, 5400,
                                        5700, 6000, 8000)
        FilterFreqSelected.grid(column=0, row=3)
                    
        action = ttk.Button(self.win, text='Click Me!', command=self.Button_OnClick)
        action.grid(column=1, row = 1)
        
        for index in range(len(Modes)):    
            RadioButton = tk.Radiobutton(self.win, text=Modes[index], variable=self.ModeVar, value=index, command=self.RadioButtonMode_SelectedIndexChanged)
            RadioButton.grid(column=2, row=index, sticky=tk.W)
        
        ButtonStart = ttk.Button(self.win, text='Start', command=self.Button_Start)
        ButtonStart.grid(column=0, row=4)
        ButtonStop = ttk.Button(self.win, text='Stop', command=self.Button_Stop)
        ButtonStop.grid(column=1, row=4)
        
        # Main Menu
        MenuBar = Menu(self.win)
        self.win.config(menu=MenuBar)
        
        FileMenu = Menu(MenuBar, tearoff=0)
        FileMenu.add_command(label='Connect', command=self._connect)
        FileMenu.add_command(label='Disconnect')
        FileMenu.add_command(label='Preferences')
        FileMenu.add_separator()
        FileMenu.add_command(label='Exit', command=self._quit)
        
        HelpMenu = Menu(MenuBar, tearoff=0)
        HelpMenu.add_command(label='About', command=self._about)
        
        MenuBar.add_cascade(label='File', menu=FileMenu)
        MenuBar.add_cascade(label='Help', menu=HelpMenu)
        
if __name__ == "__main__":
    # Start GUI
    gui = GUI_Playground()
    gui.win.mainloop()