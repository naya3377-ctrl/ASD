// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A rounded track filled in indigo, with a white round knob on a soft shadow.
Slider {
    id: slider
    implicitHeight: 26
    background: Rectangle {
        x: slider.leftPadding; y: slider.topPadding + slider.availableHeight/2 - height/2
        width: slider.availableWidth; height: 4; radius: 2; color: Theme.line
        Rectangle { width: slider.visualPosition*parent.width; height: parent.height; radius: 2; color: Theme.accent }
    }
    handle: Item {
        x: slider.leftPadding + slider.visualPosition*(slider.availableWidth-width); y: slider.topPadding + slider.availableHeight/2 - height/2
        width: 18; height: 18
        Shadow { target: knob; level: "small" }
        Rectangle {
            id: knob; anchors.fill: parent; radius: 9; color: slider.pressed ? "#f1ede6" : "#ffffff"
            border.color: "#1a2a2420"; border.width: Theme.hairline
        }
    }
}
