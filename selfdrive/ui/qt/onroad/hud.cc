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
      // seatControl not in SubMaster subscription - this is the issue!
      seat_control_command = "NOT_SUBSCRIBED";
      seat_control_source = "SubMaster exception";
      return;
    }

    if (!seatControlAlive) {
      seat_control_command = "NO_SERVICE";
      seat_control_source = "Service not alive";
      return;
    }

    // Check if we have updates
    if (!sm.updated("seatControl")) {
      // No new data, but service is alive - keep existing values or set default
      if (seat_control_command.isEmpty()) {
        seat_control_command = "WAITING";
        seat_control_source = "No Data";
      }
      return;
    }

    // Try to get the message
    const auto &seat_control = sm["seatControl"].getSeatControl();

    // Map enum values to display strings using integer values
    QString command_str;
    auto command = seat_control.getCommand();
    switch ((int)command) {
      case 0: // neutral
        command_str = "NEUTRAL";
        break;
      case 1: // forward
        command_str = "FORWARD";
        break;
      case 2: // back
        command_str = "BACK";
        break;
      case 3: // mildLeft
        command_str = "MILD_LEFT";
        break;
      case 4: // mildRight
        command_str = "MILD_RIGHT";
        break;
      case 5: // hardLeft
        command_str = "HARD_LEFT";
        break;
      case 6: // hardRight
        command_str = "HARD_RIGHT";
        break;
      default:
        command_str = QString("UNK_%1").arg((int)command);
        command_str = "Bruh";
        break;
    }

    QString source_str;
    auto source = seat_control.getSource();
    switch ((int)source) {
      case 0: // none
        source_str = "None";
        break;
      case 1: // stop
        source_str = "Stop";
        break;
      case 2: // accelerate
        source_str = "Accelerate";
        break;
      case 3: // curve
        source_str = "Curve";
        break;
      case 4: // turn
        source_str = "Turn";
        break;
      default:
        source_str = QString("UNK_%1").arg((int)source);
        break;
    }

    seat_control_command = command_str;
    seat_control_source = source_str;

  } catch (const std::exception& e) {
    seat_control_command = "ERROR";
    seat_control_source = "Exception";
  } catch (...) {
    seat_control_command = "ERROR";
    seat_control_source = "Unknown";
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
  const int width = 420;  // Increased from 310 to accommodate larger font
  const int height = 220; // Increased from 120 to accommodate larger font
  int alpha = 200;

  int x = surface_rect.width() - border_size - width;
  int y = border_size + button_size + 20;

  QRect seat_control_rect(x, y, width, height);

  // Draw background box
  p.setPen(QPen(QColor(255, 255, 255, 200), 3));
  p.setBrush(QColor(0, 0, 0, 166));
  p.drawRoundedRect(seat_control_rect, 20, 20);

  // Draw "SEAT" label with your specified color #f6f6f6
  p.setFont(InterFont(65, QFont::Normal));
  QColor seat_label_color(0xf6, 0xf6, 0xf6); // #f6f6f6
  drawColoredText(p, seat_control_rect.center().x(), seat_control_rect.top() + 70, "SEAT", seat_label_color, alpha);

  // Draw command text with color based on command type
  p.setFont(InterFont(65, QFont::Bold));

  QColor command_color;
  if (seat_control_command == "NEUTRAL") {
    command_color = QColor(0xe7, 0xe7, 0xe7); // #e7e7e7
  } else if (seat_control_command == "FORWARD") {
    command_color = QColor(0xa3, 0xff, 0xac); // #a3ffac
  } else if (seat_control_command == "BACK") {
    command_color = QColor(0xff, 0x6b, 0x55); // #ff6b55
  } else if (seat_control_command == "MILD_LEFT" || seat_control_command == "MILD_RIGHT") {
    command_color = QColor(0xff, 0xfa, 0x68); // #fffa68
  } else if (seat_control_command == "HARD_LEFT" || seat_control_command == "HARD_RIGHT") {
    command_color = QColor(0xff, 0xa2, 0x39); // #ffa239
  } else {
    command_color = QColor(0xf6, 0xf6, 0xf6); // Default #f6f6f6
  }

  drawColoredText(p, seat_control_rect.center().x(), seat_control_rect.top() + 135, seat_control_command, command_color, alpha);

  // Draw source text (optional, if not "None")
  if (seat_control_source != "None") {
    QString source_text = QString("(%1)").arg(seat_control_source);
    p.setFont(InterFont(65, QFont::Normal)); // Use size 65 for consistency
    QColor source_color(0xf6, 0xf6, 0xf6); // #f6f6f6
    drawColoredText(p, seat_control_rect.center().x(), seat_control_rect.top() + 195, source_text, source_color, alpha);
  }
}
