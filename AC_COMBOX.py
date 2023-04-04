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

import serial
import struct
import argparse
from collections import namedtuple
from time import sleep,time,localtime,strftime,perf_counter

parser = argparse.ArgumentParser()
DEFPORT = '/dev/accom_0'
DEFADDR = 0x01

parser.add_argument('--port','-p',help='port (default ='+DEFPORT,
					dest='port_dev',action='store',type=str,default=DEFPORT)
parser.add_argument('--address', '-s', help='port (default 0x01 to 0xF7)',
                    dest='slave_addr', action='store', type=bytes, default=DEFADDR)
parser.add_argument('--out','-o',help='output filename (default=ACCOM_<timestamp>.csv)',
					dest='out_name',action='store',type=str,default='!')
parser.add_argument('--time','-t',help='interval time in seconds between measurements (def=1.0)',
					dest='int_time',action='store',type=float,default=1.0)

					
parser.add_argument('--reset','-r',help='reset energy ',
					dest='reset',action='store_true')
parser.add_argument('--alarm','-a',help='power alarm threshold [W] ',
					dest='alarm',action='store',type=int,default=23000)
					
parser.add_argument('--debug','-d',help='debug level 0.. (def=1)',
					dest='debug',action='store',type=int,default=0)


class AC_COMBOX:

	__ACM  = None		# serial connection to the AC com box
	# defualt address of the AC com box
    __GENADD = 0x00		# general slave address for calibration or getting slave address
    __CALADD = 0xF8

	__FC_R_HOLD = 3		# function code: Read Hold Regs
	__FC_R_INP  = 4		# function code: Read Input Regs
	__FC_W_SING = 6		# function code: Write Single Reg
	
	__FC_U_CAL 	= 0x41	# function code (user defined): Calibration (uses __CALADD address 0xF8)
	__FC_U_RESET= 0x42	# function code (user defined): Reset Energy
	
	
	__REG_U		= 0x00	# 16bit volts in 0.1V resolution
	__REG_IL  	= 0x01	# current lower 16bit, resolution 1 mA
	__REG_IH	= 0x02	# current higher 16bit, resolution 1 mA
	__REG_PL  	= 0x03	# power lower 16bit, resolution 1 mW
	__REG_PH	= 0x04	# power higher 16bit, resolution 1 mW
	__REG_EL  	= 0x05	# energy lower 16bit, resolution 1 Wh
	__REG_EH	= 0x06	# energy higher 16bit, resolution 1 Wh
	__REG_F		= 0x07	# 16bit frequency, resolution 0.1Hz
	__REG_PF	= 0x08	# 16bit power factor, resolution 0.01
	__REG_ALM	= 0x09	# 16bit alarm status, FFFF = alarm, 0 = no alarm
	
	
	__REG_TH	= 0x01	# alarm threshold 
	__REG_ADDR	= 0x02	# address
	
	
	#
	# 	The class keeps copies of the actual values in the AC module here
	#
	__volt 		= 0.0	# in V
	__current	= 0.0	# in A
	__power		= 0.0	# in W
	__energy	= 0.0	# in Wh
	__freq		= 0.0	# in Hz
	__pf		= 0.0	
	__alarm		= 0
	__thresh	= 0.0	# in W
	__addr		= 0
	
	
	PollData = namedtuple('PollData',['Volt','Current','Power',
									  'Energy','Freq','Pf','Alarm'])
									  
									  
	
	def __dump(self,prompt,buf):
		"""
			prints a hex dump of the buffer on the terminal
		"""
		print(prompt,end='')
		for b in buf:
			print('{:02x} '.format(b),end='')
		print()

	def __CRC16(self,buf):
		""" 
			calculates and returns the CRC16 checksum for all message bytes 
			excluding the two checksum bytes 
		"""
		crc = 0xffff
		for b in buf[:-2]: # exclude the checksum space
			crc = crc ^ b
			for n in range(0,8):
				if (crc & 0x0001) != 0:
					crc = crc >> 1
					crc = crc ^ 0xa001
				else:
					crc = crc >> 1
		return crc.to_bytes(2,'little')
	
	def __cmd_read_regs(self,slave,fc,regstart,regnum):
		"""
			implements function code 0x03 or 0x04: 
			slave	: slave address
			regstart: address of first register
			regnum  : number of registers to read
			
			The expected response for this message varies with regnum. 
			For a regnum value of 5 we expect 15 bytes back
		"""
		res = None
		if (fc == self.__FC_R_HOLD) or (fc == self.__FC_R_INP):
			msg = bytearray(8)
			msg[0] = slave
			msg[1] = fc
			msg[2:4] = regstart.to_bytes(2,byteorder='big')
			msg[4:6] = regnum.to_bytes(2,byteorder='big')
			msg[6:8] = self.__CRC16(msg)
			self.__ACM.write(msg)
			res = self.__read_response(5+2*regnum)
		else:
			raise ValueError
		return res
	
	def __cmd_write_reg(self,slave,reg,data):
		"""
			implements function code 0x06: write single register
			slave	: slave address
			reg     : address of register
			data    : data to write 
			
			The expected response for this message is always 8 bytes long
		"""
		msg = bytearray(8)
		msg[0] = slave
		msg[1] = self.__FC_W_SING
		msg[2:4] = reg.to_bytes(2,byteorder='big')
		msg[4:6] = data.to_bytes(2,byteorder='big')
		msg[6:8] = self.__CRC16(msg)
		self.__ACM.write(msg)
		res = self.__read_response(8)
		return res
	
	def __cmd_userfunc(self,slave,fc):
		"""
			implements a user defined function code 
			slave	: slave address
			fc 	    : function code
			
			
			The expected response for this message is always 4 bytes long
		"""
		msg = bytearray(4)
		if fc == self.__FC_U_CAL:
			msg[0] = 0xf8
		else:
			msg[0] = slave
		msg[1] = fc
		msg[2:4] = self.__CRC16(msg)
		
		self.__ACM.write(msg)
		res = self.__read_response(4)
		return res
	
	def __read_response(self,expected_len):
		"""
			reads and processes the responses received from the module
			It does noy rely on "silent" periods to detect message ends 
			and instead needs the expected message length. 
			It verifies that the checksum is correct, but the 
			further interpretation is done "cheaply" and
			really only targets the messages we are expecting to see, 
			namely:
				- response to read_regs  for 10 registers starting at REG_U
				-
			
		"""
		buf = bytearray(128)
		buflen = 0
		raw = bytearray
		res = False
		tries = 50
		while (tries > 0):
			raw = self.__ACM.read(32)
			if len(raw) > 0:
				# got something .. append in to the buffer
				buf[buflen:buflen+len(raw)] = raw 
				buflen = buflen + len(raw)
				if buflen >= expected_len:
					break
			else:
				tries = tries - 1
		if tries == 0:
			print('timeout')
		else:
			#self.__dump('msg:',buf[:buflen])
			data = buf[:buflen]
			if buflen > 3:
				if data[-2:] == self.__CRC16(data):
					if data[1:3] == b'\x04\x14': 
						# Expected response for read_regs of 10 registers starting with REG_U
						msg = struct.unpack('>3B11H',data)
						self.__volt 	= float(msg[3+self.__REG_U])*0.1
						self.__current 	= float((0x10000*msg[3+self.__REG_IH]+msg[3+self.__REG_IL]))*0.001
						self.__power	= float((0x10000*msg[3+self.__REG_PH]+msg[3+self.__REG_PL]))*0.1
						self.__energy	= float((0x10000*msg[3+self.__REG_EH]+msg[3+self.__REG_EL]))
						self.__freq		= float(msg[3+self.__REG_F])*0.1
						self.__pf		= float(msg[3+self.__REG_PF])*0.01
						self.__alarm	= 1 if msg[3+self.__REG_ALM] == 0xffff else 0
						res = True
					elif data[1:3] == b'\x03\x04': 
						# Expected response for read_regs of 2 registers starting with REG_TH
						msg = struct.unpack('>3B3H',data)
						self.__thresh	= float(msg[3+0])
						self.__addr		= msg[3+1]
						res = True
					elif data[1] == self.__FC_W_SING: 
						# Expected response for write single reg
						# extract and format the response according to the register written 
						#    0   1   2   3   4   5   
						#  [sa][06][  reg  ][  val ][crc16]
						# 
						msg = struct.unpack('>2B3H',data)
						if msg[0] == self.__REG_TH	: 
							self.__thresh = float(msg[2])
							res = True
						elif msg[0] == self.__REG_ADDR:
							self.__addr = msg[2]
							res = True
						else: 
							self.__dump('unknown valid response to 0x06 msg:',buf[:buflen])
					elif data[1] == self.__FC_U_RESET or data[1] == self.__FC_U_CAL: 
						# Expected response for user defined function code
						# 
						#    0   1  2   3    
						#  [sa][fc][crc16]
						res = True
					else:
						self.__dump('unknown valid msg:',buf[:buflen])
				else:
					self.__dump('bad checksum:',buf[:buflen])
			elif len(buf) > 0:
				self.__dump('not enough data:',buf[:buflen])
		return res
		
	def Poll(self):
		"""
			read data from the module and return it as a tuple
			
		"""
		
		pd = None
		if self.__cmd_read_regs(self.__SLAVEADD,self.__FC_R_INP,self.__REG_U,10):
			pd = self.PollData(
						Volt 	= self.__volt,
						Current = self.__current,
						Power	= self.__power,
						Energy	= self.__energy,
						Freq	= self.__freq,
						Pf		= self.__pf,
						Alarm	= self.__alarm)
		return pd
	
	def PowerAlarm(self,Value = None):
		"""
			reads and/or sets the power alarm threshold
			
		"""
		res = None
		if Value == None:
			if self.__cmd_read_regs(self.__SLAVEADD,self.__FC_R_HOLD,self.__REG_TH,2):
				res = self.__thresh
		else:
			if (Value < 0) or (Value > 0x7fff):
				raise ValueError
			if self.__cmd_write_reg(self.__SLAVEADD,self.__REG_TH,int(round(Value,0))):
				res = self.__thresh
		return res
	def SlaveAddress(self, New_Slave_Addr=None):
		"""
                sets the Slave Address from Old_Slave_Addr to New_Slave_Addr (0x0001 to 0x00F7)
                with cmd (Old_Slave_Addr,0x06,Reg_Addr_HH,Reg_Addr_LL,Val_HH,Val_LL ,CRC_HH, CRC_LL)
                Correct Response: New_Slave_Addr,0x06,Num_Bytes,Reg_Addr_LL,Val_HH,Val_LL,CRC_HH,CRC_LL
                Error Reply: Slave_Addr, 0x86,Abnormal code, CRC_HH, CRC_LL
                Old_Slave_Addr written to __addr = .GetSlaveAddress on initialize
		"""
		res = None
		success = False
		if New_Slave_Addr == None:
			if self.__cmd_read_regs(self.__CALADD, self.__FC_R_HOLD, self.__REG_TH, 2):
				res = self.__addr
		elif (New_Slave_Addr < 0) or (New_Slave_Addr > 0x00f7):
			raise ValueError
		else:
			print('setting ' + str(self.__addr) +
					' to new addr: ' + str(New_Slave_Addr))
			if self.__cmd_write_reg(self.__addr, self.__REG_ADDR, New_Slave_Addr):
				res = self.__addr
				success = res == New_Slave_Addr
			print('success: ' + str(success))
		return res
	def ResetEnergy(self):
		"""
			resets the energy counter
			
		"""
		res = self.__cmd_userfunc(self.__SLAVEADD,self.__FC_U_RESET)
		return res
		

	def __init__(self,ACMport=DEFPORT,ACMspeed=9600):
		self.__ACM = serial.Serial(port = ACMport,
						baudrate=ACMspeed,
						timeout = 0.01)	
		# read and record current dev Slave_Addr
		# sets self.__addr from self.SlaveAddress(None) returns
		print('initializing meter - getting Address')
		print('initializing meter - has address: ' +
				str(self.SlaveAddress(None)))


