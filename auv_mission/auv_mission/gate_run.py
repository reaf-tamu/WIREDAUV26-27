"""
gate_run.py -- the December pre-qual try, as a plain-Python state machine.

No ROS in this file, so it can be tested on any laptop (see test/test_gate_run.py).
mission_node.py wraps it in a ROS 2 node.

The run:
    WAIT     at the surface, holding the heading we started with
    DIVE     go down to target depth, hold heading
    DRIVE    hold depth + heading, push forward for a set time (through the gate)
    SURFACE  stop pushing forward, come back up
    DONE     stay at the surface with zero forward push

Anything that goes wrong (a step takes too long, the whole run takes too long,
or we stop hearing from the sensors) goes to ABORT, which does the same thing
as SURFACE.

Units: depth is meters BELOW the surface (1.0 = one meter down). The ROS node
turns it into the z = -depth that the pressure sensor and EKF use.
"""

from dataclasses import dataclass, field


WAIT, DIVE, DRIVE, SURFACE, DONE, ABORT = (
    'WAIT', 'DIVE', 'DRIVE', 'SURFACE', 'DONE', 'ABORT')


@dataclass
class GateRunParams:
    target_depth_m: float = 1.0      # SYS-015: gate pass at 1 m depth
    depth_tolerance_m: float = 0.15  # "at depth" means within this much
    depth_settle_s: float = 3.0      # ...for this long, so we don't leave while bouncing
    dive_timeout_s: float = 40.0     # give up if we can't reach depth
    surge_cmd: float = 0.25          # forward command sent to the controller
    drive_time_s: float = 25.0       # how long to push forward (tune at the pool)
    surface_depth_m: float = 0.0
    surface_time_s: float = 15.0     # how long SURFACE lasts before DONE
    mission_timeout_s: float = 120.0  # whole run, from start
    sensor_timeout_s: float = 1.0    # no odometry for this long -> ABORT


@dataclass
class Command:
    state: str
    depth_m: float      # meters below the surface
    yaw_rad: float      # heading to hold
    surge: float        # forward command (0 = none)


@dataclass
class GateRun:
    p: GateRunParams = field(default_factory=GateRunParams)
    state: str = WAIT
    reason: str = ''
    _hold_yaw: float = None
    _t_start: float = None
    _t_state: float = 0.0
    _t_at_depth: float = None
    _t_last_sensor: float = None

    # ---- inputs -------------------------------------------------------
    def sensor_update(self, t):
        """Call whenever fresh odometry arrives."""
        self._t_last_sensor = t

    def _go(self, new_state, t, reason=''):
        self.state = new_state
        self._t_state = t
        self._t_at_depth = None
        if reason:
            self.reason = reason

    # ---- the state machine -------------------------------------------
    def step(self, t, depth_m, yaw_rad, start=False):
        """Advance one tick. Returns the Command to send to the controllers.

        t        seconds (any clock, as long as it only goes forward)
        depth_m  current depth, meters below the surface
        yaw_rad  current heading
        start    True once the mission switch (or start timer) says go
        """
        p = self.p
        in_state = t - self._t_state

        if self.state == WAIT:
            # Remember the heading every tick until we start, so the run goes
            # whichever way the robot was pointed when it was let go.
            self._hold_yaw = yaw_rad
            if start:
                self._t_start = t
                self._t_last_sensor = t if self._t_last_sensor is None else self._t_last_sensor
                self._go(DIVE, t)
                in_state = 0.0

        # Checks that apply to every active state
        if self.state in (DIVE, DRIVE, SURFACE):
            if self._t_last_sensor is None or t - self._t_last_sensor > p.sensor_timeout_s:
                self._go(ABORT, t, 'lost odometry')
            elif t - self._t_start > p.mission_timeout_s:
                self._go(ABORT, t, 'mission took too long')

        if self.state == DIVE:
            if abs(depth_m - p.target_depth_m) <= p.depth_tolerance_m:
                if self._t_at_depth is None:
                    self._t_at_depth = t
                if t - self._t_at_depth >= p.depth_settle_s:
                    self._go(DRIVE, t)
            else:
                self._t_at_depth = None
                if in_state > p.dive_timeout_s:
                    self._go(ABORT, t, 'could not reach depth')

        elif self.state == DRIVE:
            if in_state >= p.drive_time_s:
                self._go(SURFACE, t)

        elif self.state in (SURFACE, ABORT):
            if self.state == SURFACE and in_state >= p.surface_time_s:
                self._go(DONE, t)

        return self.command()

    def command(self):
        p = self.p
        yaw = self._hold_yaw if self._hold_yaw is not None else 0.0
        if self.state in (DIVE,):
            return Command(self.state, p.target_depth_m, yaw, 0.0)
        if self.state == DRIVE:
            return Command(self.state, p.target_depth_m, yaw, p.surge_cmd)
        # WAIT, SURFACE, DONE, ABORT: at the surface, no forward push
        return Command(self.state, p.surface_depth_m, yaw, 0.0)
