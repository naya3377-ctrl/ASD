// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// An overlay scroll bar: a thin rounded thumb that appears while scrolling
// and fattens under the pointer.
ScrollBar {
    id: bar
    padding: 3
    contentItem: Rectangle {
        implicitWidth: bar.hovered || bar.pressed ? 8 : 5; implicitHeight: bar.hovered || bar.pressed ? 8 : 5
        radius: width/2
        color: Theme.ink
        opacity: bar.policy === ScrollBar.AlwaysOn || bar.active || bar.hovered ? (bar.pressed ? .5 : .32) : 0
        Behavior on opacity { NumberAnimation { duration: Theme.smooth } }
        Behavior on implicitWidth { NumberAnimation { duration: Theme.fast } }
    }
    background: Item { }
}
