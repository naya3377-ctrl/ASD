// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A soft drop shadow made of a few translucent rounded layers, so it looks
// the same on every graphics backend (no shader effects needed).
Item {
    id: shade
    property real radius: Theme.radiusLarge
    property real spread: 10          // how far the shadow reaches
    property real offsetY: 4
    property real strength: Theme.dark ? .55 : .16
    Repeater {
        model: 4
        Rectangle {
            required property int index
            readonly property real grow: shade.spread * (index + 1) / 4
            x: -grow/2; y: -grow/2 + shade.offsetY * (index + 1) / 4
            width: shade.width + grow; height: shade.height + grow
            radius: shade.radius + grow/2
            color: Qt.rgba(0, 0, 0, shade.strength / (index + 2) / 2)
        }
    }
}
