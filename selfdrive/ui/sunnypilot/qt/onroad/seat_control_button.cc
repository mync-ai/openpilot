#include "selfdrive/ui/sunnypilot/qt/onroad/seat_control_button.h"

#include <QPainter>
#include <QPainterPath>
#include <QApplication>
#include <QScreen>
#include <QMessageBox>
#include <QGridLayout>
#include <QGroupBox>
#include <QTimer>
#include <QThread>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QAbstractButton>
#include <random>
#include <cmath>

#include "cereal/messaging/messaging.h"
#include "common/swaglog.h"
#include "common/timing.h"
#include "selfdrive/ui/qt/util.h"

// SeatControlConfigDialog Implementation
SeatControlConfigDialog::SeatControlConfigDialog(QWidget *parent)
    : QDialog(parent), waiting_for_response(false), config_valid(true) {
    setWindowTitle("Seat Control Configuration");

    // Make dialog larger and position at bottom of screen
    setFixedSize(1400, 1000); // Increased height to accommodate taller layout with proper spacing
    setModal(true);

    // Position dialog at bottom center of screen with better handling
    QTimer::singleShot(0, this, [this, parent]() {
        QRect screenGeometry;
        if (parent && parent->window()) {
            // Try to get the screen containing the parent window using QApplication
            QWidget* topLevel = parent->window();
            QScreen* screen = QApplication::screenAt(topLevel->geometry().center());
            if (screen) {
                screenGeometry = screen->availableGeometry();
            } else {
                // Fallback to primary screen
                screenGeometry = QApplication::primaryScreen()->availableGeometry();
            }
        } else {
            // Fallback to primary screen
            screenGeometry = QApplication::primaryScreen()->availableGeometry();
        }

        // Center horizontally, position at bottom with some margin
        int x = screenGeometry.x() + (screenGeometry.width() - width()) / 2;
        int y = screenGeometry.y() + screenGeometry.height() - height() - 100; // 100px from bottom

        // Ensure dialog stays within screen bounds
        x = qMax(screenGeometry.x(), qMin(x, screenGeometry.x() + screenGeometry.width() - width()));
        y = qMax(screenGeometry.y(), qMin(y, screenGeometry.y() + screenGeometry.height() - height()));

        move(x, y);
    });

    // Generate unique request ID
    std::random_device rd;
    std::mt19937 gen(rd());
    current_request_id = gen();

    setupUI();
    setupMessaging();

    // Load current configuration on startup
    QTimer::singleShot(100, this, &SeatControlConfigDialog::requestCurrentConfig);
}

