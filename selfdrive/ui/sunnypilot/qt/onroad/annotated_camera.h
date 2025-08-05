/**
 * Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.
 *
 * This file is part of sunnypilot and is licensed under the MIT License.
 * See the LICENSE.md file in the root directory for more details.
 */

#pragma once

#include <QResizeEvent>
#include "selfdrive/ui/qt/onroad/annotated_camera.h"
#include "selfdrive/ui/sunnypilot/qt/onroad/seat_control_button.h"

class AnnotatedCameraWidgetSP : public AnnotatedCameraWidget {
  Q_OBJECT

public:
  explicit AnnotatedCameraWidgetSP(VisionStreamType type, QWidget *parent = nullptr);
  void updateState(const UIState &s) override;

protected:
  void resizeEvent(QResizeEvent *event) override;

private:
  SeatControlConfigButton *seat_control_btn;
};
