// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick

// A light grey rounded strip holding related buttons (modes, tools, zoom).
// The selected button inside shows as a white pill (ActionButton.segmented).
Rectangle {
    id: group
    default property alias content: row.data
    property int padding: 3
    implicitWidth: row.implicitWidth + 2*padding
    implicitHeight: row.implicitHeight + 2*padding
    radius: Theme.radius + 2
    color: Theme.surfaceAlt
    Row { id: row; x: group.padding; y: group.padding; spacing: 2 }
}
