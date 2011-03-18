## This file is part of conftron.
## 
## Copyright (C) 2011 Greg Horn <ghorn@stanford.edu>
## 
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
## 02110-1301, USA.

import sys
import time
import argparse
import math

import lcm

print_status_ts = 0.1
rms_tracking_error_lowpass_tau = 1

# command line switches
parser = argparse.ArgumentParser(description='lightweight LCM log player')
parser.add_argument('logfile', type=str, help='logfile to play back')
parser.add_argument('-r', dest='time_dialation', type=float, default=1.0, help='time dialation, bigger for faster')
parser.add_argument('-q', dest='quiet', action="store_true", default=False, help='suppress all non-error output')
args = parser.parse_args()

# open log
if not args.quiet:
    print 'opening \"'+args.logfile+'\"'
log = lcm.EventLog(args.logfile, "r")
if not args.quiet:
    humanreadable = lambda s:[(s%1024**i and "%.2f"%(s/1024.0**i) or str(s/1024**i))+x.strip() for i,x in enumerate(' KMGTPEZY') if s<1024**(i+1) or i==8][0]
    print 'logfile is '+str(humanreadable(log.size()))+'B ('+str(log.size())+' bytes)'

# loop through and play log
lc = lcm.LCM()
sys_t_offset = time.time()
log_t_offset = None
next_print_time = 0

mean_error = 0.0
mean_squared_error = 0.0
last_log_time = 0.0
for event in log:
    # get the time tracking right
    if not log_t_offset:
        log_t_offset = event.timestamp

    log_time = (event.timestamp - log_t_offset)*1.0e-6
    sys_time = (time.time() - sys_t_offset)

    time_error = log_time - sys_time*args.time_dialation

    if time_error > 0:
        time.sleep(time_error)

    # print status message
    if not args.quiet:
        # lowpass rms time tracking error
        dt = log_time - last_log_time
        last_log_time = log_time
        emdt = math.exp(-dt/rms_tracking_error_lowpass_tau)
        mean_error = emdt*mean_error + (1.0-emdt)*time_error
        mean_squared_error = emdt*mean_squared_error + (1.0-emdt)*time_error*time_error
        
        if sys_time > next_print_time:
            sys.stdout.write("\r                                             ")
            sys.stdout.write("\rlog time: %.3f seconds (%.2f %%), rms tracking error: %.3f ms " % (log_time, float(100*log.tell())/float(log.size()), math.sqrt(mean_squared_error - mean_error*mean_error)*1e3 ))
            sys.stdout.flush()
            next_print_time += print_status_ts

    # send the message
    lc.publish(event.channel, event.data)

log.close()

if not args.quiet:
    print "finished playing log"
