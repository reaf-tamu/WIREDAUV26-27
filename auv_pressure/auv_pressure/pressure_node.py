#!/usr/bin/env python3
"""
Minimal driver for the Blue Robotics Bar02 pressure/depth sensor
(MS5837-02BA, I2C), using Blue Robotics' own official ms5837-python
library directly, installed via pip from GitHub -- not vendored as a git
submodule (that pattern caused real pain with ping_sonar_ros).

IMPORTANT: this node deliberately does NOT reimplement the sensor's
pressure/temperature calibration math -- that's exactly the kind of
manufacturer-provided, precision-critical code (calibration coefficients,
compensation formulas) that's safest to use as-is rather than
hand-transcribe. All of that lives inside the ms5837 library itself.

Publishes:
  /pressure/fluid_pressure   (sensor_msgs/FluidPressure) -- raw pressure
  /localization/depth_pose   (geometry_msgs/PoseWithCovarianceStamped)
    -- depth only (position.z), matching the pose0 placeholder already
    stubbed out (commented) in auv_localization/config/ekf.yaml. Wiring
    this sensor into the EKF later is just uncommenting those lines --
    no redesign needed.

NOTE on sign convention: position.z is set to NEGATIVE depth, consistent
with the ENU (z-up) convention already used elsewhere in this stack (see
docs/concepts/euler-quaternions.md and the VN-100's use_enu setting) --
underwater should be a negative z relative to a surface origin. This has
NOT been empirically verified against real EKF behavior yet; treat it as
a documented assumption to confirm once this is actually wired into
ekf.yaml, not a settled fact.

NOTE on covariance: the depth variance below is a placeholder starting
value, not measured from real sensor noise -- same situation as the
VN-100's initial orientation_covariance values. Tune once real data is
available.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import FluidPressure
from geometry_msgs.msg import PoseWithCovarianceStamped

try:
    import ms5837
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class PressureNode(Node):
    def __init__(self):
        super().__init__('pressure_node')

        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('frame_id', 'pressure_sensor')
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('fluid_density_kg_m3', 997.0)  # freshwater (pool) -- library default
        # Placeholder -- see module docstring. Units: meters^2.
        self.declare_parameter('depth_variance', 0.01)

        self.frame_id = self.get_parameter('frame_id').value
        self.depth_variance = self.get_parameter('depth_variance').value
        rate_hz = self.get_parameter('rate_hz').value

        self.pressure_pub = self.create_publisher(
            FluidPressure, '/pressure/fluid_pressure', qos_profile_sensor_data)
        self.depth_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/localization/depth_pose', qos_profile_sensor_data)

        self.good_reads = 0
        self.bad_reads = 0

        self.sensor = None
        if not HARDWARE_AVAILABLE:
            self.get_logger().warn(
                "ms5837 library not installed -- run: "
                "pip3 install git+https://github.com/bluerobotics/ms5837-python.git "
                "(commands will be logged, nothing published)")
        else:
            bus = self.get_parameter('i2c_bus').value
            self.get_logger().info(f'Connecting to Bar02 on I2C bus {bus}')
            self.sensor = ms5837.MS5837_02BA(bus)
            if not self.sensor.init():
                self.get_logger().error(
                    'Failed to initialize Bar02 -- check wiring/I2C address (0x76) '
                    'and that i2cdetect sees it. Node will keep retrying.')
                self.sensor = None
            else:
                self.sensor.setFluidDensity(
                    self.get_parameter('fluid_density_kg_m3').value)

        self.timer = self.create_timer(1.0 / rate_hz, self.read_loop)

    def read_loop(self):
        if self.sensor is None:
            if HARDWARE_AVAILABLE:
                bus = self.get_parameter('i2c_bus').value
                self.sensor = ms5837.MS5837_02BA(bus)
                if not self.sensor.init():
                    self.sensor = None
                else:
                    self.sensor.setFluidDensity(
                        self.get_parameter('fluid_density_kg_m3').value)
            return

        if not self.sensor.read():
            self.bad_reads += 1
            return

        self.good_reads += 1
        now = self.get_clock().now().to_msg()

        pressure_msg = FluidPressure()
        pressure_msg.header.stamp = now
        pressure_msg.header.frame_id = self.frame_id
        pressure_msg.fluid_pressure = self.sensor.pressure(ms5837.UNITS_Pa)
        pressure_msg.variance = 0.0  # not characterized yet
        self.pressure_pub.publish(pressure_msg)

        depth_m = self.sensor.depth()  # library's own depth() -- uses its calibration + fluid density

        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp = now
        pose_msg.header.frame_id = self.frame_id
        pose_msg.pose.pose.position.z = -depth_m  # ENU: underwater = negative z, see docstring
        pose_msg.pose.covariance[14] = self.depth_variance  # z-z diagonal (row-major 6x6)
        self.depth_pose_pub.publish(pose_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PressureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(
            f'Shutting down. Good reads: {node.good_reads}, bad reads: {node.bad_reads}'
        )
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
