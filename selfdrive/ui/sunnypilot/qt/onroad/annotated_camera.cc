/**
 * Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.
 *
 * This file is part of sunnypilot and is licensed under the MIT License.
 * See the LICENSE.md file in the root directory for more details.
 */

#include "selfdrive/ui/sunnypilot/qt/onroad/annotated_camera.h"

AnnotatedCameraWidgetSP::AnnotatedCameraWidgetSP(VisionStreamType type, QWidget *parent)
    : AnnotatedCameraWidget(type, parent) {

  // Create seat control button
  seat_control_btn = new SeatControlConfigButton(this);

  // Position the button manually since main_layout is private
  // We'll position it in the bottom-right corner, below where the experimental button would be
  seat_control_btn->move(width() - seat_btn_size - 20, height() - seat_btn_size - 20);
  seat_control_btn->show();
}

void AnnotatedCameraWidgetSP::updateState(const UIState &s) {
  AnnotatedCameraWidget::updateState(s);

  // Update seat control button state
  if (seat_control_btn) {
    seat_control_btn->updateState(s);
  }
}

void AnnotatedCameraWidgetSP::resizeEvent(QResizeEvent *event) {
  AnnotatedCameraWidget::resizeEvent(event);

  // Reposition seat control button when widget is resized
  if (seat_control_btn) {
    // Position in bottom-right corner with some margin
    int margin = 20;
    seat_control_btn->move(width() - seat_btn_size - margin,
                          height() - seat_btn_size - margin);
  }
}
