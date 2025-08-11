/**
 * Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.
 *
 * This file is part of sunnypilot and is licensed under the MIT License.
 * See the LICENSE.md file in the root directory for more details.
 */

#include "selfdrive/ui/sunnypilot/qt/onroad/annotated_camera.h"

AnnotatedCameraWidgetSP::AnnotatedCameraWidgetSP(VisionStreamType type, QWidget *parent)
    : AnnotatedCameraWidget(type, parent) {
  // Seat control config button removed (legacy UI deprecated in favor of CLI + JSON hot reload)
}

void AnnotatedCameraWidgetSP::updateState(const UIState &s) {
  AnnotatedCameraWidget::updateState(s);
  // No seat control button to update
}

void AnnotatedCameraWidgetSP::resizeEvent(QResizeEvent *event) {
  AnnotatedCameraWidget::resizeEvent(event);
  // No seat control button to reposition
}
