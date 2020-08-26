#!/usr/bin/python2

from bcc import BPF
from bcc.utils import printb
import os
import argparse
import thread
import time

# pre-defines
ROOT_PATH = "/sys/class/net"
TRACEPOINT_NET_DEV_START_XMIT = 1241
TRACEPOINT_NETIF_RECEIVE_SKB_ENTRY = 1234
LEN0 = 0
LEN1 = 64 
LEN2 = 512 
LEN3 = 2048
LEN4 = 16384
LEN5 = 65536
LENs = 5
# global variables
tx_num = 0
rx_num = 0
tx_queue = {}
rx_queue = {}
print_interval = 1.0

# ----------------------------------------------------------
# format_printer:
# output BPS, PPS and average packet size
# for each queue and all queues in total
# [0, 64) [64, 512) [512, 2048) [2048, 16384) [16384, 65536+)
# ----------------------------------------------------------
def format_printer(queue, num, interval):
	#global tx_queue, rx_queue, print_interval
	# duration = (end_time - start_time)
	duration = interval + 0.0
	if duration == 0.0:
		exit()

	# --- format ---
	COL_WIDTH = 10
	LEN1 = 64
	LEN2 = 512
	LEN3 = 2048
	LEN4 = 16384

	#---------------- table for tx ---------------

	# table header
	headers = [
		"QueueID", 
		"BPS", 
		"PPS", 
		"avg_size", 
		"[0, 64)", 
		"[64, 512)", 
		"[512, 2K)", 
		"[2K, 16K)",
		"[16K, 64K)"
	]
	for hd in headers:
		print(hd.center(COL_WIDTH)),
	print

	# contents
	tlen = 0
	tpkg = 0
	t_groups = [0]*LENs

	for i in range(num):
		len_cnt = queue['len_cnt'][i]
		pkg = queue['pkg_cnt'][i]
		group = queue['size_group'][i]
		t_groups = [(t_groups[k] + group[k]) for k in range(LENs)]

		tlen += len_cnt
		tpkg += pkg
		if pkg != 0:
			avg_size = len_cnt / pkg
		else:
			avg_size = 0

		printb(b"%5d %11.2f %10.2f %10d %10d %10d %10d %10d %10d" % (
			i, 
			len_cnt/duration, 
			pkg/duration, 
			avg_size, 
			group[0],
			group[1],
			group[2],
			group[3],
			group[4]
		))

	if tpkg >0:
		t_avg = tlen / tpkg
	else:
		t_avg = 0

	printb(b" Total %10.2f %10.2f %10d %10d %10d %10d %10d %10d" % (
		tlen / duration, 
		tpkg / duration, 
		t_avg,
		t_groups[0],
		t_groups[1],
		t_groups[2],
		t_groups[3],
		t_groups[4]
	))
	print 
	

#----------------------------------------------------
# timer function, call format_printer every interval
#----------------------------------------------------
def timing_printer():
	global print_interval
	while 1:
		time.sleep(print_interval)
		print("")
		print("TX")
		format_printer(tx_queue, tx_num, print_interval)
		# clear tx queue
		tx_queue['pkg_cnt'] = [0] * tx_num
		tx_queue['len_cnt'] = [0] * tx_num
		for i in range(tx_num):
			tx_queue['size_group'][i] = [0] * LENs
		print("")
		print("RX")
		format_printer(rx_queue, rx_num, print_interval)
		# clear rx queue
		rx_queue['pkg_cnt'] = [0] * rx_num
		rx_queue['len_cnt'] = [0] * rx_num
		for i in range(rx_num):
			rx_queue['size_group'][i] = [0] *LENs


############## specify network interface #################
parser = argparse.ArgumentParser(description="")
parser.add_argument("--name", "-n", type=str, default="")
parser.add_argument("--interval", "-i", type=int, default=1)
args = parser.parse_args()
if args.name == "":
	print ("Please specify a network interface.")
	exit()
else:
	dev_name = args.name
print_interval = args.interval

################ get number of queues #####################
tx_num = 0
rx_num = 0
path = ROOT_PATH + "/" + dev_name + "/queues"
if not os.path.exists(path):
	print "Net interface", dev_name, "does not exits."
	exit()

list = os.listdir(path)
for str in list:
    if str[0] == 'r':
        rx_num += 1
    if str[0] == 't':
        tx_num += 1

###################### tracing ########################
tx_queue = {
	'pkg_cnt': [0] * tx_num,
	'len_cnt': [0] * tx_num,
	'size_group': [[0]] * tx_num
}
for i in range(tx_num):
	tx_queue['size_group'][i] = [0] * LENs

rx_queue = {
	'pkg_cnt': [0] * rx_num,
	'len_cnt': [0] * rx_num,
	'size_group': [0] * rx_num
}
for i in range(rx_num):
	rx_queue['size_group'][i] = [0] *LENs

# ------------------- start tracing ------------------
b = BPF(src_file = "startxmit_buf.c")

# start printing thread
thread.start_new_thread(timing_printer,())

# process event
def handle_data(cpu, data, size):
	global tx_queue, rx_queue
	event = b['events'].event(data)

	# device name
	if event.name != dev_name:
		return

	# for transmited data
	if event.tpid == TRACEPOINT_NET_DEV_START_XMIT:
		id = event.queue_mapping
		tx_queue['pkg_cnt'][id] += 1
		tx_queue['len_cnt'][id] += event.skblen
		if event.skblen / LEN5:
			pass
		elif event.skblen / LEN4:
			tx_queue['size_group'][id][4] += 1
		elif event.skblen / LEN3:
			tx_queue['size_group'][id][3] += 1
		elif event.skblen / LEN2:
			tx_queue['size_group'][id][2] += 1
		elif event.skblen / LEN1:
			tx_queue['size_group'][id][1] += 1
		else:
			tx_queue['size_group'][id][0] += 1
	# for received data
	elif event.tpid == TRACEPOINT_NETIF_RECEIVE_SKB_ENTRY:
		id = event.queue_mapping
		rx_queue['pkg_cnt'][id] += 1
		rx_queue['len_cnt'][id] += event.skblen
		if event.skblen / LEN5:
			pass
		elif event.skblen / LEN4:
			rx_queue['size_group'][id][4] += 1
		elif event.skblen / LEN3:
			rx_queue['size_group'][id][3] += 1
		elif event.skblen / LEN2:
			rx_queue['size_group'][id][2] += 1
		elif event.skblen / LEN1:
			rx_queue['size_group'][id][1] += 1
		else:
			rx_queue['size_group'][id][0] += 1

# loop callback 
b["events"].open_perf_buffer(handle_data)
while 1:
	try:
		b.perf_buffer_poll()
	except KeyboardInterrupt:
		exit()
#------------------ end tracing ----------------------
'''
while 1:
	try:
		(task, pid, cpu, flags, ts, msg) = b.trace_fields()
		print msg
	except KeyboardInterrupt:
		exit()
		
'''
