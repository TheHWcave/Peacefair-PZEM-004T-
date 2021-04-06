# Peacefair-PZEM-004T-
reverse-engineered schematics and interface software 

The PZEM-004T module is a mains powered module that measures voltage, current, power factor, apparent power and frequency. It has no display but provides these values over a serial interface. 

I have reverse-enineered the circuit in PZEM004T-orig.pdf
The modification I have performed is in PZEM004-opton2.pdf 

The modification allows it to measure from 0VAC onwards and powers it from the serial interface instead of mains. This module uses AC mains directly. Use or modify it only if you are familiar with the necessary precautions. Use at your own risk!

Edited to add:
Regarding R17a and R17b in the modification: These should be rated for 350V. I used TE-connectivity type  LR1F  0.6W 1%    or Vishay MRS25 0.6W 1%  . The combined value needs to match the original R17 which in my module was just 978K  (instead of 1M). This is because the module has been factory-calibrated with the original R17. For the isolating (!!!!) DC-2-DC converter I used Recom 1W DC-DC converter 4.5-5.5V to 12V  RS-Components stock# 828-9343, price £10.66 (incl VAT). This converter is more expensive than the usual isolating types but tested to 6.4KV (instead of the usual 1KV). The 1KV types are generally not designed to be exposed continuously to high voltage. 

There is a YouTube video about the modification, here: https://www.youtube.com/watch?v=qRsjsenvlJA

The software will work with original or modified modules. Note that the x1/x10 feature in the software only makes sense if you use the current transformer with either a single wire passing through the core (x1 mode , range 0.02A to 100A), or 10 windings (x10 mode, range 0.002A to 10A)

The AC_USB_PowerMeter.py contains the GUI. It needs the AC_COMBOX.py which contains the serial interface handler. Use Python3.8 or newer. The software has been tested on Linux and Windows 7. 


usage: AC_USB_PowerMeter.py [-h] [--port PORT] [--no_average]

optional arguments:
  -h, --help    show this help message and exit
  --port PORT   port
  --no_average  disables recording of averages

