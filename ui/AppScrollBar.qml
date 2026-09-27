// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A thin ink bar that shows while scrolling or under the pointer.
ScrollBar {
    id: bar
    padding: 2
    contentItem: Rectangle {
        implicitWidth: bar.pressed || bar.hovered ? 6 : 4; implicitHeight: bar.pressed || bar.hovered ? 6 : 4
        color: Theme.ink
        opacity: bar.policy === ScrollBar.AlwaysOn || bar.active || bar.hovered ? (bar.pressed ? 1 : .55) : 0
    }
    background: Item { }
}
