from __future__ import annotations

EDITOR_STYLESHEET = """
            QMainWindow, QWidget {
                background: #0e0e0e;
                color: #e7e5e5;
            }
            QStackedWidget#contentStack, QWidget#editorPage {
                background: transparent;
            }
            QFrame#topBar, QFrame#footerBar {
                background: #050505;
                border: none;
            }
            QLabel#topTitle {
                color: #f1f5f9;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#topHint {
                color: #6b7280;
                font-weight: 700;
            }
            QFrame#leftSidebar {
                background: #020202;
                border-right: 1px solid rgba(71, 72, 72, 0.18);
            }
            QLabel#sidebarTitle {
                font-weight: 800;
                color: #f4f4f5;
            }
            QLabel#sidebarSubtitle {
                color: #60a5fa;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QPushButton[navActive="true"], QPushButton[navActive="false"] {
                min-height: 44px;
                border-radius: 8px;
                border: none;
                text-align: left;
                padding: 0 14px;
                font-weight: 700;
                background: transparent;
            }
            QPushButton[navActive="true"] {
                background: #1a1d22;
                color: #60a5fa;
            }
            QPushButton[navActive="false"] {
                background: transparent;
                color: #737373;
            }
            QPushButton[navActive="false"]:hover:enabled {
                background: #111214;
                color: #e7e5e5;
            }
            QPushButton[navImplemented="false"] {
                color: #4b5563;
            }
            QFrame#sidebarDivider {
                background: rgba(71, 72, 72, 0.18);
                border: none;
                margin: 6px 0 8px 0;
            }
            QPushButton[sidebarUtility="true"] {
                min-height: 40px;
                border-radius: 8px;
                border: none;
                text-align: left;
                padding: 0 14px;
                font-weight: 700;
                background: transparent;
            }
            QPushButton[sidebarUtility="true"]:disabled {
                color: #6f747b;
                background: transparent;
            }
            QFrame#previewPanel {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.9, fx:0.5, fy:0.5,
                    stop:0 #191a1a, stop:1 #0a0a0a);
            }
            QLabel#sectionTitle, QLabel#panelTitle {
                font-weight: 800;
                color: #f4f4f5;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLabel#sectionSubtitle, QLabel#fileInfo {
                color: #a3a3a3;
            }
            QFrame#rightPanel, QFrame#batchRightPanel {
                background: #131313;
                border-left: 1px solid rgba(71, 72, 72, 0.15);
            }
            QFrame#rightHeader, QFrame#actionPanel {
                background: transparent;
                border: none;
            }
            QLabel#metaLabel, QLabel#batchEyebrow {
                color: #9f9d9d;
                font-weight: 800;
                letter-spacing: 2px;
                text-transform: uppercase;
            }
            QLabel#batchEyebrow {
                color: #848a91;
            }
            QFrame#imageInfoCard {
                background: transparent;
                border: none;
                border-radius: 0;
            }
            QLabel#imageSectionTitle {
                color: #f4f4f5;
                font-weight: 700;
            }
            QLabel#pathLabel, QLabel#pathBoxLabel {
                color: #b7bcc3;
                background: transparent;
            }
            QPushButton#secondaryButton, QPushButton#primaryButton, QPushButton#dangerButton {
                min-height: 44px;
                border-radius: 8px;
                font-weight: 800;
                border: none;
                padding: 0 16px;
            }
            QPushButton#secondaryButton {
                background: #252626;
                color: #e7e5e5;
            }
            QPushButton#secondaryButton:hover {
                background: #2b2c2c;
            }
            QPushButton#secondaryButton:disabled, QPushButton#dangerButton:disabled {
                background: #1d1d1d;
                color: #5f6368;
            }
            QPushButton#dangerButton {
                background: #241717;
                color: #ee7d77;
            }
            QPushButton#dangerButton:hover:enabled {
                background: #2f1b1b;
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a3c9ff, stop:1 #004883);
                color: #e7f1ff;
            }
            QPushButton#primaryButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #bcd6ff, stop:1 #0a5ea8);
            }
            QPushButton#primaryButton:disabled {
                background: #3b3b3b;
                color: #757575;
            }
            QLabel#statusLabel {
                color: #67e8f9;
                font-weight: 700;
            }
            QLabel#footerMeta {
                color: #737373;
                font-weight: 600;
                padding-left: 18px;
            }
            QScrollArea#previewScroll, QScrollArea#batchCardsScroll,
            QScrollArea#rightPanelScroll, QScrollArea#templateLibraryScroll,
            QScrollArea#settingsScroll {
                border: none;
                background: transparent;
            }
            QFrame#templateLibraryPage, QWidget#templateLibraryContent {
                background: #0e0e0e;
            }
            QLabel#templateLibraryHeading {
                color: #e7e5e5;
                font-weight: 900;
                letter-spacing: -1px;
            }
            QLabel#templateLibrarySubtitle, QLabel#templateLibraryMeta {
                color: #9f9d9d;
                line-height: 1.4;
            }
            QLabel#templateLibraryMeta {
                font-weight: 700;
            }
            QFrame#settingsPage, QWidget#settingsContent {
                background: #0e0e0e;
            }
            QLabel#settingsHeading {
                color: #e7e5e5;
                font-weight: 900;
                letter-spacing: -1px;
            }
            QLabel#settingsSubtitle {
                color: #9f9d9d;
                line-height: 1.4;
            }
            QFrame#settingsCard {
                background: #131313;
                border-radius: 12px;
                border: 1px solid rgba(71, 72, 72, 0.12);
            }
            QLabel#settingsCardTitle, QLabel#settingsToggleTitle {
                color: #f4f4f5;
                font-weight: 700;
            }
            QLabel#settingsHint {
                color: #7f848d;
                line-height: 1.45;
            }
            QPushButton#settingsToggle {
                border: none;
                border-radius: 16px;
                padding: 0 14px;
                background: #252626;
                color: #9f9d9d;
                font-weight: 800;
            }
            QPushButton#settingsToggle:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a3c9ff, stop:1 #004883);
                color: #e7f1ff;
            }
            QFrame#settingsLogoCard {
                background: #111214;
                border-radius: 10px;
                border: 1px solid rgba(71, 72, 72, 0.12);
            }
            QLabel#settingsLogoPreview {
                background: transparent;
                color: #6f747b;
            }
            QLabel#settingsLogoName {
                color: #b7bcc3;
                font-weight: 700;
            }
            QFrame#templateLibraryCard {
                background: transparent;
                border: none;
            }
            QFrame#templateLibraryPreviewFrame {
                background: #131313;
                border-radius: 8px;
                border: 1px solid transparent;
            }
            QFrame#templateLibraryCard:hover QFrame#templateLibraryPreviewFrame {
                background: #191a1a;
                border: 1px solid rgba(71, 72, 72, 0.28);
            }
            QFrame#templateLibraryCard[cardSelected="true"] QFrame#templateLibraryPreviewFrame {
                background: #1f2020;
                border: 1px solid rgba(163, 201, 255, 0.58);
            }
            QLabel#templateLibraryThumbnail {
                background: #050505;
                border-radius: 6px;
                color: #6b7280;
                font-weight: 700;
            }
            QLabel#templateLibraryTitle {
                color: #e7e5e5;
                font-weight: 700;
            }
            QFrame#templateLibraryCard[cardSelected="true"] QLabel#templateLibraryTitle {
                color: #a3c9ff;
            }
            QLabel#templateLibraryBadge {
                color: #83fff6;
                background: rgba(131, 255, 246, 0.08);
                border-radius: 8px;
                padding: 4px 8px;
                font-weight: 800;
            }
            QFrame#createTemplateCard {
                background: #191a1a;
                border-radius: 8px;
                border: 1px dashed rgba(117, 117, 117, 0.35);
            }
            QFrame#createTemplateCard:hover {
                background: #1f2020;
                border: 1px dashed rgba(163, 201, 255, 0.55);
            }
            QLabel#createTemplatePlus {
                color: #757575;
                font-weight: 300;
            }
            QFrame#createTemplateCard:hover QLabel#createTemplatePlus {
                color: #a3c9ff;
            }
            QLabel#createTemplateText {
                color: #9f9d9d;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#createTemplateHint {
                color: #6b7280;
            }
            QFrame#batchWorkspace {
                background: #101010;
            }
            QFrame#batchProgressCard {
                background: #111214;
                border-radius: 8px;
                border: 1px solid rgba(71, 72, 72, 0.12);
            }
            QLabel#progressCounter, QLabel#qualityValue {
                color: #83fff6;
                font-weight: 700;
            }
            QLabel#sliderHint, QLabel#batchDetailLabel {
                color: #7f848d;
            }
            QFrame#pathBox {
                background: #0a0b0b;
                border: 1px solid rgba(71, 72, 72, 0.12);
                border-radius: 8px;
            }
            QComboBox#batchCombo {
                min-height: 42px;
                border-radius: 8px;
                padding: 0 14px;
                background: #252626;
                color: #e7e5e5;
                border: 1px solid rgba(163, 201, 255, 0.35);
            }
            QComboBox#batchCombo:hover {
                background: #2b2c2c;
            }
            QComboBox#batchCombo::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox#batchCombo::down-arrow {
                image: none;
                width: 0;
                height: 0;
            }
            QSlider {
                min-height: 24px;
                background: transparent;
            }
            QSlider::groove:horizontal {
                height: 8px;
                margin: 0 2px;
                background: #1a1c1f;
                border: 1px solid rgba(71, 72, 72, 0.24);
                border-radius: 4px;
            }
            QSlider::sub-page:horizontal {
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #004883, stop:1 #83fff6);
                border: 1px solid rgba(131, 255, 246, 0.18);
                border-radius: 4px;
            }
            QSlider::add-page:horizontal {
                height: 8px;
                background: #202225;
                border: 1px solid rgba(71, 72, 72, 0.16);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 18px;
                margin: -7px 0;
                border-radius: 9px;
                background: qradialgradient(cx:0.5, cy:0.45, radius:0.8, fx:0.5, fy:0.35,
                    stop:0 #d3e3ff, stop:0.55 #a3c9ff, stop:1 #5f97dc);
                border: 2px solid #0e0e0e;
            }
            QSlider::handle:horizontal:hover {
                background: qradialgradient(cx:0.5, cy:0.45, radius:0.8, fx:0.5, fy:0.35,
                    stop:0 #e5efff, stop:0.55 #bcd6ff, stop:1 #73a8ea);
            }
            QSlider::sub-page:horizontal:disabled {
                background: #35506f;
                border: 1px solid rgba(53, 80, 111, 0.22);
            }
            QSlider::add-page:horizontal:disabled {
                background: #1a1b1d;
                border: 1px solid rgba(53, 56, 61, 0.2);
            }
            QSlider::handle:horizontal:disabled {
                background: #4d535b;
                border: 2px solid #131313;
            }
            QProgressBar#batchOverallProgress {
                min-height: 6px;
                background: #252626;
                border: none;
                border-radius: 3px;
            }
            QProgressBar#batchOverallProgress::chunk {
                background: #a3c9ff;
                border-radius: 3px;
            }
            QLabel#batchEmptyLabel {
                color: #6f747b;
                background: #111214;
                border-radius: 8px;
                border: 1px dashed rgba(127, 132, 141, 0.25);
                padding: 28px;
            }
            QFrame#batchCard {
                background: #151515;
                border: 1px solid transparent;
                border-radius: 8px;
            }
            QFrame#batchCard:hover {
                background: #181919;
            }
            QFrame#batchCard[cardSelected="true"] {
                background: #191b1e;
                border: 1px solid rgba(163, 201, 255, 0.45);
            }
            QFrame#batchCard[batchState="processing"] {
                background: #14181a;
            }
            QFrame#batchCard[batchState="success"] {
                background: #15191a;
            }
            QFrame#batchCard[batchState="failed"] {
                background: #1a1414;
            }
            QFrame#batchPreviewFrame {
                background: #f4f4f5;
                border-radius: 6px;
            }
            QFrame#batchCard[batchState="processing"] QFrame#batchPreviewFrame {
                background: #182024;
            }
            QLabel#batchThumbnail {
                background: #f4f4f5;
                border-radius: 4px;
            }
            QToolButton#batchRemoveButton {
                background: #5b1f21;
                color: #ffe6e5;
                border: 1px solid rgba(238, 125, 119, 0.28);
                border-radius: 6px;
                padding: 0;
                font-weight: 800;
            }
            QToolButton#batchRemoveButton:hover {
                background: #6d2629;
                color: #fff2f1;
            }
            QToolButton#batchRemoveButton:pressed {
                background: #491719;
            }
            QToolButton#batchRemoveButton:disabled {
                background: #241717;
                color: #77514f;
                border: 1px solid rgba(119, 81, 79, 0.25);
            }
            QLabel#batchFileName {
                color: #f4f4f5;
                font-weight: 700;
            }
            QLabel#batchMeta {
                color: #8f959c;
            }
"""
