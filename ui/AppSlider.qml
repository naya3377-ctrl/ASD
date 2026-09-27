// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A thin rounded track filled with the accent and a white round knob with a
// hairline edge.
Slider {
    id: slider
    implicitHeight: Theme.control
    background: Rectangle {
        x: slider.leftPadding; y: slider.topPadding + slider.availableHeight/2 - height/2
        width: slider.availableWidth; height: 4; radius: 2; color: Theme.line
        Rectangle { width: slider.visualPosition*parent.width; height: parent.height; radius: 2; color: Theme.accent }
    }
    handle: Rectangle {
        x: slider.leftPadding + slider.visualPosition*(slider.availableWidth-width); y: slider.topPadding + slider.availableHeight/2 - height/2
        width: 18; height: 18; radius: 9
        color: slider.pressed ? "#f0f1f3" : "#ffffff"
        border.color: slider.visualFocus ? Theme.focusRing : "#b8bcc2"; border.width: slider.visualFocus ? 2 : Theme.hairline
    }
}
