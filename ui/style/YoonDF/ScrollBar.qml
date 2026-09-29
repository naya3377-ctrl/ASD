// SPDX-License-Identifier: AGPL-3.0-or-later
// Overlay scroll bar: a thin rounded thumb that shows while scrolling or
// hovered and widens under the pointer, as on macOS.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.ScrollBar {
    id: control
    padding: 2
    minimumSize: .06
    contentItem: Rectangle {
        implicitWidth: control.hovered || control.pressed ? 9 : 6
        implicitHeight: control.hovered || control.pressed ? 9 : 6
        radius: width / 2
        color: control.pressed ? Theme.inkMuted : Theme.inkFaint
        opacity: control.policy === B.ScrollBar.AlwaysOn || control.active || control.hovered ? .85 : 0
        Behavior on opacity { NumberAnimation { duration: Theme.reducedMotion ? 0 : 250 } }
        Behavior on implicitWidth { NumberAnimation { duration: Theme.motionFast } }
    }
    background: Item { }
}
