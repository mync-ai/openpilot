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

    commands = ['NEUTRAL', 'FORWARD', 'BACK', 'MILD_LEFT', 'MILD_RIGHT', 'HARD_LEFT', 'HARD_RIGHT']
    events = ['STOP', 'ACCELERATE', 'TURN', 'CURVE']

    def __init__(self, turn_thresh_1=1.5, turn_thresh_2=5.0, long_thresh=2.0, smoothing_window=3):
        self.accelX_pred = []
        self.accelY_pred = []
        self.velX_pred = []
        self.velY_pred = []
        self.kinetime = []
        self.accel = 0
        self.vel = 0
        self.stopped = True
        self.state = self.NEUTRAL
        self.last_event = 'None'
        self.turn_thr1 = turn_thresh_1
        self.turn_thr2 = turn_thresh_2
        self.long_thr = long_thresh
        self.lft_blnk = 0
        self.rght_blnk = 0
        self.preds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.smoothing_window = smoothing_window
        self.update_state()

    def set_data(self, new_data):
        self.kinetime = new_data['acceleration_pred'].t
        ind_3s = next((i for i, t in enumerate(self.kinetime) if t > 3), len(self.kinetime))
        self.accelX_pred = [new_data['acceleration_pred'].x[i] for i in range(min(ind_3s, len(new_data['acceleration_pred'].x)))]
        self.accelY_pred = [new_data['acceleration_pred'].y[i] for i in range(min(ind_3s, len(new_data['acceleration_pred'].y)))]
        self.velX_pred = [new_data['velocity_pred'].x[i] for i in range(min(ind_3s, len(new_data['velocity_pred'].x)))]
        self.velY_pred = [new_data['velocity_pred'].y[i] for i in range(min(ind_3s, len(new_data['velocity_pred'].y)))]

        self.lft_blnk = new_data['left_blinker']
        self.rght_blnk = new_data['right_blinker']
        self.vel = new_data['vEgo']
        self.accel = new_data['aEgo']

        self.update_state()

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
        minX = min(self.accelX_pred)
        if minX < -self.long_thr:
            return self.BACK
        return self.NEUTRAL

    def accelerate(self):
        maxX = max(self.accelX_pred)
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
