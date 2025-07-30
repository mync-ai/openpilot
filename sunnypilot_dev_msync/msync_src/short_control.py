class Decider:
    """
    This class implements the short-term decision-making process.
    It uses the model predictions from the openpilot module
    to make future seat actuator commands.
    """
    NEUTRAL = 0
    FORWARD = 1
    BACK = 2
    MILD_LEFT = 3
    MILD_RIGHT = 4
    HARD_LEFT = 5
    HARD_RIGHT = 6

    PLAN_TIME = [0.0, 0.156, 0.312, 0.468, 0.625, 0.781, 0.937, 1.093, 1.25, 1.406, 1.562, 1.718, 1.875, 2.031, 2.187, 2.343, 2.5]
    PRED_TIME = [0, 0.009, 0.039, 0.087, 0.156, 0.244, 0.351, 0.478, 0.625, 0.791, 0.976, 1.181, 1.406, 1.650, 1.914, 2.197, 2.5,
                 2.822, 3.164, 3.525, 3.906, 4.306, 4.726, 5.166, 5.625, 6.103, 6.601, 7.119, 7.656, 8.212, 8.789, 9.384, 10]

    commands = ['NEUTRAL', 'FORWARD', 'BACK', 'MILD_LEFT', 'MILD_RIGHT', 'HARD_LEFT', 'HARD_RIGHT']
    events = ['STOP', 'ACCELERATE', 'TURN', 'CURVE']

    def __init__(self, turn_thresh_1=1.5, turn_thresh_2=5.0, long_thresh=2.0, smoothing_window=3, horizon=3.0, use_plan=False):
        self.accelX_pred = []
        self.accelY_pred = []
        self.velX_pred = []
        self.velY_pred = []
        self.long_plan = []
        self.accel_plan = []
        self.vel_plan = []
        self.kinetime = []
        self.accel = 0
        self.vel = 0
        self.stopped = True
        self.state = self.NEUTRAL
        self.last_event = 'None'
        self.use_plan = use_plan
        self.turn_thr1 = turn_thresh_1
        self.turn_thr2 = turn_thresh_2
        self.long_thr = long_thresh
        self.lft_blnk = 0
        self.rght_blnk = 0
        self.preds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.smoothing_window = smoothing_window
        self.horizon = horizon
        self.update_state()
        self.ind_pred = self.compute_horizon_indices(self.PRED_TIME)
        self.ind_plan = self.compute_horizon_indices(self.PLAN_TIME)

    def compute_horizon_indices(self, time_vec):
        """
        Compute the index in the time vector where the time first exceeds the specified horizon.

        Args:
            time_vec (list or array-like): Sequence of time values.

        Returns:
            int: Index of the first element in time_vec greater than self.horizon. If none, returns the length of time_vec.
        """

        # Find index where time exceeds horizon for predictions
        indices = next((i for i, t in enumerate(time_vec) if t > self.horizon), len(time_vec))

        # For now, use same horizon for plan data - could be different in future

        return indices

    def set_data(self, new_data):
        self.accelX_pred = [new_data['acceleration_pred'].x[i] for i in range(min(self.ind_pred, len(new_data['acceleration_pred'].x)))]
        self.accelY_pred = [new_data['acceleration_pred'].y[i] for i in range(min(self.ind_pred, len(new_data['acceleration_pred'].y)))]
        self.velX_pred = [new_data['velocity_pred'].x[i] for i in range(min(self.ind_pred, len(new_data['velocity_pred'].x)))]
        self.velY_pred = [new_data['velocity_pred'].y[i] for i in range(min(self.ind_pred, len(new_data['velocity_pred'].y)))]

        self.accelX_plan = [new_data['acceleration_plan'].x[i] for i in range(min(self.ind_plan, len(new_data['acceleration_plan'].x)))]
        self.velX_plan = [new_data['velocity_plan'].x[i] for i in range(min(self.ind_plan, len(new_data['velocity_plan'].x)))]

        # Extend X_plan vectors if horizon exceeds 2.5 seconds
        self.extend_plan(new_data)

        self.lft_blnk = new_data['left_blinker']
        self.rght_blnk = new_data['right_blinker']
        self.vel = new_data['vEgo']
        self.accel = new_data['aEgo']

        self.update_state()

    def extend_plan(self, new_data):
        """
        Extend X_plan vectors beyond 2.5 seconds using prediction data when horizon > 2.5s.

        Combines plan data (first 2.5s) with prediction data (remaining time) to fill
        the extended horizon period.
        """
        if self.horizon <= 2.5:
            return

        # Calculate how many additional elements we need from prediction data
        additional_elements = self.ind_pred - self.ind_plan

        if additional_elements > 0:
            # Get the additional prediction elements starting from plan length
            pred_start_idx = self.ind_plan
            pred_end_idx = min(pred_start_idx + additional_elements, len(new_data['acceleration_pred'].x))

            # Extend accelX_plan with prediction data
            additional_accelX = [new_data['acceleration_pred'].x[i] for i in range(pred_start_idx, pred_end_idx)]
            self.accelX_plan.extend(additional_accelX)

            # Extend velX_plan with prediction data
            additional_velX = [new_data['velocity_pred'].x[i] for i in range(pred_start_idx, min(pred_start_idx + additional_elements, len(new_data['velocity_pred'].x)))]
            self.velX_plan.extend(additional_velX)

    def update_state(self, decision=-1):
        """
        Updates the stopped/driving status based on ego motion.
        """
        # Consider vehicle stopped if velocity is very low (0.05 m/s ≈ 0.18 km/h)
        if self.vel > 0.05:
            self.stopped = False
        else:
            self.stopped = True

        # Add new decision to the prediction history for smoothing
        if decision > -1:
            self.preds.pop(0)  # Remove oldest decision
            self.preds.append(decision)  # Add newest decision

        # Return True only if last smoothing_window decisions are identical (temporal smoothing)
        if len(self.preds) < self.smoothing_window:
            return False
        return all(self.preds[-i] == self.preds[-1] for i in range(1, self.smoothing_window + 1))

    def get_x_vectors(self):
        """
        Returns the appropriate X-direction vectors based on use_plan setting.

        Returns:
            tuple: (accelX, velX) - either prediction or plan vectors
        """
        if self.use_plan:
            return self.accelX_plan, self.velX_plan
        else:
            return self.accelX_pred, self.velX_pred

    def curve(self):
        maxY = max(self.accelY_pred)
        minY = min(self.accelY_pred)
        if self.stopped:
            return self.NEUTRAL

        # Check for hard turns (high lateral acceleration thresholds)
        hard_right = maxY > self.turn_thr2
        hard_left = minY < -self.turn_thr2

        # Check for mild turns (moderate lateral acceleration thresholds)
        mild_right = maxY > self.turn_thr1
        mild_left = minY < -self.turn_thr1

        # Handle conflicting turn signals (both left and right detected)
        # This can happen during lane changes or S-curves
        if (hard_right and hard_left) or (mild_right and mild_left):
            # Get 1-second window of acceleration data to determine predominant direction
            ind_1s = next((i for i, t in enumerate(self.kinetime) if t > 1), len(self.kinetime))
            accelY_1s = [self.accelY_pred[i] for i in range(min(ind_1s, len(self.accelY_pred)))]

            # Calculate average acceleration over 1 second to resolve direction
            avg_accel_1s = sum(accelY_1s) / len(accelY_1s) if accelY_1s else 0

            # Determine direction based on average acceleration
            if avg_accel_1s > 0:  # More right acceleration
                if hard_right:
                    return self.HARD_RIGHT
                elif mild_right:
                    return self.MILD_RIGHT
            else:  # More left acceleration
                if hard_left:
                    return self.HARD_LEFT
                elif mild_left:
                    return self.MILD_LEFT

        # Original logic for single-direction cases (no conflict)
        if maxY > self.turn_thr2:
            return self.HARD_RIGHT
        elif maxY > self.turn_thr1:
            return self.MILD_RIGHT
        if minY < -self.turn_thr2:
            return self.HARD_LEFT
        elif minY < -self.turn_thr1:
            return self.MILD_LEFT
        return self.NEUTRAL

    def turn(self):
        maxY = max(self.accelY_pred)
        minY = min(self.accelY_pred)
        if self.stopped:
            return self.NEUTRAL

        # Only activate turn commands when driver signals intent via blinkers
        if self.rght_blnk:
            if maxY > self.turn_thr2:
                return self.HARD_RIGHT
            elif maxY > self.turn_thr1:
                return self.MILD_RIGHT

        elif self.lft_blnk:
            if minY < -self.turn_thr2:
                return self.HARD_LEFT
            elif minY < -self.turn_thr1:
                return self.MILD_LEFT

        return self.NEUTRAL

    def stop(self):
        if self.stopped:
            return self.NEUTRAL
        accelX, _ = self.get_x_vectors()
        minX = min(accelX)
        if minX < -self.long_thr:
            return self.BACK
        return self.NEUTRAL

    def accelerate(self):
        accelX, _ = self.get_x_vectors()
        maxX = max(accelX)
        if maxX > self.long_thr:
            if self.stopped:
                # Special case: if accelerating from stop with turn signal,
                # prepare for directional movement
                if self.lft_blnk:
                    return self.MILD_LEFT
                if self.rght_blnk:
                    return self.MILD_RIGHT
            else:
                # Normal forward acceleration while moving
                return self.FORWARD
        return self.NEUTRAL

    def short_decision(self):
        """
        Makes a short-term control decision by evaluating multiple driving maneuvers.

        Evaluates four types of driving decisions (stop, accelerate, turn, curve) and
        selects the one with the highest priority/confidence score. Updates the internal
        state based on the decision and returns the corresponding command and source.

        Returns:
            tuple: A tuple containing:
                - command: The control command corresponding to the selected decision
                - source: String identifying which decision type was selected or last event

        Note:
            - Compares decisions from stop(), accelerate(), turn(), and curve() methods
            - Updates internal state if decision validation passes via update_state()
            - Falls back to last_event if state update fails
        """
        decision = 0
        source = 'None'
        sub_decisions = [0, 0, 0, 0]
        sub_decisions[0] = self.stop()
        sub_decisions[1] = self.accelerate()
        sub_decisions[2] = self.turn()
        sub_decisions[3] = self.curve()
        prediction = self.state

        for i, d in enumerate(sub_decisions):
            if d > decision:
                decision = d
                source = self.events[i]

        if (self.update_state(decision=decision)):
            prediction = decision
            self.last_event = source
        else:
            source = self.last_event

        self.state = prediction

        return self.commands[prediction], source
