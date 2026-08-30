# PID Control

## The problem it solves

Say you want the vehicle to hold 1 meter of depth. You know your current depth (thanks to the EKF), and you know the target. The gap between them — target minus current — is called the **error**. A PID controller's whole job is: given this error, right now, how hard should the thrusters push?

It does this continuously, many times a second: measure the error, compute an output, apply it, measure the new error, repeat. This is called a **closed-loop** or **feedback** controller — it constantly corrects itself based on what's actually happening, rather than just guessing once and hoping.

## The three terms, and what each one actually brings

The name says it all: **P**roportional, **I**ntegral, **D**erivative. Each term looks at the error a different way, and each fixes a different problem the others can't.

### P — Proportional: react to how wrong you are *right now*

```
P_output = Kp * error
```

The bigger the error, the bigger the correction. Simple, and it's doing most of the work most of the time — if you're 50cm off target depth, push harder than if you're 5cm off.

**What P alone can't do:** it can never fully close the gap. Think about it — as the error shrinks, P's output shrinks right along with it. Near the target, the correction becomes tiny... but gravity, buoyancy, current, and friction don't shrink to match. The vehicle settles into an equilibrium *short* of the actual target, where the small remaining P output exactly balances out those constant real-world forces. This permanent leftover error is called **steady-state error**, and it's the single biggest reason P alone usually isn't good enough.

### I — Integral: react to how wrong you've *been*

```
I_output = Ki * (running sum of error over time)
```

The integral term keeps a running total of error over time. If the vehicle has been sitting slightly below target depth for the last few seconds, that error keeps accumulating, and the integral term keeps growing — pushing harder and harder until it finally forces the steady-state error to zero.

This is I's whole purpose: **it's the fix for the exact gap P alone leaves behind.**

