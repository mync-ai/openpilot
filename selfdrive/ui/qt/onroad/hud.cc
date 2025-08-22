#include "selfdrive/ui/qt/onroad/hud.h"

#include <cmath>
#include <iostream>
#include "selfdrive/ui/qt/util.h"

constexpr int SET_SPEED_NA = 255;

HudRenderer::HudRenderer() {}

void HudRenderer::updateState(const UIState &s) {
  is_metric = s.scene.is_metric;
  status = s.status;

  const SubMaster &sm = *(s.sm);
  if (sm.rcv_frame("carState") < s.scene.started_frame) {
    is_cruise_set = false;
    set_speed = SET_SPEED_NA;
    speed = 0.0;
    return;
  }


  const auto &controls_state = sm["controlsState"].getControlsState();
  const auto &car_state = sm["carState"].getCarState();

  // Handle older routes where vCruiseCluster is not set
  set_speed = car_state.getVCruiseCluster() == 0.0 ? controls_state.getVCruiseDEPRECATED() : car_state.getVCruiseCluster();
  is_cruise_set = set_speed > 0 && set_speed != SET_SPEED_NA;
  is_cruise_available = set_speed != -1;

  if (is_cruise_set && !is_metric) {
    set_speed *= KM_TO_MILE;
  }

  // Handle older routes where vEgoCluster is not set
  v_ego_cluster_seen = v_ego_cluster_seen || car_state.getVEgoCluster() != 0.0;
  float v_ego = v_ego_cluster_seen ? car_state.getVEgoCluster() : car_state.getVEgo();
  speed = std::max<float>(0.0f, v_ego * (is_metric ? MS_TO_KPH : MS_TO_MPH));

  // Update seat control state
  updateSeatControlState(sm);
}

void HudRenderer::updateSeatControlState(const SubMaster &sm) {
  try {
    // Safely check if seatControl service exists
    bool seatControlAlive = false;
    try {
      seatControlAlive = sm.alive("seatControl");
    } catch (const std::exception& e) {
      // seatControl not in SubMaster subscription
      seat_control_lateral_command = "NO_SUB";
      seat_control_longitudinal_command = "NO_SUB";
      return;
    }

    if (!seatControlAlive) {
      seat_control_lateral_command = "NO_SVC";
      seat_control_longitudinal_command = "NO_SVC";
      return;
    }

    // Check if we have updates
    if (!sm.updated("seatControl")) {
      // No new data, but service is alive - keep existing values or set default
      if (seat_control_lateral_command.isEmpty()) {
        seat_control_lateral_command = "WAITING";
        seat_control_longitudinal_command = "WAITING";
      }
      return;
    }

    // Try to get the message
    const auto &seat_control = sm["seatControl"].getSeatControl();

    // Map lateral command enum to display string
    QString lateral_str;
    auto lateral_command = seat_control.getLateralCommand();
    switch ((int)lateral_command) {
      case 0: // neutral
        lateral_str = "NEUTRAL";
        break;
      case 1: // forward
        lateral_str = "FORWARD";
        break;
      case 2: // back
        lateral_str = "BACK";
        break;
      case 3: // mildLeft
        lateral_str = "MILD LEFT";
        break;
      case 4: // mildRight
        lateral_str = "MILD RIGHT";
        break;
      case 5: // hardLeft
        lateral_str = "HARD LEFT";
        break;
      case 6: // hardRight
        lateral_str = "HARD RIGHT";
        break;
      default:
        lateral_str = QString("UNK_%1").arg((int)lateral_command);
        break;
    }

    // Map longitudinal command enum to display string
    QString longitudinal_str;
    auto longitudinal_command = seat_control.getLongitudinalCommand();
    switch ((int)longitudinal_command) {
      case 0: // neutral
        longitudinal_str = "NEUTRAL";
        break;
      case 1: // forward
        longitudinal_str = "FORWARD";
        break;
      case 2: // back
        longitudinal_str = "BACK";
        break;
      case 3: // mildLeft
        longitudinal_str = "MILD LEFT";
        break;
      case 4: // mildRight
        longitudinal_str = "MILD RIGHT";
        break;
      case 5: // hardLeft
        longitudinal_str = "HARD LEFT";
        break;
      case 6: // hardRight
        longitudinal_str = "HARD RIGHT";
        break;
      default:
        longitudinal_str = QString("UNK_%1").arg((int)longitudinal_command);
        break;
    }

    seat_control_lateral_command = lateral_str;
    seat_control_longitudinal_command = longitudinal_str;

  } catch (const std::exception& e) {
    seat_control_lateral_command = "ERROR";
    seat_control_longitudinal_command = "ERROR";
  } catch (...) {
    seat_control_lateral_command = "ERROR";
    seat_control_longitudinal_command = "ERROR";
  }
}

