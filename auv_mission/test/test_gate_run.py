"""Tests for the December gate run. No ROS needed:  python3 -m pytest auv_mission/test"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from auv_mission.gate_run import GateRun, GateRunParams  # noqa: E402

DT = 0.1


def run(mission, depth_fn, until, yaw=0.3, start_at=1.0, odom=True):
    """Tick the mission with a fake depth profile. Returns the list of states."""
    states = []
    t = 0.0
    while t <= until:
        if odom:
            mission.sensor_update(t)
        cmd = mission.step(t, depth_fn(t), yaw, start=t >= start_at)
        states.append((round(t, 2), cmd))
        t += DT
    return states


def first_time(states, name):
    return next((t for t, c in states if c.state == name), None)


def test_full_run_order_and_commands():
    m = GateRun(GateRunParams(drive_time_s=10, surface_time_s=5))
    # robot reaches 1 m at t = 6 s and stays there
    s = run(m, lambda t: min(1.0, max(0.0, (t - 1) / 5)), until=40)
    order = []
    for _, c in s:
        if not order or order[-1] != c.state:
            order.append(c.state)
    assert order == ['WAIT', 'DIVE', 'DRIVE', 'SURFACE', 'DONE']
    drive = [c for _, c in s if c.state == 'DRIVE']
    assert all(c.depth_m == 1.0 and c.surge == 0.25 for c in drive)
    assert all(c.surge == 0.0 for _, c in s if c.state != 'DRIVE')
    # drive lasts drive_time_s
    t_drive, t_surface = first_time(s, 'DRIVE'), first_time(s, 'SURFACE')
    assert abs((t_surface - t_drive) - 10) < 0.15


def test_holds_heading_from_when_it_started():
    m = GateRun()
    yaws = iter([0.1] * 5 + [0.7] * 1000)   # robot is pointed at 0.1 rad, then drifts
    t = 0.0
    cmd = None
    for k in range(200):
        m.sensor_update(t)
        cmd = m.step(t, 0.5, next(yaws), start=k >= 4)
        t += DT
    assert math.isclose(cmd.yaw_rad, 0.1)


def test_waits_for_settle_before_driving():
    m = GateRun(GateRunParams(depth_settle_s=3))
    # bounces through 1 m without staying there
    s = run(m, lambda t: 1.0 + 0.4 * math.sin(2 * t), until=20)
    assert first_time(s, 'DRIVE') is None


def test_aborts_if_it_cannot_reach_depth():
    m = GateRun(GateRunParams(dive_timeout_s=10))
    s = run(m, lambda t: 0.2, until=20)          # stuck near the surface
    assert first_time(s, 'ABORT') is not None
    assert m.reason == 'could not reach depth'
    assert s[-1][1].depth_m == 0.0 and s[-1][1].surge == 0.0


def test_aborts_on_lost_odometry():
    m = GateRun(GateRunParams(drive_time_s=30))
    t = 0.0
    cmd = None
    while t < 20:
        if t < 12:                       # odometry stops at 12 s
            m.sensor_update(t)
        cmd = m.step(t, min(1.0, t / 3), 0.0, start=t >= 1)
        t += DT
    assert cmd.state == 'ABORT' and m.reason == 'lost odometry'


def test_whole_mission_timeout():
    m = GateRun(GateRunParams(drive_time_s=500, mission_timeout_s=60))
    s = run(m, lambda t: 1.0 if t > 2 else 0.0, until=80)
    assert m.reason == 'mission took too long'
    assert 60 <= first_time(s, 'ABORT') - 1.0 <= 60.2


def test_never_moves_before_start():
    m = GateRun()
    s = run(m, lambda t: 0.0, until=30, start_at=1e9)
    assert all(c.state == 'WAIT' and c.depth_m == 0.0 and c.surge == 0.0 for _, c in s)
