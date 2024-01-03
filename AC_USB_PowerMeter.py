#!/usr/bin/env python3
#MIT License
#
#Copyright (c) 2021 TheHWcave
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
import tkinter as tk
import tkinter.scrolledtext as tkst
import tkinter.filedialog as tkfd
import tkinter.messagebox as tkmb
import tkinter.font as tkFont
from collections import namedtuple
from AC_COMBOX import AC_COMBOX 
from time import localtime,strftime,perf_counter_ns
import math,argparse

class AC_USB_PM_GUI():
	
	
	
	def __init__(self,port,rec_averages = False):

		# create root window and frames
		self.window = tk.Tk()
		self.window.option_add('*Font','fixed')
		
		
		# give main loop a chance to run once before running (file) dialog
		# otherwise entry fields will loose focus and appear to hang
		self.window.update_idletasks()
		
		self.window.title("TheHWcave's AC USB Powermeter")
		
		# the overall structure is a 5 rows by 3 columns grid 
		
		#         (16)    (16)     16)   = 48
		#          0       1        2
		#    0  [         port         ]
		#    1  [         rec          ]
		#    2  [Volt]   [Curr]  [Pwr] ]
		#    3  [Freq]   [Ener]  [Pf ] ]
		#    4  [Q   ]    [S]    [phi] ]
		
		


					  
		
		# port stuff in row 0
		#        (8)           (32)            (8)    = 48
		#         0              1              2
		#   0   label  eeeeeeeeeeeeeeeeeeeee  button
		#
		#
		self.portframe = tk.Frame(self.window)
		
		self.labelPort = tk.Label(self.portframe,width=8, text= 'port:')
		self.entryPort = tk.Entry(self.portframe, width=32)
		self.buttConn  = tk.Button(self.portframe,width=8,text='Connect',bd=5,command=self.DoConnect)
		self.entryPort.bind('<Return>',self.DoConnect)
		self.entryPort.insert(0,port)
		self.labelPort.grid(row=0,column=0,sticky='E')
		self.entryPort.grid(row=0,column=1,sticky='W')
		self.buttConn.grid(row=0,column=2,sticky='W') 
		self.portframe.grid(row=0,column=0,columnspan=3)
		
		
		# rec stuff in row 1
		# 
		#        (4) (4)  (8)            (24)          (8)    = 48
		#         0   1    2               3            4
		#   0   x10  REC  #recs  fffffffffffffffffff   menu
		#
		#
		self.recframe = tk.Frame(self.window)
		self.RecSpdList= ('0.5s','1s','2s','5s','10s','30s','1min','5min','10min','30min','1h')
		self.RecSpdSec = (  0.5 , 1  , 2 ,  5  , 10  , 30  ,60    ,300   ,600    ,1800   ,3600)
		self.RecSpd    = 1
		self.RecNums   = 0
		self.x10 = False
		self.RecSpdVal = tk.StringVar()
		self.RecSpdVal.set(self.RecSpdList[1])
		self.optRecSpd = tk.OptionMenu(self.recframe,self.RecSpdVal,*self.RecSpdList,command=self.DoRecSpd)

		self.buttRec   = tk.Button(self.recframe,text='Rec',bd=5,command=self.DoRec,width=3)
		self.buttx10   = tk.Button(self.recframe,text='x1', bd=5,command=self.Dox10,width=3)
		self.RecName   = ''
		self.RecData   = [[0.0,0.0,0] for x in range (9)]
		self.REC_VALUE = 0
		self.REC_SUM   = 1
		self.REC_N     = 2
		self.RecAve    = rec_averages
		self.labelRecFn= tk.Label(self.recframe,text= '{:24s}'.format(self.RecName),width=24)
		self.labelRNums= tk.Label(self.recframe,text= '',width=8)
		
		self.buttx10.grid(row=0,column=0,sticky='W')
		self.buttRec.grid(row=0,column=1,sticky='W')
		self.labelRNums.grid(row=0,column=2,sticky='E')
		self.labelRecFn.grid(row=0,column=3,sticky='W')
		self.optRecSpd.grid(row=0,column=4,sticky='W')
		
		self.recframe.grid(row=1,column=0,columnspan=3)
		
		# data frames in rows 2 & 3
		# 6 data frames, arranged as a 2 x 3 grid. The grid positon is
		# defined in the FD structure. Each data frame looks like
		# 
		#        (5)   (8)    (3)      = 16
		#         0     1      2  
		#   0   label  value unit 
		#
		#
		
		FrameData = namedtuple('FrameData',('Attr','Row','Col','Label','Fmtx1','Fmtx10','Scale','Unit','Idx'))
		self.FD	   = [FrameData(Attr='Volt'   ,Row=2,Col=0,Label='Volt',Fmtx1 ='{:7.1f}',Fmtx10 ='{:7.1f}',Scale = 1,Unit='V'  ,Idx=0),
					  FrameData(Attr='Current',Row=2,Col=1,Label='Curr',Fmtx1 ='{:7.3f}',Fmtx10 ='{:7.4f}',Scale =10,Unit='A'  ,Idx=1),
					  FrameData(Attr='Power'  ,Row=2,Col=2,Label='Pwr ',Fmtx1 ='{:7.1f}',Fmtx10 ='{:7.2f}',Scale =10,Unit='W'  ,Idx=2),
					  FrameData(Attr='Pf'     ,Row=3,Col=2,Label='Pf  ',Fmtx1 ='{:7.2f}',Fmtx10 ='{:7.2f}',Scale = 1,Unit=' '  ,Idx=3),
					  FrameData(Attr='Freq'   ,Row=3,Col=0,Label='Freq',Fmtx1 ='{:7.1f}',Fmtx10 ='{:7.1f}',Scale = 1,Unit='Hz' ,Idx=4),
					  FrameData(Attr='Energy' ,Row=3,Col=1,Label='Ener',Fmtx1 ='{:7.0f}',Fmtx10 ='{:7.1f}',Scale =10,Unit='Wh' ,Idx=5),
					  FrameData(Attr='Q-pwr'  ,Row=4,Col=0,Label='Qpwr',Fmtx1 ='{:7.3f}',Fmtx10 ='{:7.4f}',Scale =10,Unit='var',Idx=6),
					  FrameData(Attr='S-pwr'  ,Row=4,Col=1,Label='Spwr',Fmtx1 ='{:7.3f}',Fmtx10 ='{:7.4f}',Scale =10,Unit='VA' ,Idx=7),
					  FrameData(Attr='Phi'    ,Row=4,Col=2,Label='Phi ',Fmtx1 ='{:4.1f}',Fmtx10 ='{:4.1f}',Scale = 1,Unit='º'  ,Idx=8)]
	
		
		self.dataframe = []
		self.datalabel = []
		self.datavalue = []
		self.dataunit  = []
		for fd in self.FD:
			df = tk.Frame(self.window,borderwidth=4,relief='groove')
			dl = tk.Label(df,width=5,text=fd.Label)
			dl.grid(row=0,column=0,sticky='W')
			
		
			dv = tk.Label(df,width=8,text='-------')
			dv.grid(row=0,column=1,sticky='E')
			
			du = tk.Label(df,width=3,text=fd.Unit)
			du.grid(row=0,column=2,sticky='W')
			
			df.grid(row=fd.Row,column=fd.Col,sticky='W')
			
			
			self.dataframe.append(df)
			self.datalabel.append(dl)
			self.datavalue.append(dv)
			self.dataunit.append(du)
	
	
		# remaining intitalisation and start of main loop
		
		self.Module = None
		self.entryPort.focus_set()
		self.PollCount = 0
		self.ProgStart = perf_counter_ns()
		self.PollModule()
		tk.mainloop()
		if self.RecName != '':
			self.f.close()
	
	def DoConnect(self,event=None):
		"""
			given a port name, the function tries to connect.  
			As a (crude) test if we connected to a PZEM004T it tries
			to read a data record. 
			
			Note that once it connects successfully subsequent connects 
			only reset the energy data 
			
		"""
		port = self.entryPort.get()
		if self.Module == None:
			
			try:
				self.Module = AC_COMBOX(port)
				self.pd = self.Module.Poll() # try a read 
				if self.pd == None:
					self.Module = None
					tkmb.showerror("device error","device at "+port+" does not respond")
				else:
					self.buttConn.config(relief='sunken')
			except: 
				tkmb.showerror("port error","can't open "+port)
				self.Module = None
				self.buttConn.config(relief='raised')
				
		else:
			self.Module.ResetEnergy()
	
	def DoRecSpd(self,event=None):
		"""
			changes the recording speed
		"""
		idx = self.RecSpdList.index(self.RecSpdVal.get())
		self.RecSpd = self.RecSpdSec[idx]
		
	def Dox10(self,event=None):
		"""
			changes the x1 / x10 mode. 
		"""
		self.x10 = not self.x10
		if self.x10:
			self.buttx10.config(text='x10',relief='sunken')
		else:
			self.buttx10.config(text='x1',relief='raised')
	

	def DoRec(self,event=None):
		"""
			starts or stops the recording and shows the 
			recording filename while recording is on. 
		"""
		if self.Module != None:
			if self.RecName == '':
				self.RecName = 'REC_'+strftime('%Y%m%d%H%M%S',localtime())+'.csv'
				try:
					self.f = open(self.RecName,'w',encoding='utf-8')
					self.f.write('Time[S],')
					for fd in self.FD: self.f.write(fd.Label+'['+fd.Unit+'],')
					self.f.write('xmode\n')
					for RD in self.RecData:
						RD[self.REC_SUM] = 0.0
						RD[self.REC_N] = 0
						
					self.buttRec.config(relief='sunken')
					self.PollCount = 0
					self.RecNums = 0
					self.labelRNums.config(text= '#{:7n}'.format(self.RecNums))
				except:
					tkmb.showerror("rec error","can't create "+self.RecName)
					self.RecName = ''
					self.labelRNums.config(text= '')
			else:
				self.f.close()
				self.buttRec.config(relief='raised')
				self.RecName = ''
				self.labelRNums.config(text= '')
			self.labelRecFn.config(text= '{:24s}'.format(self.RecName))
		
			
	def PollModule(self,event=None):
		"""
			polls the module every 0.5s. The time is adjusted to maintain accuracy
		"""
		if self.Module != None:
			
			self.PollCount += 0.5
			err = False
			try:
				self.pd = self.Module.Poll()
			except:
				err = True
			if err or self.pd == None:
				tkmb.showerror("comms error","lost connection ")
				self.window.quit()
			else:
				
				
				# calculate some useful values out of the measured data
				phi_rad = math.acos(self.pd.Pf)
				phi_deg = math.degrees(phi_rad)
				spwr = self.pd.Volt * self.pd.Current
				qpwr =spwr * math.sin(phi_rad)
				
				
				for i,fd in enumerate(self.FD):
					if i < 6:
						# values directly measured
						if self.x10:
							val = getattr(self.pd,fd.Attr) / fd.Scale
							s   = fd.Fmtx10.format(val)
							
						else:
							val = getattr(self.pd,fd.Attr)
							s   = fd.Fmtx1.format(val)
					else:
						# calculated values
						if fd.Attr == 'Phi':
							val =phi_deg
							s=fd.Fmtx1.format(val)
						elif fd.Attr == 'Q-pwr':
							val = qpwr
							if self.x10:
								val = val/fd.Scale
								s = fd.Fmtx10.format(val)
							else:
								s=fd.Fmtx1.format(val)
						elif fd.Attr == 'S-pwr':
							val = spwr
							if self.x10:
								val = val/fd.Scale
								s = fd.Fmtx10.format(val)
							else:
								s=fd.Fmtx1.format(val)
						else:
							s='???' # should never happen
					if self.RecName != '':
						self.RecData[fd.Idx][self.REC_VALUE] = val
						self.RecData[fd.Idx][self.REC_N] += 1
						self.RecData[fd.Idx][self.REC_SUM] += val
					
					self.datavalue[i].configure(text=s)
					
				
				if self.RecName != '':
					# for debug only
					# rs = '' 
					# for RD in self.RecData:
						# rs += '{:9.5f}'.format(RD[self.REC_VALUE]) + ','
					# s = '{:5n},{:s}{:1n}'.format(0,rs,0)
					# self.f.write(s+'\n')
					if self.PollCount % self.RecSpd == 0:
						rs = '' # for building a recording string 
						for RD in self.RecData:
							if self.RecAve:
								rs += '{:9.5f}'.format(RD[self.REC_SUM] / RD[self.REC_N]) + ','
								RD[self.REC_SUM] = 0.0
								RD[self.REC_N] = 0
							else:
								rs += '{:9.5f}'.format(RD[self.REC_VALUE]) + ','
						s = '{:5n},{:s}{:1n}'.format(self.PollCount,rs,10 if self.x10 else 1)
						try:
							self.f.write(s+'\n')
							self.RecNums = self.RecNums +1
							self.labelRNums.config(text= '#{:7n}'.format(self.RecNums))
						except:
							tkmb.showerror("rec error","can't write to "+self.RecName)
							self.RecName = ''
							self.labelRNums.config(text= '')
							self.labelRecFn.config(text= '{:24s}'.format(self.RecName))
							self.buttRec.config(relief='raised')

							
		elapsed = (perf_counter_ns() - self.ProgStart)//1000000  # time in ms since start
		time2sleep= 500 - (elapsed % 500)
		self.window.after(time2sleep, self.PollModule)
			

if __name__ == "__main__":
	
	parser = argparse.ArgumentParser()

	parser.add_argument('--port',help='port ',
					action='store',type=str,default='')
	parser.add_argument('--no_average',help='disables recording of averages',action="store_true")
					
	
	arg = parser.parse_args()
	
	gui = AC_USB_PM_GUI(arg.port,not arg.no_average)

