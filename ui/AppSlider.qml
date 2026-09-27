// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A hairline track, a solid rule for the value and a square handle that
// empties while it is held.
Slider {
    id: slider
    implicitHeight: 28
    background: Item {
        x: slider.leftPadding; y: slider.topPadding + slider.availableHeight/2 - height/2
        width: slider.availableWidth; height: Theme.borderStrong
        Rectangle { anchors.verticalCenter: parent.verticalCenter; width: parent.width; height: Theme.hairline; color: Theme.lineSoft }
        Rectangle { width: slider.visualPosition*parent.width; height: parent.height; color: Theme.ink }
    }
    handle: Rectangle {
        x: slider.leftPadding + slider.visualPosition*(slider.availableWidth-width); y: slider.topPadding + slider.availableHeight/2 - height/2
        width: 12; height: 12; color: slider.pressed ? Theme.surface : Theme.ink
        border.width: Theme.borderStrong; border.color: Theme.ink
    }
}
