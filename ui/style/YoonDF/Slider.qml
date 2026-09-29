// SPDX-License-Identifier: AGPL-3.0-or-later
// Thin rounded track, accent fill, white knob with a soft shadow.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.Slider {
    id: control
    implicitHeight: 28
    opacity: enabled ? 1 : .45
    background: Rectangle {
        x: control.leftPadding; y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 200; width: control.availableWidth; height: 4; radius: 2
        color: Theme.surfaceAlt
        Rectangle { width: control.visualPosition * parent.width; height: parent.height; radius: 2; color: Theme.accent }
    }
    handle: Item {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: 20; height: 20
        SoftShadow { anchors.fill: parent; radius: 10; spread: 4; offsetY: 1 }
        Rectangle { anchors.fill: parent; radius: 10; color: control.pressed ? "#f2f2f7" : "white"; border.width: 1; border.color: "#1f000000" }
    }
}
