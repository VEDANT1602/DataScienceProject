"""Reproducible synthetic longitudinal-braking envelope benchmark.

No real vehicles, perception models, roads, or observed accident data are used.
Run: python study.py --output results
Python 3.11+ standard library; NumPy and Matplotlib only for verification/figures.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import time


@dataclass(frozen=True)
class Profile:
    speed: float
    decel: float
    jerk: float
    delay: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.speed,self.decel,self.jerk,self.delay)):
            raise ValueError("Braking parameters must be finite")
        if self.speed < 0 or self.decel <= 0 or self.jerk <= 0 or self.delay < 0:
            raise ValueError("Invalid braking profile")

    @property
    def ramp(self):
        return min(self.decel / self.jerk, math.sqrt(2 * self.speed / self.jerk))

    @property
    def ramp_speed(self):
        return max(0.0, self.speed - 0.5 * self.jerk * self.ramp**2)

    @property
    def stop_time(self):
        return self.delay + self.ramp + self.ramp_speed / self.decel

    @property
    def stop_distance(self):
        u = self.ramp
        return (self.speed * self.delay + self.speed * u
                - self.jerk * u**3 / 6
                + self.ramp_speed**2 / (2 * self.decel))

    def state(self, t):
        """Displacement, nonnegative velocity at absolute time t."""
        if not math.isfinite(t) or t < 0:
            raise ValueError("Time must be finite and nonnegative")
        if t <= self.delay:
            return self.speed * t, self.speed
        u = t - self.delay
        if u <= self.ramp:
            return (self.speed * t - self.jerk * u**3 / 6,
                    max(0.0, self.speed - 0.5 * self.jerk * u**2))
        if t >= self.stop_time:
            return self.stop_distance, 0.0
        w = u - self.ramp
        xr = self.speed * (self.delay + self.ramp) - self.jerk * self.ramp**3 / 6
        return (xr + self.ramp_speed * w - 0.5 * self.decel * w**2,
                self.ramp_speed - self.decel * w)

    def velocity_polynomial(self, t):
        """Coefficients c0,c1,c2 for velocity on the phase containing t."""
        if t < self.delay:
            return self.speed, 0.0, 0.0
        if t < self.delay + self.ramp:
            return (self.speed - 0.5 * self.jerk * self.delay**2,
                    self.jerk * self.delay, -0.5 * self.jerk)
        if t < self.stop_time:
            return (self.ramp_speed + self.decel * (self.delay + self.ramp),
                    -self.decel, 0.0)
        return 0.0, 0.0, 0.0


def real_roots(c0, c1, c2):
    if abs(c2) < 1e-12:
        return [] if abs(c1) < 1e-12 else [-c0 / c1]
    discrim = c1 * c1 - 4 * c2 * c0
    if discrim < -1e-10:
        return []
    sqrt_d = math.sqrt(max(0.0, discrim))
    # Stable quadratic calculation avoids subtracting nearly equal terms.
    q = -0.5 * (c1 + math.copysign(sqrt_d, c1))
    if abs(q) < 1e-15:
        return [-c1 / (2 * c2)]
    return [q / c2, c0 / q]


def envelope(follower, leader):
    """Maximum closure over the complete planned braking motion, m.

    Gap here is bumper clearance: vehicle lengths are not subtracted twice.
    Returns required nonnegative clearance, earliest maximizing time, and
    number of finite candidates examined. A positive engineering margin must
    be added to avoid interpreting zero clearance as non-contact.
    """
    horizon = max(follower.stop_time, leader.stop_time)
    breaks = sorted(set([0.0, horizon, follower.delay, leader.delay,
                         follower.delay + follower.ramp,
                         leader.delay + leader.ramp,
                         follower.stop_time, leader.stop_time]))
    candidates = list(breaks)
    for lo, hi in zip(breaks[:-1], breaks[1:]):
        if hi - lo < 1e-12:
            continue
        fp = follower.velocity_polynomial((lo + hi) / 2)
        lp = leader.velocity_polynomial((lo + hi) / 2)
        coeff = [f - l for f, l in zip(fp, lp)]
        candidates.extend(r for r in real_roots(*coeff) if lo < r < hi)
    scored = sorted((follower.state(t)[0] - leader.state(t)[0], -t)
                    for t in candidates)
    gap, negative_t = scored[-1]
    return max(0.0, gap), -negative_t, len(candidates)


def endpoint(follower, leader):
    return max(0.0, follower.stop_distance - leader.stop_distance)


def instant_endpoint(follower, leader):
    return max(0.0, follower.speed * follower.delay
               + follower.speed**2 / (2 * follower.decel)
               - leader.speed**2 / (2 * leader.decel))


def percentile(values, q):
    values = sorted(values)
    t = (len(values) - 1) * q
    lo = int(t)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (t - lo) * (values[hi] - values[lo])


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def wilson(success, n):
    """Descriptive 95% Wilson interval for synthetic iid Bernoulli draws."""
    z = 1.959963984540054
    p = success / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return [max(0., center-radius), min(1., center+radius)]


def verify(output):
    import numpy as np
    rng = random.Random(937)
    results = []
    # These scenarios are separate from both the factorial and uncertainty sets.
    for k in range(200):
        f = Profile(rng.uniform(0.1, 40), rng.uniform(1, 12), rng.uniform(1, 40), rng.uniform(0, 1))
        l = Profile(rng.uniform(0.1, 40), rng.uniform(1, 12), rng.uniform(1, 40))
        exact, when, _ = envelope(f, l)
        horizon = max(f.stop_time, l.stop_time)
        # Independent dense sampling of the state equations: not a proof,
        # but it catches missed roots and incorrect phase selection.
        ts = np.linspace(0, horizon, 50001)
        def vector_x(p):
            u = np.maximum(0., ts-p.delay)
            ramp_u = np.minimum(u, p.ramp)
            w = np.clip(u-p.ramp, 0., p.ramp_speed/p.decel)
            return (p.speed*np.minimum(ts,p.delay)
                    + p.speed*ramp_u-p.jerk*ramp_u**3/6
                    + p.ramp_speed*w-.5*p.decel*w**2)
        dense = float(np.max(vector_x(f)-vector_x(l)))
        error = exact-max(0.,dense)
        assert -1e-8 <= error < 1e-3, (f,l,exact,dense)
        assert exact+1e-9 >= endpoint(f,l)
        results.append(dict(case=k, exact=exact,dense=max(0.,dense), difference_m=error, maximizing_t=when))
    # Physical/limiting cases independent of the random validation.
    p=Profile(20,6,12,.3)
    assert abs(envelope(p,p)[0]) < 1e-10
    assert abs(Profile(0,6,12).stop_distance) < 1e-10
    for bad in [float("nan"),float("inf"),float("-inf")]:
        for params in [(bad,6,12,0),(20,bad,12,0),(20,6,bad,0),(20,6,12,bad)]:
            try:
                Profile(*params)
            except ValueError:
                pass
            else:
                raise AssertionError("Nonfinite profile accepted")
    for v,b,tau in product([1,10,30],[2,6,10],[0,.3]):
        p=Profile(v,b,1e8,tau)
        assert abs(p.stop_distance-(v*tau+v*v/(2*b))) < 1e-4
    write_csv(output/"verification.csv", results)
    # Independently integrate acceleration on a fixed fine mesh, then clamp
    # nonnegative velocity and integrate position. This does not use state().
    dynamics=[]
    for k in range(40):
        f = Profile(rng.uniform(.1,40),rng.uniform(1,12),rng.uniform(1,40),rng.uniform(0,1))
        l = Profile(rng.uniform(.1,40),rng.uniform(1,12),rng.uniform(1,40))
        horizon=max(f.stop_time,l.stop_time)
        ts=np.linspace(0,horizon,int(math.ceil(horizon/.0005))+1)
        dt=ts[1]-ts[0]
        def integrate(p):
            acceleration=-np.minimum(p.jerk*np.maximum(0.,ts-p.delay),p.decel)
            velocity=np.maximum(0.,p.speed+np.r_[0.,np.cumsum((acceleration[:-1]+acceleration[1:])*.5*dt)])
            return np.r_[0.,np.cumsum((velocity[:-1]+velocity[1:])*.5*dt)]
        xf=integrate(f);xl=integrate(l)
        integrated=max(0.,float(np.max(xf-xl)))
        exact=envelope(f,l)[0]
        err=abs(exact-integrated)
        assert err<.005, (exact,integrated,f,l)
        assert abs(xf[-1]-f.stop_distance)<.005
        assert abs(xl[-1]-l.stop_distance)<.005
        dynamics.append(dict(case=k,exact_gap_m=exact,integrated_gap_m=integrated,absolute_error_m=err,step_s=dt))
    write_csv(output/"dynamics_verification.csv",dynamics)
    return {"random_cases":200,"samples_each":50001,
            "max_exact_minus_dense_m":max(x["difference_m"] for x in results),
            "min_exact_minus_dense_m":min(x["difference_m"] for x in results),
            "independent_dynamics_cases":40,"independent_dynamics_step_s_max":.0005,
            "independent_dynamics_max_error_m":max(x["absolute_error_m"] for x in dynamics),
            "limiting_and_identical_cases":"passed"}


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    verification=verify(output)
    rows=[]
    grid={"follower_speed_mps":[10.,20.,30.],"leader_speed_ratio":[.5,.75,1.,1.25],
          "follower_decel_mps2":[3.,6.,9.],"leader_decel_mps2":[3.,6.,9.],
          "follower_delay_s":[0.,.2,.5],"follower_jerk_mps3":[5.,10.,20.],
          "leader_jerk_mps3":[5.,10.,20.]}
    for i,params in enumerate(product(*grid.values())):
        vf,ratio,bf,bl,tau,jf,jl=params
        f=Profile(vf,bf,jf,tau);l=Profile(vf*ratio,bl,jl)
        exact,when,nc=envelope(f,l)
        end=endpoint(f,l);inst=instant_endpoint(f,l)
        row=dict(zip(grid.keys(),params))
        row.update(case=i,leader_speed_mps=vf*ratio,full_gap_m=exact,
                   endpoint_gap_m=end,instant_endpoint_gap_m=inst,
                   endpoint_shortfall_m=exact-end,
                   instant_shortfall_m=max(0.,exact-inst),
                   instant_excess_m=max(0.,inst-exact),maximizing_t_s=when,
                   follower_stop_s=f.stop_time,leader_stop_s=l.stop_time,
                   candidate_count=nc)
        rows.append(row)
    write_csv(output/"factorial.csv",rows)
    summary={"n":len(rows),"grid":grid,"verification":verification}
    for key in ["endpoint","instant"]:
        vals=[r[key+"_shortfall_m"] for r in rows]
        summary[key]={"shortfall_gt_1mm_count":sum(x>.001 for x in vals),
                      "shortfall_gt_1m_count":sum(x>1 for x in vals),
                      "mean_shortfall_m":statistics.mean(vals),
                      "p95_shortfall_m":percentile(vals,.95),"max_shortfall_m":max(vals)}
    summary["endpoint_worst_case"]=max(rows,key=lambda r:r["endpoint_shortfall_m"])
    summary["instant_worst_case"]=max(rows,key=lambda r:r["instant_shortfall_m"])
    # The known RSS inequality is not enforced in the unrestricted grid.
    # Report this subgroup explicitly to avoid attacking RSS outside its assumptions.
    for cond,fn in [("follower_decel_leader_or_less",lambda r:r["follower_decel_mps2"]<=r["leader_decel_mps2"]),
                    ("follower_decel_stronger",lambda r:r["follower_decel_mps2"]>r["leader_decel_mps2"])]:
        subset=[r for r in rows if fn(r)]
        summary[cond]={"n":len(subset),"endpoint_shortfall_gt_1mm_count":sum(r["endpoint_shortfall_m"]>.001 for r in subset),
                       "endpoint_max_shortfall_m":max(r["endpoint_shortfall_m"] for r in subset),
                       "instant_shortfall_gt_1mm_count":sum(r["instant_shortfall_m"]>.001 for r in subset)}
    by_delay=[]
    for tau in grid["follower_delay_s"]:
        subset=[r for r in rows if r["follower_delay_s"]==tau]
        by_delay.append(dict(delay_s=tau,n=len(subset),
                            endpoint_shortfall_gt_1m_count=sum(r["endpoint_shortfall_m"]>1 for r in subset),
                            instant_shortfall_gt_1m_count=sum(r["instant_shortfall_m"]>1 for r in subset),
                            endpoint_mean_shortfall_m=statistics.mean(r["endpoint_shortfall_m"] for r in subset)))
    write_csv(output/"by_delay.csv",by_delay)
    # Controlled parameter-mismatch experiment. These are authored distributions,
    # not fitted to road/weather/vehicle data; uncertainty intervals are chosen.
    rng=random.Random(241107)
    uncertainty=[]
    for regime in ["inside_declared_bounds","outside_declared_bounds"]:
        for i in range(5000):
            vf=rng.uniform(10,30);vl=vf*rng.uniform(.5,1.25)
            bf=rng.uniform(3,9);bl=rng.uniform(3,9)
            jf=rng.uniform(5,20);jl=rng.uniform(5,20);tau=rng.uniform(0,.5)
            nf=Profile(vf,bf,jf,tau);nl=Profile(vl,bl,jl)
            corner_f=Profile(vf,.8*bf,.8*jf,tau+.15)
            corner_l=Profile(vl,1.2*bl,1.2*jl)
            if regime=="inside_declared_bounds":
                af=Profile(vf,bf*rng.uniform(.8,1.2),jf*rng.uniform(.8,1.2),max(0.,tau+rng.uniform(-.15,.15)))
                al=Profile(vl,bl*rng.uniform(.8,1.2),jl*rng.uniform(.8,1.2))
            else:
                af=Profile(vf,bf*rng.uniform(.6,.8),jf*rng.uniform(.6,.8),tau+rng.uniform(.15,.30))
                al=Profile(vl,bl*rng.uniform(1.2,1.4),jl*rng.uniform(1.2,1.4))
            truth=envelope(af,al)[0]
            nom=envelope(nf,nl)[0];corner=envelope(corner_f,corner_l)[0]
            uncertainty.append(dict(regime=regime,case=i,
                vf=vf,vl=vl,bf_nom=bf,bl_nom=bl,jf_nom=jf,jl_nom=jl,tau_nom=tau,
                bf_actual=af.decel,bl_actual=al.decel,jf_actual=af.jerk,jl_actual=al.jerk,tau_actual=af.delay,
                actual_gap_m=truth,nominal_gap_m=nom,bounded_gap_m=corner,
                nominal_shortfall_after_1m_margin=truth>nom+1.,
                bounded_shortfall_after_1m_margin=truth>corner+1.,
                bounded_extra_gap_m=corner-nom))
    write_csv(output/"uncertainty.csv",uncertainty)
    summary["uncertainty"]={"seed":241107,"n_each":5000,"margin_m":1.0,"regimes":{}}
    for regime in ["inside_declared_bounds","outside_declared_bounds"]:
        subset=[r for r in uncertainty if r["regime"]==regime]
        rec={}
        for method in ["nominal","bounded"]:
            failures=sum(r[method+"_shortfall_after_1m_margin"] for r in subset)
            rec[method]={"shortfalls":failures,"fraction":failures/len(subset),
                         "wilson95":wilson(failures,len(subset))}
        rec["mean_bounded_extra_gap_m"]=statistics.mean(r["bounded_extra_gap_m"] for r in subset)
        rec["p95_bounded_extra_gap_m"]=percentile([r["bounded_extra_gap_m"] for r in subset],.95)
        summary["uncertainty"]["regimes"][regime]=rec
    # Save an interpretable trajectory witness before making charts.
    witness=summary["endpoint_worst_case"]
    f=Profile(witness["follower_speed_mps"],witness["follower_decel_mps2"],witness["follower_jerk_mps3"],witness["follower_delay_s"])
    l=Profile(witness["leader_speed_mps"],witness["leader_decel_mps2"],witness["leader_jerk_mps3"])
    h=max(f.stop_time,l.stop_time)
    trajectory=[]
    for k in range(2001):
        t=k*h/2000;xf,vf=f.state(t);xl,vl=l.state(t)
        trajectory.append(dict(t_s=t,xf_m=xf,xl_m=xl,vf_mps=vf,vl_mps=vl,
                               closure_m=xf-xl,endpoint_plus_1m_gap_m=witness["endpoint_gap_m"]+1.-(xf-xl)))
    write_csv(output/"witness_trajectory.csv",trajectory)
    summary["runtime_environment"]={"python":sys.version,"platform":platform.platform(),
                                    "implementation":platform.python_implementation(),
                                    "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    figures(output,rows,uncertainty,trajectory,summary)
    print(json.dumps(summary,indent=2))


def figures(output,rows,uncertainty,trajectory,summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    ax.plot([r["t_s"] for r in trajectory],[r["closure_m"] for r in trajectory],color="#245778",label="Full trajectory closure")
    ax.axhline(summary["endpoint_worst_case"]["endpoint_gap_m"],color="#ae482e",ls="--",label="Endpoint-only envelope")
    ax.axhline(summary["endpoint_worst_case"]["full_gap_m"],color="#317156",ls=":",label="Maximum closure")
    ax.set(xlabel="Time after leader braking begins (s)",ylabel="Follower minus leader travel (m)")
    ax.legend(frameon=False,fontsize=9);fig.tight_layout();fig.savefig(output/"figure1_witness.png",dpi=220);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    data=np.zeros((3,3))
    for i,bf in enumerate([3.,6.,9.]):
        for j,bl in enumerate([3.,6.,9.]):
            ss=[r for r in rows if r["follower_decel_mps2"]==bf and r["leader_decel_mps2"]==bl]
            data[i,j]=100*sum(r["endpoint_shortfall_m"]>1 for r in ss)/len(ss)
    im=ax.imshow(data,cmap="Blues",vmin=0,vmax=100)
    for i in range(3):
        for j in range(3):
            ax.text(j,i,f"{data[i,j]:.1f}%",ha="center",va="center",color="white" if data[i,j]>50 else "#13232f")
    ax.set(xticks=[0,1,2],xticklabels=[3,6,9],yticks=[0,1,2],yticklabels=[3,6,9],
           xlabel="Leader braking cap (m/s²)",ylabel="Follower braking cap (m/s²)")
    fig.colorbar(im,ax=ax,label="Grid cases with endpoint shortfall > 1 m (%)")
    fig.tight_layout();fig.savefig(output/"figure2_cap_heatmap.png",dpi=220);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.5,3.5))
    labels=["Within declared bounds","Beyond declared bounds"]
    for k,method in enumerate(["nominal","bounded"]):
        means=[];low=[];high=[]
        for regime in ["inside_declared_bounds","outside_declared_bounds"]:
            rec=summary["uncertainty"]["regimes"][regime][method]
            means.append(rec["fraction"]*100)
            low.append((rec["fraction"]-rec["wilson95"][0])*100)
            high.append((rec["wilson95"][1]-rec["fraction"])*100)
        x=np.arange(2)+(k-.5)*.28
        ax.bar(x,means,.28,label=method.title(),color=["#ae482e","#245778"][k])
        ax.errorbar(x,means,yerr=[low,high],fmt="none",ecolor="#1b2730",capsize=3)
    ax.set(xticks=[0,1],xticklabels=labels,ylabel="Synthetic draws with > 1 m shortfall (%)",ylim=(0,105))
    ax.legend(frameon=False);fig.tight_layout();fig.savefig(output/"figure3_uncertainty.png",dpi=220);plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path(__file__).parent/"results")
    args=p.parse_args();main(args.output)