void SeatControlConfigDialog::setupUI() {
    main_layout = new QVBoxLayout(this);
    main_layout->setSpacing(25); // Increased spacing
    main_layout->setContentsMargins(40, 40, 40, 40); // Larger margins

    // Title and description
    title_label = new QLabel("Seat Control Parameters");
    title_label->setStyleSheet("font-size: 36px; font-weight: bold; color: #ffffff;"); // Larger font
    title_label->setAlignment(Qt::AlignCenter);
    main_layout->addWidget(title_label);

    description_label = new QLabel(
        "Configure the hyperparameters for the seat control system. "
        "These settings control how the seat responds to vehicle motion."
    );
    description_label->setStyleSheet("font-size: 22px; color: #cccccc; margin-bottom: 15px;"); // Larger font
    description_label->setWordWrap(true);
    description_label->setAlignment(Qt::AlignCenter);
    main_layout->addWidget(description_label);

    // Parameters group
    QGroupBox *params_group = new QGroupBox("Parameters");
    params_group->setStyleSheet(
        "QGroupBox { font-size: 24px; font-weight: bold; color: #ffffff; " // Larger font
        "border: 3px solid #666666; border-radius: 15px; margin-top: 15px; padding-top: 15px; }" // Thicker border
        "QGroupBox::title { subcontrol-origin: margin; left: 25px; }"
    );

    QGridLayout *params_layout = new QGridLayout(params_group);
    params_layout->setContentsMargins(30, 40, 30, 30); // Larger margins
    params_layout->setVerticalSpacing(45); // Much larger vertical spacing to prevent overlap of 50px tall spinboxes
    params_layout->setHorizontalSpacing(40); // Much larger horizontal spacing to accommodate wide spinbox buttons

    // Set column stretch factors to give more space to the spinbox column
    params_layout->setColumnStretch(0, 2); // Label column gets 2 parts
    params_layout->setColumnStretch(1, 3); // Spinbox column gets 3 parts (more space for wide buttons)

    // Set minimum row heights to prevent overlap
    for (int row = 0; row < 7; row++) {
        params_layout->setRowMinimumHeight(row, 70); // Each row needs at least 70px for 50px spinboxes + spacing
    }

    // Create input fields with labels and descriptions
    auto create_label = [](const QString &text, const QString &description = "") {
        QVBoxLayout *layout = new QVBoxLayout();
        layout->setContentsMargins(0, 0, 0, 0);
        layout->setSpacing(6); // Slightly more space between label and description

        QLabel *label = new QLabel(text);
        label->setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;"); // Larger font
        label->setMinimumHeight(25); // Taller minimum height
        label->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
        layout->addWidget(label);

        if (!description.isEmpty()) {
            QLabel *desc = new QLabel(description);
            desc->setStyleSheet("font-size: 16px; color: #aaaaaa;"); // Larger font
            desc->setWordWrap(true);
            desc->setMinimumHeight(20); // Taller minimum height
            desc->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
            layout->addWidget(desc);
        }

        // Create a container widget to hold the layout and set proper size constraints
        QWidget *container = new QWidget();
        container->setLayout(layout);
        container->setMinimumHeight(description.isEmpty() ? 50 : 70); // Much taller containers to match spinbox height
        container->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Minimum);

        // Return the container widget instead of the layout
        return container;
    };    // Frequency
    params_layout->addWidget(create_label("Update Frequency (Hz)", "How often seat commands are sent"), 0, 0);
    frequency_spin = new QSpinBox();
    frequency_spin->setRange(1, 100);
    frequency_spin->setValue(20);
    frequency_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    frequency_spin->setMinimumHeight(50); // Touch-friendly height
    frequency_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(frequency_spin, 0, 1);

    // Turn Threshold 1
    params_layout->addWidget(create_label("Turn Threshold 1", "First threshold for turn detection"), 1, 0);
    turn_thresh_1_spin = new QDoubleSpinBox();
    turn_thresh_1_spin->setRange(0.1, 10.0);
    turn_thresh_1_spin->setDecimals(2);
    turn_thresh_1_spin->setSingleStep(0.1);
    turn_thresh_1_spin->setValue(1.0);
    turn_thresh_1_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    turn_thresh_1_spin->setMinimumHeight(50); // Touch-friendly height
    turn_thresh_1_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(turn_thresh_1_spin, 1, 1);

    // Turn Threshold 2
    params_layout->addWidget(create_label("Turn Threshold 2", "Second threshold for aggressive turns"), 2, 0);
    turn_thresh_2_spin = new QDoubleSpinBox();
    turn_thresh_2_spin->setRange(0.1, 10.0);
    turn_thresh_2_spin->setDecimals(2);
    turn_thresh_2_spin->setSingleStep(0.1);
    turn_thresh_2_spin->setValue(2.5);
    turn_thresh_2_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    turn_thresh_2_spin->setMinimumHeight(50); // Touch-friendly height
    turn_thresh_2_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(turn_thresh_2_spin, 2, 1);

    // Longitudinal Threshold
    params_layout->addWidget(create_label("Longitudinal Threshold", "Threshold for acceleration/braking"), 3, 0);
    long_thresh_spin = new QDoubleSpinBox();
    long_thresh_spin->setRange(0.1, 10.0);
    long_thresh_spin->setDecimals(2);
    long_thresh_spin->setSingleStep(0.1);
    long_thresh_spin->setValue(1.0);
    long_thresh_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    long_thresh_spin->setMinimumHeight(50); // Touch-friendly height
    long_thresh_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(long_thresh_spin, 3, 1);

    // Smoothing Window
    params_layout->addWidget(create_label("Smoothing Window", "Number of samples for smoothing"), 4, 0);
    smoothing_window_spin = new QSpinBox();
    smoothing_window_spin->setRange(1, 20);
    smoothing_window_spin->setValue(4);
    smoothing_window_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    smoothing_window_spin->setMinimumHeight(50); // Touch-friendly height
    smoothing_window_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(smoothing_window_spin, 4, 1);

    // Horizon
    params_layout->addWidget(create_label("Prediction Horizon (s)", "Time horizon for predictions"), 5, 0);
    horizon_spin = new QDoubleSpinBox();
    horizon_spin->setRange(0.5, 10.0);
    horizon_spin->setDecimals(1);
    horizon_spin->setSingleStep(0.1);
    horizon_spin->setValue(3.0);
    horizon_spin->setStyleSheet("font-size: 18px; padding: 12px; min-height: 50px;"); // Larger font and height
    horizon_spin->setMinimumHeight(50); // Touch-friendly height
    horizon_spin->setMinimumWidth(200); // Ensure enough width for wide buttons
    params_layout->addWidget(horizon_spin, 5, 1);

    // Set button text for spinboxes to show + and - symbols
    auto set_spinbox_button_text = [](QSpinBox* spinbox) {
        if (spinbox->findChild<QLineEdit*>()) {
            QList<QAbstractButton*> buttons = spinbox->findChildren<QAbstractButton*>();
            for (auto* button : buttons) {
                if (button->objectName().contains("up")) {
                    button->setText("+");
                } else if (button->objectName().contains("down")) {
                    button->setText("−");
                }
            }
        }
    };

    auto set_double_spinbox_button_text = [](QDoubleSpinBox* spinbox) {
        if (spinbox->findChild<QLineEdit*>()) {
            QList<QAbstractButton*> buttons = spinbox->findChildren<QAbstractButton*>();
            for (auto* button : buttons) {
                if (button->objectName().contains("up")) {
                    button->setText("+");
                } else if (button->objectName().contains("down")) {
                    button->setText("−");
                }
            }
        }
    };

    // Apply button text after a short delay to ensure widgets are fully constructed
    QTimer::singleShot(50, [=]() {
        set_spinbox_button_text(frequency_spin);
        set_double_spinbox_button_text(turn_thresh_1_spin);
        set_double_spinbox_button_text(turn_thresh_2_spin);
        set_double_spinbox_button_text(long_thresh_spin);
        set_spinbox_button_text(smoothing_window_spin);
        set_double_spinbox_button_text(horizon_spin);
    });

    // Use Plan
    params_layout->addWidget(create_label("Use Plan Data", "Use plan instead of prediction data"), 6, 0);
    use_plan_check = new QCheckBox();
    use_plan_check->setStyleSheet("font-size: 18px; min-height: 50px;"); // Larger font and height
    use_plan_check->setMinimumHeight(50); // Touch-friendly height
    params_layout->addWidget(use_plan_check, 6, 1);

    main_layout->addWidget(params_group);

    // Validation label
    validation_label = new QLabel();
    validation_label->setStyleSheet("font-size: 18px; color: #ff6666; font-weight: bold;"); // Larger font
    validation_label->setAlignment(Qt::AlignCenter);
    validation_label->hide();
    main_layout->addWidget(validation_label);

    // Control buttons
    QHBoxLayout *control_layout = new QHBoxLayout();

    load_button = new QPushButton("Load Current");
    load_button->setStyleSheet(
        "QPushButton { background-color: #4a90e2; color: white; font-size: 16px; " // Back to original font size
        "padding: 10px 20px; border-radius: 8px; font-weight: bold; }" // Back to original padding
        "QPushButton:hover { background-color: #357abd; }"
        "QPushButton:pressed { background-color: #2968a3; }"
    );
    connect(load_button, &QPushButton::clicked, this, &SeatControlConfigDialog::requestCurrentConfig);
    control_layout->addWidget(load_button);

    reset_button = new QPushButton("Reset to Defaults");
    reset_button->setStyleSheet(
        "QPushButton { background-color: #f39c12; color: white; font-size: 16px; " // Back to original font size
        "padding: 10px 20px; border-radius: 8px; font-weight: bold; }" // Back to original padding
        "QPushButton:hover { background-color: #d68910; }"
        "QPushButton:pressed { background-color: #b7750f; }"
    );
    connect(reset_button, &QPushButton::clicked, this, &SeatControlConfigDialog::resetToDefaults);
    control_layout->addWidget(reset_button);

    control_layout->addStretch();
    main_layout->addLayout(control_layout);

    // Status and progress
    status_label = new QLabel();
    status_label->setStyleSheet("font-size: 16px; color: #66cc66;"); // Back to smaller font
    status_label->setAlignment(Qt::AlignCenter);
    main_layout->addWidget(status_label);

    progress_bar = new QProgressBar();
    progress_bar->setVisible(false);
    progress_bar->setStyleSheet(
        "QProgressBar { border: 2px solid #666666; border-radius: 5px; text-align: center; " // Back to original
        "font-size: 14px; min-height: 20px; }" // Back to original size
        "QProgressBar::chunk { background-color: #4a90e2; border-radius: 3px; }"
    );
    main_layout->addWidget(progress_bar);

    // Dialog buttons
    button_box = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
    button_box->button(QDialogButtonBox::Save)->setText("Save & Apply");
    button_box->button(QDialogButtonBox::Save)->setStyleSheet(
        "QPushButton { background-color: #27ae60; color: white; font-size: 16px; " // Back to original font size
        "padding: 12px 25px; border-radius: 8px; font-weight: bold; }" // Back to original padding
        "QPushButton:hover { background-color: #229954; }"
        "QPushButton:pressed { background-color: #1e8449; }"
        "QPushButton:disabled { background-color: #7f8c8d; }"
    );
    button_box->button(QDialogButtonBox::Cancel)->setStyleSheet(
        "QPushButton { background-color: #95a5a6; color: white; font-size: 16px; " // Back to original font size
        "padding: 12px 25px; border-radius: 8px; font-weight: bold; }" // Back to original padding
        "QPushButton:hover { background-color: #7f8c8d; }"
        "QPushButton:pressed { background-color: #6c7b7d; }"
    );

    connect(button_box, &QDialogButtonBox::accepted, this, &SeatControlConfigDialog::saveConfig);
    connect(button_box, &QDialogButtonBox::rejected, this, &QDialog::reject);
    main_layout->addWidget(button_box);

    // Set up validation timer
    validation_timer = new QTimer(this);
    validation_timer->setSingleShot(false);
    validation_timer->setInterval(500); // Validate every 500ms
    connect(validation_timer, &QTimer::timeout, this, &SeatControlConfigDialog::onValidationTimer);

    // Connect input changes to validation
    connect(frequency_spin, QOverload<int>::of(&QSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);
    connect(turn_thresh_1_spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);
    connect(turn_thresh_2_spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);
    connect(long_thresh_spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);
    connect(smoothing_window_spin, QOverload<int>::of(&QSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);
    connect(horizon_spin, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this, &SeatControlConfigDialog::validateInputs);

    validation_timer->start();

    // Set dialog style
    setStyleSheet(
        "QDialog { background-color: #2c3e50; }"
        "QLabel { color: #ffffff; }"
        "QSpinBox, QDoubleSpinBox { "
        "  background-color: #34495e; color: #ffffff; border: 2px solid #666666; "
        "  border-radius: 8px; padding: 8px; font-size: 18px; min-height: 50px; }"
        "QSpinBox::up-button, QDoubleSpinBox::up-button { "
        "  background-color: #4a90e2; border: 2px solid #357abd; "
        "  border-top-right-radius: 8px; width: 60px; color: #ffffff; " // Much wider button (was 30px)
        "  font-size: 24px; font-weight: bold; min-height: 25px; " // Larger font for button text
        "  subcontrol-position: top right; subcontrol-origin: border; }"
        "QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover { "
        "  background-color: #357abd; }"
        "QSpinBox::down-button, QDoubleSpinBox::down-button { "
        "  background-color: #4a90e2; border: 2px solid #357abd; "
        "  border-bottom-right-radius: 8px; width: 60px; color: #ffffff; " // Much wider button (was 30px)
        "  font-size: 24px; font-weight: bold; min-height: 25px; " // Larger font for button text
        "  subcontrol-position: bottom right; subcontrol-origin: border; }"
        "QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { "
        "  background-color: #357abd; }"
        "QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { "
        "  width: 20px; height: 20px; }" // Larger arrow icons
        "QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { "
        "  width: 20px; height: 20px; }" // Larger arrow icons
        "QCheckBox { color: #ffffff; font-size: 18px; min-height: 50px; }"
        "QCheckBox::indicator { width: 25px; height: 25px; }"
        "QCheckBox::indicator:unchecked { background-color: #34495e; border: 2px solid #666666; border-radius: 4px; }"
        "QCheckBox::indicator:checked { background-color: #27ae60; border: 2px solid #27ae60; border-radius: 4px; }"
    );
}

void SeatControlConfigDialog::setupMessaging() {
    // Initialize messaging for configuration requests
    pm = std::make_unique<PubMaster>(std::vector<const char*>{"seatControlConfigRequest"});
    sm = std::make_unique<SubMaster>(std::vector<const char*>{"seatControlConfig"});

    // Set up timer to check for incoming messages - less frequent to avoid performance issues
    message_timer = new QTimer(this);
    message_timer->setInterval(500); // Check every 500ms instead of 100ms
    message_timer->setSingleShot(false);

    connect(message_timer, &QTimer::timeout, this, [this]() {
        if (!waiting_for_response) {
            return; // Don't check if we're not waiting for anything
        }

        sm->update();
        if (sm->updated("seatControlConfig")) {
            auto config_msg = (*sm)["seatControlConfig"].getSeatControlConfig();

            SeatControlConfig config;
            config.frequency = config_msg.getFrequency();
            config.turn_thresh_1 = config_msg.getTurnThresh1();
            config.turn_thresh_2 = config_msg.getTurnThresh2();
            config.long_thresh = config_msg.getLongThresh();
            config.smoothing_window = config_msg.getSmoothingWindow();
            config.horizon = config_msg.getHorizon();
            config.use_plan = config_msg.getUsePlan();

            onConfigReceived(config);
        }
    });

    // Don't start the timer immediately - only when we need it
}

void SeatControlConfigDialog::sendConfigRequest(int action, const SeatControlConfig *config) {
    MessageBuilder msg;
    auto event = msg.initEvent();
    auto request = event.initSeatControlConfigRequest();

    request.setAction(static_cast<cereal::SeatControlConfigRequest::ConfigAction>(action));
    request.setRequestId(++current_request_id);

    if (config && action == 1) { // set action
        auto config_data = request.initConfig();
        config_data.setFrequency(config->frequency);
        config_data.setTurnThresh1(config->turn_thresh_1);
        config_data.setTurnThresh2(config->turn_thresh_2);
        config_data.setLongThresh(config->long_thresh);
        config_data.setSmoothingWindow(config->smoothing_window);
        config_data.setHorizon(config->horizon);
        config_data.setUsePlan(config->use_plan);
        config_data.setTimestamp(nanos_since_boot());
    }

    pm->send("seatControlConfigRequest", msg);
    waiting_for_response = true;

    // Start the message timer only when we're waiting for a response
    if (!message_timer->isActive()) {
        message_timer->start();
    }

    // Show progress
    progress_bar->setVisible(true);
    progress_bar->setRange(0, 0); // Indeterminate progress

    // Timeout after 5 seconds
    QTimer::singleShot(5000, this, [this]() {
        if (waiting_for_response) {
            waiting_for_response = false;
            message_timer->stop(); // Stop checking for messages
            progress_bar->setVisible(false);
            showStatus("Request timed out", false);
        }
    });
}

void SeatControlConfigDialog::requestCurrentConfig() {
    showStatus("Loading current configuration...");
    sendConfigRequest(0); // get action
}

void SeatControlConfigDialog::saveConfig() {
    if (!isValidConfig()) {
        showStatus("Please fix validation errors before saving", false);
        return;
    }

    SeatControlConfig config = getConfig();
    showStatus("Saving configuration...");
    sendConfigRequest(1, &config); // set action
}

void SeatControlConfigDialog::resetToDefaults() {
    showStatus("Resetting to defaults...");
    sendConfigRequest(2); // reset action
}

void SeatControlConfigDialog::onConfigReceived(const SeatControlConfig &config) {
    waiting_for_response = false;
    progress_bar->setVisible(false);

    current_config = config;
    setConfig(config);
    showStatus("Configuration loaded successfully");

    emit configChanged(config);
}

void SeatControlConfigDialog::onValidationTimer() {
    validateInputs();
}

void SeatControlConfigDialog::validateInputs() {
    config_valid = isValidConfig();

    if (!config_valid) {
        validation_label->setText("⚠ Turn Threshold 2 must be greater than Turn Threshold 1");
        validation_label->show();
    } else {
        validation_label->hide();
    }

    button_box->button(QDialogButtonBox::Save)->setEnabled(config_valid);
}

bool SeatControlConfigDialog::isValidConfig() const {
    return turn_thresh_2_spin->value() > turn_thresh_1_spin->value();
}

void SeatControlConfigDialog::showStatus(const QString &message, bool success) {
    status_label->setText(message);
    status_label->setStyleSheet(QString("font-size: 14px; color: %1;")
                               .arg(success ? "#66cc66" : "#ff6666"));
}

void SeatControlConfigDialog::setControlsEnabled(bool enabled) {
    frequency_spin->setEnabled(enabled);
    turn_thresh_1_spin->setEnabled(enabled);
    turn_thresh_2_spin->setEnabled(enabled);
    long_thresh_spin->setEnabled(enabled);
    smoothing_window_spin->setEnabled(enabled);
    horizon_spin->setEnabled(enabled);
    use_plan_check->setEnabled(enabled);
    button_box->setEnabled(enabled);
    load_button->setEnabled(enabled);
    reset_button->setEnabled(enabled);
}

SeatControlConfig SeatControlConfigDialog::getConfig() const {
    SeatControlConfig config;
    config.frequency = frequency_spin->value();
    config.turn_thresh_1 = turn_thresh_1_spin->value();
    config.turn_thresh_2 = turn_thresh_2_spin->value();
    config.long_thresh = long_thresh_spin->value();
    config.smoothing_window = smoothing_window_spin->value();
    config.horizon = horizon_spin->value();
    config.use_plan = use_plan_check->isChecked();
    return config;
}

void SeatControlConfigDialog::setConfig(const SeatControlConfig &config) {
    frequency_spin->setValue(config.frequency);
    turn_thresh_1_spin->setValue(config.turn_thresh_1);
    turn_thresh_2_spin->setValue(config.turn_thresh_2);
    long_thresh_spin->setValue(config.long_thresh);
    smoothing_window_spin->setValue(config.smoothing_window);
    horizon_spin->setValue(config.horizon);
    use_plan_check->setChecked(config.use_plan);
}

// SeatControlConfigButton Implementation
SeatControlConfigButton::SeatControlConfigButton(QWidget *parent)
    : QPushButton(parent), seat_control_active(false), config_dialog(nullptr) {
    setFixedSize(seat_btn_size, seat_btn_size);

    // Load icons - using existing assets
    seat_icon = loadPixmap("../assets/icons/couch.svg", {seat_btn_size * 3/4, seat_btn_size * 3/4});
    config_icon = loadPixmap("../assets/icons/settings.png", {seat_btn_size / 4, seat_btn_size / 4});

    // Connect click to open dialog
    QObject::connect(this, &QPushButton::clicked, this, &SeatControlConfigButton::openConfigDialog);
}

void SeatControlConfigButton::updateState(const UIState &s) {
    // Check if seat control is active based on UI state
    // For now, assume it's always available
    seat_control_active = true;
    update();
}

void SeatControlConfigButton::openConfigDialog() {
    if (!config_dialog) {
        initializeDialog();
    }

    if (config_dialog) {
        config_dialog->requestCurrentConfig();
        config_dialog->exec();
    }
}

void SeatControlConfigButton::onConfigChanged(const SeatControlConfig &config) {
    current_config = config;
    // Optionally update button appearance based on config
    update();
}

void SeatControlConfigButton::paintEvent(QPaintEvent *event) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    // Draw button background
    QColor bg_color = seat_control_active ? QColor(0, 150, 255, 200) : QColor(100, 100, 100, 200);
    float opacity = (isDown() || !seat_control_active) ? 0.6 : 1.0;

    p.setOpacity(opacity);
    p.setPen(Qt::NoPen);
    p.setBrush(bg_color);
    p.drawEllipse(rect().center(), seat_btn_size / 2, seat_btn_size / 2);

    // Draw seat icon
    QPoint center = rect().center();
    p.drawPixmap(center - QPoint(seat_icon.width() / 2, seat_icon.height() / 2), seat_icon);

    // Draw small config icon in corner
    QPoint config_pos = center + QPoint(seat_btn_size / 4, seat_btn_size / 4);
    p.drawPixmap(config_pos - QPoint(config_icon.width() / 2, config_icon.height() / 2), config_icon);

    p.setOpacity(1.0);
}

