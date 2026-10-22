"""
Generate FAKE runs.csv / samples.csv for testing plots.py.
None of this is real measurement: the curves follow simple hard-coded rules
(loss-based sawtooth for cubic/reno, flat cwnd with probe bumps for bbr).

Usage:  python3 gen_fake_data.py      (writes runs.csv and samples.csv here)
        python3 ../../plots.py --runs runs.csv --samples samples.csv --out out
"""
import csv, random, math
random.seed(1)
servers=[("speedtest.chi11.us.leaseweb.net",5201,20),("102.214.66.39",5201,180),("iperf.he.net",5201,45)]
rw=csv.writer(open("runs.csv","w",newline="")); sw=csv.writer(open("samples.csv","w",newline=""))
rw.writerow("run_id,server,port,algo_requested,algo_actual,rep,start_utc,status,error".split(","))
sw.writerow("run_id,t_s,bytes_acked,goodput_mbps,cwnd_segs,srtt_ms,rttvar_ms,min_rtt_ms,total_retrans,retrans_delta,pacing_rate_mbps".split(","))
for si,(h,p,base) in enumerate(servers):
  for rep in range(3):
    for a in ["cubic","reno","bbr"]:
      rid=f"r{si}-{a}-{rep}"; rw.writerow([rid,h,p,a,a,rep,"2026-10-21T05:00:00Z","ok",""])
      cw=10;acked=0;tot=0;wmax=200
      for i in range(1,301):
        t=i*0.2
        loss=0
        if a=="bbr":
          cw = min(cw*1.5, 120) if t<2 else 120*(1.25 if i%40<5 else (0.5 if i%400<3 else 1))
          rtt=base*(1.05+0.1*random.random())
          if random.random()<0.02: loss=random.randint(1,5)
        else:
          cw = cw*2 if cw<60 and t<1 else cw+(1 if a=="reno" else 2)
          rtt=base*(1+min(cw,400)/400)
          if cw>wmax+random.randint(-30,30): loss=random.randint(2,20); wmax=cw; cw=cw*(0.5 if a=="reno" else 0.7)
        gp=cw*1448*8/(rtt/1000)/1e6*(0.9+0.2*random.random())
        acked+=gp*1e6/8*0.2; tot+=loss
        sw.writerow([rid,f"{t:.1f}",int(acked),f"{gp:.2f}",int(cw),f"{rtt:.2f}",f"{rtt*0.1:.2f}",f"{base:.2f}",tot,loss,f"{gp*1.2:.2f}"])
rw.writerow(["bad","1.2.3.4",5201,"bbr","",0,"x","failed","timeout"])