**The catch — integral windup:** because I keeps accumulating for as long as error exists, it can build up to a huge value if the vehicle is *far* from target for an extended stretch (e.g. right after a big setpoint change, or while a thruster is temporarily maxed out and physically can't respond faster). When the vehicle finally reaches the target, that huge accumulated sum doesn't vanish instantly — it has to "unwind," causing the vehicle to badly overshoot past the target before settling. This is a common, well-known failure mode, usually fixed by **clamping** the integral term to some maximum magnitude ("anti-windup") so it can't build up an unreasonably large correction.

### D — Derivative: react to how fast the error is *changing*

```
D_output = Kd * (rate of change of error)
```

The derivative term looks at *how quickly* the error is closing. If the vehicle is approaching the target depth fast, D produces a large *negative* contribution — acting as a brake, damping the approach before P and I cause an overshoot.

This is D's whole purpose: **it's damping, fighting the overshoot/oscillation that P (and especially I) tend to cause.**

**The catch — noise sensitivity:** derivative is a rate of change, and rates of change amplify noise badly. If your sensor reading jitters even slightly from sample to sample, the derivative term can spike wildly, injecting jittery, aggressive corrections into an otherwise smooth control loop. This is why D is the term most often left out entirely, or run through a low-pass filter before use.

## Putting it together

```
output = Kp*error + Ki*(sum of error) + Kd*(rate of change of error)
```

Each term is covering for what the others are bad at:
- P gets you *most* of the way there, fast, but leaves a residual gap.
- I closes that residual gap completely, but overshoots if left unchecked.
- D dampens the overshoot that P and I cause, at the cost of noise sensitivity.

None of them alone is a complete solution — that's the entire reason all three commonly get combined.

## When you might only need PI (or just P)

Using all three terms isn't automatic — it depends on the system:

- **Drop D when your sensor is noisy relative to how fast the system actually moves.** If derivative noise would inject more garbage than the damping is worth, PI is often the more stable, practical choice — many real industrial controllers run PI-only for exactly this reason.
- **Drop D when the system is naturally damped already.** Some physical systems have enough friction/drag/inertia built in that they don't overshoot much on their own — D would be solving a problem that barely exists.
- **Drop I too (P-only, or P with very weak I) when steady-state error doesn't matter much,** or when the system is fast enough and disturbances small enough that "close enough" is fine without eliminating the last bit of drift.
- **Keep all three** when you need to both eliminate steady-state error *and* control overshoot precisely, and your sensor data is clean enough that derivative noise isn't a real problem.

A practical way to think about it: start with P alone and get the response roughly reasonable, add I only if you see a persistent, un-closing gap, and add D only if you're seeing overshoot/oscillation that I made worse. Adding terms you don't need just adds tuning complexity and more ways for the loop to misbehave.

## Setpoints, error, and a few other terms worth knowing

- **Setpoint** — the target value you want (e.g. desired depth, desired heading).
- **Process variable** — the actual current measured value (e.g. current depth from the EKF).
- **Error** — setpoint minus process variable. This is the only input a PID controller ever sees; it has no idea *why* the error exists, only that it does.
- **Control effort / control output** — what the PID controller produces, which then gets sent to an actuator (in our case, ultimately to the thrusters via the allocation matrix).
- **Tuning** — picking Kp, Ki, Kd. There's no universal formula that works for every system; it's usually done empirically (adjust, test, repeat), sometimes guided by more formal methods like Ziegler–Nichols as a starting point.
- **Oscillation** — the output overshooting, undershooting, overshooting the other way, etc., before settling. Usually a sign Kp or Ki is too aggressive relative to Kd.

## How this works in ROS2

PID isn't something ROS2 gives you "for free" as a service — it's a fairly small, self-contained piece of math that individual packages implement or bring in as a small library. The most common one is [`control_toolbox`](https://github.com/ros-controls/control_toolbox)'s `Pid` class, part of the broader `ros2_control` ecosystem — it handles the P/I/D math, integral clamping, and derivative filtering described above, so individual controller nodes don't have to reimplement that logic from scratch.

Regardless of the exact library, the shape of a PID node in ROS2 is generally the same: subscribe to whatever gives the current process variable (for us, `/odometry/filtered` from the EKF), subscribe to whatever gives the setpoint, compute the PID output every time a new state estimate arrives, and publish that output — either directly to something an actuator listens to, or to an intermediate topic that a downstream node (like thruster allocation) consumes.

## How we use it in the club

Once `auv_control` is built out, it'll run **6 independent PID loops** — one each for roll, pitch, yaw, depth, surge, and sway. Every one of them reads the fused state from `/odometry/filtered` (the EKF's output — see `docs/concepts/kalman-filter.md`) and a target from `auv_msgs/Setpoint`, and produces a correction for its one axis.

Those 6 corrections get combined into a single wrench (net force + torque) and passed through the thruster allocation matrix, which converts that wrench into individual thruster commands for our 8-thruster layout.

We don't yet know which axes will need all three terms versus just PI — that's exactly the kind of thing that gets decided empirically once we're bench-testing the real vehicle in stage 3 of the roadmap, not something to guess at now. A reasonable expectation going in: depth (fighting a fairly constant, predictable buoyancy offset) is a likely candidate for needing a real I term to eliminate steady-state error, while an axis like yaw might turn out fine with less integral action if there's no comparable constant disturbance pushing on it.

## Resources to learn more

- **[Improving the Beginner's PID](http://brettbeauregard.com/blog/2011/04/improving-the-beginners-pid-introduction/)** — a fantastic, very readable series walking from the naive textbook PID equation up to a robust, production-quality implementation, covering exactly the windup and derivative-noise issues discussed above.
- **[PID controller — Wikipedia](https://en.wikipedia.org/wiki/PID_controller)** — solid reference for the formal definitions, block diagrams, and tuning methods like Ziegler–Nichols.
- **[`control_toolbox` (ros-controls)](https://github.com/ros-controls/control_toolbox)** — the actual PID implementation commonly used across the ROS2 ecosystem, including anti-windup handling.
