from typing import Optional

import simple_pid


class Controller:
    """This class wraps an internal PID controller.

    This class is used to control the drone's descent."""

    def __init__(
            self,
            kp: float = 0,
            ki: float = 0,
            kd: float = 0,
            target: float = 0,
            upper_limit: float = 0,
            lower_limit: float = 0,
            update_rate: float = 0,
            scalar: float = 0):
        """
        :param kp: The proportional coefficient of the PID
        :param ki: The integral coefficient of the PID
        :param kd: The derivative coefficient of the PID
        :param target: The initial target value which the PID will approach
        :param upper_limit: The largest value which the PID should output
        :param lower_limit: The smallest value which the PID should output
        :param update_rate: The (approximate) time in seconds between each call to enable.
        :param scalar: A value to offset the result of each update by."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.target = target
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.update_rate = update_rate
        self.scalar = scalar
        self.pid = simple_pid.PID(
            Kp=self.kp,
            Ki=self.ki,
            Kd=self.kd,
            setpoint=self.target,
            output_limits=(self.lower_limit, self.upper_limit),
            sample_time=self.update_rate,
            auto_mode=False)

    def enable(
            self,
            l_output: Optional[float] = None):
        """Start the pid controller, with an optional last output of the
        previous controller.

        This function is used to transition from another controller to
        this PID controller. It must be called before the update method."""
        self.pid.set_auto_mode(True, last_output=l_output)

    def update(
            self,
            input: float) -> float:
        """Feed a new input value into the controller.

        Be sure to call the enable method prior to this method.

        :param input: The new input value"""
        output = self.pid(input) + self.scalar
        return output

    def set_target(
            self,
            new_target: float):
        """Set the target value for the pid.

        :param new_target: The new target value"""
        self.target = new_target
        self.pid.setpoint = self.target

    def reset(self):
        """Reset the PID's values to all zeros.

        Useful for eliminating integral windup."""
        self.pid.reset()
