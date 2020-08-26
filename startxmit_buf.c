//#include <linux/skbuff.h>
#include <linux/netdevice.h>
//#include <linux/tracepoint.h>
//#include <bcc/proto.h>
//#include <linux/sched.h>
//#define	IFNAMSIZ	16
#include <linux/ethtool.h>
#define TRACEPOINT_NET_DEV_START_XMIT 1241
#define TRACEPOINT_NETIF_RECEIVE_SKB_ENTRY 1234

struct data_t{
    //char * name;
    char name[IFNAMSIZ];
	u16 queue_mapping;
	unsigned int skblen;
    u64 tpid; // tracepoint id
    u16 protocol;
};

BPF_PERF_OUTPUT(events);

TRACEPOINT_PROBE(net, net_dev_start_xmit){
    
	struct data_t data = {};
    __builtin_memset(&data, 0, sizeof(data));
	
    // -------------- device name --------------
    /*
	int name = args->data_loc_name;
    u64 base = (u64)args;
    u64 offset = (u64)(name & 0xffff);
    u64 length = (u64)((name >> 16)&0xffff);
    bpf_probe_read(&data.name, sizeof(data.name), (char*)(base+offset));
    */
    struct sk_buff* skb = (struct sk_buff*)args->skbaddr;
    struct net_device *dev;
    bpf_probe_read(&dev, sizeof(skb->dev), ((char*)skb + offsetof(typeof(*skb), dev)));
    bpf_probe_read(&data.name, IFNAMSIZ, dev->name);

	// -------------- queue id ------------------
    data.queue_mapping = skb->queue_mapping;

    // -------------- data length ---------------- 
    data.skblen = skb->len; //args->len is of the same value as skb->len

    // -------------- func name
    data.tpid = TRACEPOINT_NET_DEV_START_XMIT;

    data.protocol = args->protocol;

    // -------------- submit data ----------------
    events.perf_submit(args, &data, sizeof(data));

	return 0;
}

TRACEPOINT_PROBE(net, netif_receive_skb){
    
	struct data_t data = {};
    __builtin_memset(&data, 0, sizeof(data));

    struct sk_buff* skb = (struct sk_buff*)args->skbaddr;
    struct net_device *dev;
    bpf_probe_read(&dev, sizeof(skb->dev), ((char*)skb + offsetof(typeof(*skb), dev)));
    bpf_probe_read(&data.name, IFNAMSIZ, dev->name);
    data.queue_mapping = skb->queue_mapping;
    data.skblen = skb->len;
    //data.time = bpf_ktime_get_ns();
    data.tpid = TRACEPOINT_NETIF_RECEIVE_SKB_ENTRY;
    
    events.perf_submit(args, &data, sizeof(data));

    return 0;
}
