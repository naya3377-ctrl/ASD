// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A flat surface drawn with a line: no shadow, no radius. Depth comes from
// the weight of the line and from inversion, not from elevation.
Rectangle {
    property color fill: Theme.raised
    property color outline: Theme.lineStrong
    property int outlineWidth: Theme.border
    color: fill
    border.color: outline; border.width: outlineWidth
}