if __name__ == "__main__":
	arg = parser.parse_args()
	
	ACM = AC_COMBOX(arg.port_dev)
	
	if arg.out_name=='!':
		out_name = 'ACM_'+strftime('%Y%m%d%H%M%S',localtime())+'.csv'
	else:
		out_name = arg.out_name
		
	if arg.reset:
		ACM.ResetEnergy()
	
	
	ACM.PowerAlarm(arg.alarm)
	
	
	f = open(out_name,'w')
	f.write('Time[S],Volt[V],Current[A],Power[W],Energy[Wh],Freq[Hz],PF, Alarm\n')
	start = perf_counter()
	now = perf_counter()-start
	try:			
		while True:
			now = perf_counter()-start
			pd = ACM.Poll()
			s = '{:5.1f},{:4.1f},{:7.3f},{:5.1f},{:5.0f},{:3.1f},{:5.2f},{:1n}'.format(
				now,
				pd.Volt, 
				pd.Current,
				pd.Power,
				pd.Energy,
				pd.Freq,
				pd.Pf,
				pd.Alarm)
			f.write(s+'\n')
			print(s)
			elapsed = (perf_counter()-start) - now
			if elapsed < arg.int_time:
				sleep(arg.int_time - elapsed)
	except KeyboardInterrupt:
		f.close()			




