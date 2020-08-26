#! /bin/bash

SOCKPERF="sockperf"
TOOL="./netqtop.py"
RUNTIME=20
LOGPREFIX="latency"
PORT=13344

pkill sockperf > /dev/null 2>&1
# start server
taskset -c 0 ${SOCKPERF} sr -p ${PORT} > /dev/null 2>&1 &

# start client while not running tool(netqtop)
CPUNUM=$(cat /proc/cpuinfo | grep processor | wc -l)
taskset -c $((CPUNUM-1)) ${SOCKPERF} pp -t ${RUNTIME} -i 127.0.0.1 -p ${PORT} \
        > ${LOGPREFIX}.part1.log 2>&1 &
wait $!

late1=$(cat ${LOGPREFIX}.part1.log | awk '{match($0, /(Summary: Latency is )([0-9]+\.[0-9]+)/, a); print a[2]}')

# start client while running tool(netqtop)
if [ $CPUNUM == 1 ]; then
    taskset -c 0 ${TOOL} -n eth0 -i 1 > /dev/null 2>&1 &
else
    taskset -c $((CPUNUM-2)) ${TOOL} -n eth0 -i 1 > /dev/null 2>&1 &
fi

pid1=$!

taskset -c $((CPUNUM-1)) ${SOCKPERF} pp -t ${RUNTIME} -i 127.0.0.1 -p ${PORT} \
        > ${LOGPREFIX}.part2.log 2>&1 &
wait $!

late2=$(cat ${LOGPREFIX}.part2.log | awk '{match($0, /(Summary: Latency is )([0-9]+\.[0-9]+)/, a); print a[2]}')

late1=$(echo $late1 | bc)
late2=$(echo $late2 | bc)
echo Original Latency: $late1 usec
echo Latency when running netqtop: $late2 usec
echo Latency increased by $(echo "$late1 $late2" | awk '{printf("%.2f%%", ($2-$1)*100/$1)}')
pkill netqtop > /dev/null 2>&1
pkill sockperf > /dev/null 2>&1 &
rm -f latency.*.log
