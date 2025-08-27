from collections import deque


class Decider:
    """Seat short-term decision engine.

    Step 1 refactor: Lateral (left/right) and longitudinal (forward/back) decisions
    are computed independently and returned together. Each domain has its own
    temporal smoothing window.

    External API change (staged): short_decision() now returns a tuple:
        (lateral_command: str, longitudinal_command: str)

    Commands are still expressed as strings from the original combined command
    list for backward familiarity, but the two axes no longer overwrite each other.
    """

    # Original combined enumerations (kept for continuity of string labels)
    NEUTRAL = 0
    FORWARD = 1
    BACK = 2
    MILD_LEFT = 3
    MILD_RIGHT = 4
    HARD_LEFT = 5
    HARD_RIGHT = 6

    # Time vectors (comma.ai formatted) - prediction horizon & plan horizon
    PLAN_TIME = [0.0, 0.156, 0.312, 0.468, 0.625, 0.781, 0.937, 1.093, 1.25, 1.406, 1.562, 1.718, 1.875, 2.031, 2.187, 2.343, 2.5]
    PRED_TIME = [0, 0.009, 0.039, 0.087, 0.156, 0.244, 0.351, 0.478, 0.625, 0.791, 0.976, 1.181, 1.406, 1.650, 1.914, 2.197, 2.5,
                 2.822, 3.164, 3.525, 3.906, 4.306, 4.726, 5.166, 5.625, 6.103, 6.601, 7.119, 7.656, 8.212, 8.789, 9.384, 10]

    commands = ['NEUTRAL', 'FORWARD', 'BACK', 'MILD_LEFT', 'MILD_RIGHT', 'HARD_LEFT', 'HARD_RIGHT']

    def __init__(self, *, turn_thresh_1=1.0, turn_thresh_2=2.0,
                 accel_thresh=1.0, decel_thresh=1.0,
                 long_sens=5, lat_sens=5,
                 long_sticky=3, lat_sticky=3,
                 horizon=3.0, use_plan=True):
        # Prediction buffers
        self.accelX_pred = []
        self.accelY_pred = []
        self.velX_pred = []
        self.velY_pred = []
        # Plan buffers (optional)
        self.accelX_plan = []
        self.velX_plan = []
        self.kinetime = []  # time stamps aligned with accelY_pred subset

        # Ego state
        self.accel = 0.0
        self.vel = 0.0
        self.stopped = True

        # Thresholds / parameters
        self.use_plan = use_plan
        self.turn_thr1 = turn_thresh_1
        self.turn_thr2 = turn_thresh_2
        self.accel_thr = accel_thresh
        self.decel_thr = decel_thresh
        self.long_smooth = max(1, int(long_sens))
        self.lat_smooth = max(1, int(lat_sens))
        self.long_sticky = max(1, int(long_sticky))
        self.lat_sticky = max(1, int(lat_sticky))
        self.horizon = horizon

        # Signals
        self.lft_blnk = 0
        self.rght_blnk = 0
        self.gear = 'drive'

        # Independent domain states (smoothed) & histories
        self.long_state = self.NEUTRAL
        self.lat_state = self.NEUTRAL
        self._long_history = deque()  # No maxlen - we'll manage size dynamically
        self._lat_history = deque()   # No maxlen - we'll manage size dynamically

        # Compute horizon-limited indices once (depends on horizon)
        self.ind_pred = self._compute_horizon_indices(self.PRED_TIME)
        self.ind_plan = self._compute_horizon_indices(self.PLAN_TIME)

    def _compute_horizon_indices(self, time_vec):
        """Return index of first element whose time exceeds horizon, else len(time_vec)."""
        return next((i for i, t in enumerate(time_vec) if t > self.horizon), len(time_vec))

    def set_data(self, new_data):
            """Ingest latest model outputs & ego state.

            Expected new_data keys:
                acceleration_pred (with .x / .y sequences)
                velocity_pred (with .x / .y sequences)
                acceleration_plan / velocity_plan (optional, if use_plan)
                left_blinker, right_blinker, vEgo, aEgo
            """
            self.accelX_pred = [new_data['acceleration_pred'].x[i] for i in range(min(self.ind_pred, len(new_data['acceleration_pred'].x)))]
            self.accelY_pred = [new_data['acceleration_pred'].y[i] for i in range(min(self.ind_pred, len(new_data['acceleration_pred'].y)))]
            self.velX_pred = [new_data['velocity_pred'].x[i] for i in range(min(self.ind_pred, len(new_data['velocity_pred'].x)))]
            self.velY_pred = [new_data['velocity_pred'].y[i] for i in range(min(self.ind_pred, len(new_data['velocity_pred'].y)))]

            if self.use_plan:
                    self.accelX_plan = [new_data['acceleration_plan'].x[i] for i in range(min(self.ind_plan, len(new_data['acceleration_plan'].x)))]
                    self.velX_plan = [new_data['velocity_plan'].x[i] for i in range(min(self.ind_plan, len(new_data['velocity_plan'].x)))]
                    self._extend_plan(new_data)

            self.lft_blnk = new_data['left_blinker']
            self.rght_blnk = new_data['right_blinker']
            self.vel = float(new_data['vEgo'])
            self.accel = float(new_data['aEgo'])
            self.gear = new_data['gear_shifter']
            self.stopped = self.vel <= 0.05  # ~0.18 km/h threshold
            # Update kinetime slice for lateral conflict resolution (limit to horizon)
            self.kinetime = self.PRED_TIME[:self.ind_pred]

    def _extend_plan(self, new_data):
        """Extend plan arrays beyond 2.5s with prediction data when horizon > 2.5s."""
        if self.horizon <= 2.5:
            return
        additional = self.ind_pred - self.ind_plan
        if additional > 0:
            pred_start = self.ind_plan
            pred_end = min(pred_start + additional, len(new_data['acceleration_pred'].x))
            # Convert capnp slice to list comprehension (capnp doesn't support slice notation)
            additional_accelX = [new_data['acceleration_pred'].x[i] for i in range(pred_start, pred_end)]
            self.accelX_plan.extend(additional_accelX)

            vel_end = min(pred_start + additional, len(new_data['velocity_pred'].x))
            additional_velX = [new_data['velocity_pred'].x[i] for i in range(pred_start, vel_end)]
            self.velX_plan.extend(additional_velX)

    # ----------------------- Accessors & helpers -----------------------

    def get_x_vectors(self):
        """Return (accelX, velX) either from plan (if enabled) or prediction."""
        return (self.accelX_plan, self.velX_plan) if self.use_plan else (self.accelX_pred, self.velX_pred)

    def _smooth_update(self, domain, new_decision):
        """Update smoothing history for a domain ('lat' or 'long').

        If the history (size == required window) is homogeneous, commit state.
        Uses sticky values when current state is not neutral, smooth values when neutral.
        Returns committed state (int).
        """
        if domain == 'lat':
            history = self._lat_history
            current_state = self.lat_state
            # Use sticky value if current state is not neutral, otherwise use smooth
            required = self.lat_sticky if current_state != self.NEUTRAL else self.lat_smooth
            state_attr = 'lat_state'
        else:
            history = self._long_history
            current_state = self.long_state
            # Use sticky value if current state is not neutral, otherwise use smooth
            required = self.long_sticky if current_state != self.NEUTRAL else self.long_smooth
            state_attr = 'long_state'

        history.append(new_decision)

        # Trim history to the maximum required size (max of smooth and sticky)
        max_required = max(self.lat_smooth, self.lat_sticky) if domain == 'lat' else max(self.long_smooth, self.long_sticky)
        while len(history) > max_required:
            history.popleft()

        # Check if we have enough history and all entries match
        if len(history) >= required and all(h == new_decision for h in list(history)[-required:]):
            setattr(self, state_attr, new_decision)
        return getattr(self, state_attr)

    # ----------------------- Lateral decision logic -----------------------

    def curve(self):
        """Predictive lateral inference from future lateral acceleration.

        Predictive lateral is allowed even while stopped (per requirement) so we
        do NOT early-return when self.stopped is True.
        """
        if not self.accelY_pred:
            return self.NEUTRAL
        maxY = max(self.accelY_pred)
        minY = min(self.accelY_pred)

        hard_right = maxY > self.turn_thr2
        hard_left = minY < -self.turn_thr2
        mild_right = maxY > self.turn_thr1
        mild_left = minY < -self.turn_thr1

        # Conflict (simultaneous indications). Use 1s average to disambiguate.
        if (hard_right and hard_left) or (mild_right and mild_left):
            ind_1s = next((i for i, t in enumerate(self.kinetime) if t > 1), len(self.kinetime))
            accelY_1s = self.accelY_pred[:min(ind_1s, len(self.accelY_pred))]
            avg_accel_1s = (sum(accelY_1s) / len(accelY_1s)) if accelY_1s else 0.0
            if avg_accel_1s > 0:
                if hard_right:
                    return self.HARD_RIGHT
                if mild_right:
                    return self.MILD_RIGHT
            else:
                if hard_left:
                    return self.HARD_LEFT
                if mild_left:
                    return self.MILD_LEFT
            return self.NEUTRAL

        if hard_right:
            return self.HARD_RIGHT
        if hard_left:
            return self.HARD_LEFT
        if mild_right:
            return self.MILD_RIGHT
        if mild_left:
            return self.MILD_LEFT
        return self.NEUTRAL

    def turn(self):
        """Driver-intended lateral command (blinkers influence severity selection)."""
        if not self.accelY_pred:
            return self.NEUTRAL
        maxY = max(self.accelY_pred)
        minY = min(self.accelY_pred)
        if self.rght_blnk:
            if maxY > self.turn_thr2:
                return self.HARD_RIGHT
            if maxY > self.turn_thr1:
                return self.MILD_RIGHT
        if self.lft_blnk:
            if minY < -self.turn_thr2:
                return self.HARD_LEFT
            if minY < -self.turn_thr1:
                return self.MILD_LEFT
        return self.NEUTRAL

    def _lateral_decision_raw(self):
        """Combine driver intent (turn) and predictive (curve)."""
        t = self.turn()
        c = self.curve()
        if self.gear != 'drive':
            return self.NEUTRAL
        if t == self.NEUTRAL and c == self.NEUTRAL:
            return self.NEUTRAL
        if t != self.NEUTRAL and c == self.NEUTRAL:
            return t
        if c != self.NEUTRAL and t == self.NEUTRAL:
            return c
        # Both non-neutral: prioritize driver intent direction; upgrade severity
        if (t in (self.MILD_LEFT, self.HARD_LEFT) and c in (self.MILD_RIGHT, self.HARD_RIGHT)) or \
           (t in (self.MILD_RIGHT, self.HARD_RIGHT) and c in (self.MILD_LEFT, self.HARD_LEFT)):
            return t  # conflicting directions -> choose intent
        # Same direction -> choose higher severity (numerically larger means harder in each direction group)
        severity_order = {self.MILD_LEFT: 1, self.HARD_LEFT: 2, self.MILD_RIGHT: 1, self.HARD_RIGHT: 2}
        return t if severity_order.get(t, 0) >= severity_order.get(c, 0) else c

    # ----------------------- Longitudinal decision logic -----------------------

    def stop(self):
        """Return BACK if deceleration exceeds threshold."""
        accelX, _ = self.get_x_vectors()
        if not accelX:
            return self.NEUTRAL
        if min(accelX) < -self.decel_thr:
            return self.BACK
        return self.NEUTRAL

    def accelerate(self):
        """Return FORWARD if forward accel exceeds threshold."""
        accelX, _ = self.get_x_vectors()
        if not accelX:
            return self.NEUTRAL
        if max(accelX) > self.accel_thr:
            return self.FORWARD
        return self.NEUTRAL

    def _longitudinal_decision_raw(self):
        """Combine accelerate and stop signals with priority: BACK > FORWARD."""
        acc = self.accelerate()
        dec = self.stop()
        if self.gear != 'drive':
            return self.NEUTRAL
        if dec == self.BACK:
            return self.BACK
        if acc == self.FORWARD:
            return self.FORWARD
        return self.NEUTRAL

    def short_decision(self):
        """Return a tuple (lateral_command_str, longitudinal_command_str).

        Each axis is smoothed independently using its configured window length.
        Predictive lateral is allowed at zero speed. Both outputs may be
        non-neutral simultaneously (e.g., HARD_LEFT & BACK for hard braking in turn).
        """
        lat_raw = self._lateral_decision_raw()
        long_raw = self._longitudinal_decision_raw()
        lat_committed = self._smooth_update('lat', lat_raw)
        long_committed = self._smooth_update('long', long_raw)
        return (self.commands[lat_committed], self.commands[long_committed])
