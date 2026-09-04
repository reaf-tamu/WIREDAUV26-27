"""Minimal, self-contained PID controller.

See docs/concepts/pid-control.md for what each term does conceptually.
Includes integral clamping (anti-windup) since that's a known real risk
once a loop saturates against thruster limits.
"""


class PID:
    def __init__(self, kp, ki, kd, output_limits=(-1.0, 1.0), integral_limits=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min, self.output_max = output_limits
        if integral_limits is None:
            integral_limits = output_limits
        self.integral_min, self.integral_max = integral_limits

        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        """Call when a setpoint changes abruptly or the loop re-enables --
        prevents a stale integral/derivative from causing a sudden kick."""
        self._integral = 0.0
        self._prev_error = None

    def update(self, setpoint, measurement, dt):
        if dt <= 0.0:
            return 0.0

        error = setpoint - measurement

        p_term = self.kp * error

        self._integral += error * dt
        self._integral = max(self.integral_min, min(self.integral_max, self._integral))
        i_term = self.ki * self._integral

        if self._prev_error is None:
            d_term = 0.0
        else:
            d_term = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        output = p_term + i_term + d_term
        return max(self.output_min, min(self.output_max, output))