void HudRenderer::draw(QPainter &p, const QRect &surface_rect) {
  p.save();

  // Draw header gradient
  QLinearGradient bg(0, UI_HEADER_HEIGHT - (UI_HEADER_HEIGHT / 2.5), 0, UI_HEADER_HEIGHT);
  bg.setColorAt(0, QColor::fromRgbF(0, 0, 0, 0.45));
  bg.setColorAt(1, QColor::fromRgbF(0, 0, 0, 0));
  p.fillRect(0, 0, surface_rect.width(), UI_HEADER_HEIGHT, bg);


  if (is_cruise_available) {
    drawSetSpeed(p, surface_rect);
  }

  drawCurrentSpeed(p, surface_rect);
  drawSeatControlCommand(p, surface_rect);

  p.restore();
}

void HudRenderer::drawSetSpeed(QPainter &p, const QRect &surface_rect) {
  // Draw outer box + border to contain set speed
  const QSize default_size = {172, 204};
  QSize set_speed_size = is_metric ? QSize(200, 204) : default_size;
  QRect set_speed_rect(QPoint(60 + (default_size.width() - set_speed_size.width()) / 2, 45), set_speed_size);

  // Draw set speed box
  p.setPen(QPen(QColor(255, 255, 255, 75), 6));
  p.setBrush(QColor(0, 0, 0, 166));
  p.drawRoundedRect(set_speed_rect, 32, 32);

  // Colors based on status
  QColor max_color = QColor(0xa6, 0xa6, 0xa6, 0xff);
  QColor set_speed_color = QColor(0x72, 0x72, 0x72, 0xff);
  if (is_cruise_set) {
    set_speed_color = QColor(255, 255, 255);
    if (status == STATUS_DISENGAGED) {
      max_color = QColor(255, 255, 255);
    } else if (status == STATUS_OVERRIDE) {
      max_color = QColor(0x91, 0x9b, 0x95, 0xff);
    } else {
      max_color = QColor(0x80, 0xd8, 0xa6, 0xff);
    }
  }

  // Draw "MAX" text
  p.setFont(InterFont(40, QFont::DemiBold));
  p.setPen(max_color);
  p.drawText(set_speed_rect.adjusted(0, 27, 0, 0), Qt::AlignTop | Qt::AlignHCenter, tr("MAX"));

  // Draw set speed
  QString setSpeedStr = is_cruise_set ? QString::number(std::nearbyint(set_speed)) : "–";
  p.setFont(InterFont(90, QFont::Bold));
  p.setPen(set_speed_color);
  p.drawText(set_speed_rect.adjusted(0, 77, 0, 0), Qt::AlignTop | Qt::AlignHCenter, setSpeedStr);
}

void HudRenderer::drawCurrentSpeed(QPainter &p, const QRect &surface_rect) {
  QString speedStr = QString::number(std::nearbyint(speed));

  p.setFont(InterFont(176, QFont::Bold));
  drawText(p, surface_rect.center().x(), 210, speedStr);

  p.setFont(InterFont(66));
  drawText(p, surface_rect.center().x(), 290, is_metric ? tr("km/h") : tr("mph"), 200);
}

