#pragma once

#include <QPushButton>
#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QCheckBox>
#include <QDialogButtonBox>
#include <QTimer>
#include <QProgressBar>
#include <memory>

#include "common/params.h"
#include "cereal/messaging/messaging.h"

#ifdef SUNNYPILOT
#include "selfdrive/ui/sunnypilot/ui.h"
#else
#include "selfdrive/ui/ui.h"
#endif

const int seat_btn_size = 140;

// Configuration structure
struct SeatControlConfig {
    int frequency = 20;
    double turn_thresh_1 = 1.0;
    double turn_thresh_2 = 2.5;
    double long_thresh = 1.0;
    int smoothing_window = 4;
    double horizon = 3.0;
    bool use_plan = false;
};

// Configuration Dialog for Seat Control Parameters
class SeatControlConfigDialog : public QDialog {
    Q_OBJECT

public:
    explicit SeatControlConfigDialog(QWidget *parent = nullptr);
    SeatControlConfig getConfig() const;
    void setConfig(const SeatControlConfig &config);

public slots:
    void requestCurrentConfig();
    void saveConfig();
    void resetToDefaults();
    void onConfigReceived(const SeatControlConfig &config);

signals:
    void configChanged(const SeatControlConfig &config);

private slots:
    void onValidationTimer();
    void validateInputs();

private:
    void setupUI();
    void setupMessaging();
    void sendConfigRequest(int action, const SeatControlConfig *config = nullptr);
    bool isValidConfig() const;
    void showStatus(const QString &message, bool success = true);
    void setControlsEnabled(bool enabled);

    // UI Components
    QVBoxLayout *main_layout;
    QLabel *title_label;
    QLabel *description_label;

    // Parameter inputs
    QSpinBox *frequency_spin;
    QDoubleSpinBox *turn_thresh_1_spin;
    QDoubleSpinBox *turn_thresh_2_spin;
    QDoubleSpinBox *long_thresh_spin;
    QSpinBox *smoothing_window_spin;
    QDoubleSpinBox *horizon_spin;
    QCheckBox *use_plan_check;

    // Control buttons
    QDialogButtonBox *button_box;
    QPushButton *reset_button;
    QPushButton *load_button;

    // Status components
    QLabel *status_label;
    QProgressBar *progress_bar;

    // Messaging
    std::unique_ptr<PubMaster> pm;
    std::unique_ptr<SubMaster> sm;
    QTimer *message_timer;
    QTimer *validation_timer;

    // State
    uint64_t current_request_id;
    bool waiting_for_response;
    SeatControlConfig current_config;

    // Validation
    QLabel *validation_label;
    bool config_valid;
};

// Button for opening Seat Control Configuration
class SeatControlConfigButton : public QPushButton {
    Q_OBJECT

public:
    explicit SeatControlConfigButton(QWidget *parent = nullptr);
    void updateState(const UIState &s);

private slots:
    void openConfigDialog();
    void onConfigChanged(const SeatControlConfig &config);

private:
    void paintEvent(QPaintEvent *event) override;
    void initializeDialog();

    Params params;
    SeatControlConfigDialog *config_dialog;
    QPixmap seat_icon;
    QPixmap config_icon;
    bool seat_control_active;
    SeatControlConfig current_config;
};

// Utility functions for drawing
void drawSeatIcon(QPainter &p, const QPoint &center, const QBrush &bg, float opacity = 1.0);
void drawConfigIcon(QPainter &p, const QPoint &center, const QBrush &bg, float opacity = 1.0);