void SeatControlConfigButton::initializeDialog() {
    config_dialog = new SeatControlConfigDialog(this);
    QObject::connect(config_dialog, &SeatControlConfigDialog::configChanged,
                     this, &SeatControlConfigButton::onConfigChanged);
}

// Utility functions for drawing
void drawSeatIcon(QPainter &p, const QPoint &center, const QBrush &bg, float opacity) {
    p.setOpacity(opacity);
    p.setBrush(bg);
    p.setPen(Qt::NoPen);

    // Draw simple seat outline
    p.drawRect(center.x() - 20, center.y() - 15, 40, 30);  // Seat base
    p.drawRect(center.x() - 20, center.y() - 25, 40, 10);  // Seat back
}

void drawConfigIcon(QPainter &p, const QPoint &center, const QBrush &bg, float opacity) {
    p.setOpacity(opacity);
    p.setBrush(bg);
    p.setPen(QPen(Qt::white, 2));

    // Draw simple gear/settings icon
    int radius = 8;
    p.drawEllipse(center, radius, radius);

    // Draw gear teeth
    for (int i = 0; i < 8; i++) {
        float angle = i * M_PI / 4;
        QPoint tooth(center.x() + (radius + 3) * cos(angle),
                    center.y() + (radius + 3) * sin(angle));
        p.drawLine(center, tooth);
    }
}