void HudRenderer::drawText(QPainter &p, int x, int y, const QString &text, int alpha) {
  QRect real_rect = p.fontMetrics().boundingRect(text);
  real_rect.moveCenter({x, y - real_rect.height() / 2});

  p.setPen(QColor(0xff, 0xff, 0xff, alpha));
  p.drawText(real_rect.x(), real_rect.bottom(), text);
}

void HudRenderer::drawColoredText(QPainter &p, int x, int y, const QString &text, QColor color, int alpha) {
  QRect real_rect = p.fontMetrics().boundingRect(text);
  real_rect.moveCenter({x, y - real_rect.height() / 2});

  p.setPen(QColor(color.red(), color.green(), color.blue(), alpha));
  p.drawText(real_rect.x(), real_rect.bottom(), text);
}

void HudRenderer::drawSeatControlCommand(QPainter &p, const QRect &surface_rect) {
  // Position the seat control display on the right side, below where experimental button would be
  const int border_size = 30;
  const int button_size = 192;
  const int width = 440;
  const int height = 180; // Reduced height for single line
  int alpha = 200;

  int x = surface_rect.width() - border_size - width;
  int y = border_size + button_size + 20;

  QRect seat_control_rect(x, y, width, height);

  // Draw background box
  p.setPen(QPen(QColor(255, 255, 255, 200), 3));
  p.setBrush(QColor(0, 0, 0, 166));
  p.drawRoundedRect(seat_control_rect, 20, 20);

  // Draw "SEAT CONTROL" label
  p.setFont(InterFont(55, QFont::Normal));
  QColor seat_label_color(0xf6, 0xf6, 0xf6); // #f6f6f6
  drawColoredText(p, seat_control_rect.center().x(), seat_control_rect.top() + 65, "HAPTIC SIGNAL", seat_label_color, alpha);

  // Helper function to get command color
  auto getCommandColor = [](const QString &command) -> QColor {
    if (command == "NEUTRAL") {
      return QColor(0xe7, 0xe7, 0xe7); // #e7e7e7
    } else if (command == "FORWARD") {
      return QColor(0xa3, 0xff, 0xac); // #a3ffac
    } else if (command == "BACK") {
      return QColor(0xff, 0x6b, 0x55); // #ff6b55
    } else if (command == "MILD LEFT" || command == "MILD RIGHT") {
      return QColor(0xff, 0xfa, 0x68); // #fffa68
    } else if (command == "HARD LEFT" || command == "HARD RIGHT") {
      return QColor(0xff, 0xa2, 0x39); // #ffa239
    } else if (command == "NONE") {
      return QColor(0x80, 0x80, 0x80); // #808080 gray for NONE
    } else {
      return QColor(0xf6, 0xf6, 0xf6); // Default #f6f6f6
    }
  };

  // Determine the display text based on signal availability
  QString display_text;
  QColor text_color;

  // Check if we have valid signals
  bool has_signal = (seat_control_lateral_command != "NO_SUB" &&
                     seat_control_lateral_command != "NO_SVC" &&
                     seat_control_lateral_command != "ERROR" &&
                     seat_control_lateral_command != "WAITING" &&
                     seat_control_longitudinal_command != "NO_SUB" &&
                     seat_control_longitudinal_command != "NO_SVC" &&
                     seat_control_longitudinal_command != "ERROR" &&
                     seat_control_longitudinal_command != "WAITING");

  if (!has_signal) {
    display_text = "NONE";
    text_color = getCommandColor("NONE");
  } else {
    // Show only the active (non-neutral) command
    if (seat_control_lateral_command != "NEUTRAL") {
      display_text = seat_control_lateral_command;
      text_color = getCommandColor(seat_control_lateral_command);
    } else if (seat_control_longitudinal_command != "NEUTRAL") {
      display_text = seat_control_longitudinal_command;
      text_color = getCommandColor(seat_control_longitudinal_command);
    } else {
      // Both are neutral
      display_text = "NEUTRAL";
      text_color = getCommandColor("NEUTRAL");
    }
  }

  // Draw the single line command display
  p.setFont(InterFont(70, QFont::Bold));
  drawColoredText(p, seat_control_rect.center().x(), seat_control_rect.top() + 140, display_text, text_color, alpha);
}
