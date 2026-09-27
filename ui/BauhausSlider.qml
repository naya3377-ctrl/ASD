// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Black track, blue fill, a yellow square handle that turns 45° while dragged.
Slider {
    id: slider
    implicitHeight: 28
    background: Item {
        x: slider.leftPadding; y: slider.topPadding + slider.availableHeight/2 - height/2
        width: slider.availableWidth; height: 6
        Rectangle { anchors.fill: parent; color: Theme.lineSoft; border.width: Theme.border; border.color: Theme.lineStrong }
        Rectangle { width: slider.visualPosition*parent.width; height: parent.height; color: Theme.blue; border.width: Theme.border; border.color: Theme.lineStrong }
    }
    handle: Rectangle {
        x: slider.leftPadding + slider.visualPosition*(slider.availableWidth-width); y: slider.topPadding + slider.availableHeight/2 - height/2
        width: 18; height: 18; color: Theme.yellow; border.width: Theme.border; border.color: Theme.black
        rotation: slider.pressed ? 45 : 0
        Behavior on rotation { NumberAnimation { duration: Theme.snap; easing.type: Easing.OutCubic } }
    }
}
