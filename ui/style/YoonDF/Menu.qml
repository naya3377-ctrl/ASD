// SPDX-License-Identifier: AGPL-3.0-or-later
// Popover menu: rounded, soft shadow, accent highlight per row.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.Menu {
    id: control
    padding: 5
    implicitWidth: Math.max(200, contentWidth + leftPadding + rightPadding)
    delegate: MenuItem { }
    background: Item {
        implicitWidth: 200
        SoftShadow { anchors.fill: parent; radius: Theme.radius + 2; spread: 14; offsetY: 5 }
        Rectangle { anchors.fill: parent; radius: Theme.radius + 2; color: Theme.dark ? "#2c2c2e" : "#fbfbfd"; border.width: 1; border.color: Theme.line }
    }
}
