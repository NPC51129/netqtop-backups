#! /bin/bash
SOCKPERF="sockperf"
TOOL="./netqtop.py"
RUNTIME=20
THREADS=$1
LOGPREFIX="throughput"

echo "Throughput Case: $THREADS threads" 
# -----------------------------------------------------------------
# part 1: run sockperf
for((i=0;i<${THREADS};i++)); do
    taskset -c $i ${SOCKPERF} tp -i 127.0.0.1 -t ${RUNTIME} > ${LOGPREFIX}.${i}.log 2>&1 &
    pids[$i]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done

totalmsg1=0
for((i=0;i<${THREADS};i++)); do
    msg=$(cat ${LOGPREFIX}.${i}.log | grep Message | awk '{match($0, /(Message Rate is )([0-9]+)/, a); print a[2]}')
    totalmsg1=$((${totalmsg1}+$msg))
done
totalmsg1=$(echo ${totalmsg1} | bc)
rm -f throughput.*.log

# -----------------------------------------------------------------
# part 2: run sockperf and netqtop
taskset -c 0 ${TOOL} -n eth0 -i 1 > netqtop.log 2>&1 &
pid1=$!

for((i=0;i<${THREADS};i++)); do
    taskset -c $i ${SOCKPERF} tp -i 192.168.0.123 -t ${RUNTIME} > ${LOGPREFIX}.${i}.log 2>&1 &
    pids[$i]=$!
done

for pid in ${pids[*]}; do
    wait $pid
done

totalmsg2=0
for((i=0;i<${THREADS};i++)); do
    msg=$(cat ${LOGPREFIX}.${i}.log | grep Message | awk '{match($0, /(Message Rate is )([0-9]+)/, a); print a[2]}')
    totalmsg2=$((${totalmsg2}+$msg))
done
totalmsg2=$(echo ${totalmsg2} | bc)

# ------------------------------------------------------------------
# results 
echo "Sockperf message rate: $totalmsg1"
echo "Sockperf message rate while running netqtop: $totalmsg2"
variation=$(echo ${totalmsg1}-$totalmsg2 | bc)
echo PPS decreases: $variation
rate=$(echo "${variation} ${totalmsg1}" | awk '{printf("%.2f",$1*100/$2)}')
if [ $(echo "$rate<=0" | bc) == 1 ]; then
    echo PPS decreased by 0.00% 
else
    echo PPS decreased by ${rate}% 
fi

kill $pid1 > /dev/null 2>&1
rm -f throughput.*.log
