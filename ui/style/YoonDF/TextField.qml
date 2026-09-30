// SPDX-License-Identifier: AGPL-3.0-or-later
// Rounded field with the macOS focus glow.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.TextField {
    id: control
    implicitHeight: 36
    leftPadding: 10; rightPadding: 10
    font.pixelSize: 14
    color: Theme.ink
    placeholderTextColor: Theme.inkMuted
    selectionColor: Theme.selection; selectedTextColor: Theme.ink
    opacity: enabled ? 1 : .5
    background: Item {
        implicitWidth: 120
        Rectangle { anchors.fill: parent; anchors.margins: -3; radius: Theme.radius + 3; color: "transparent"; border.width: 3; border.color: Theme.tint(.35); visible: control.activeFocus }
        Rectangle { anchors.fill: parent; radius: Theme.radius; color: Theme.field; border.width: 1; border.color: control.activeFocus ? Theme.focusRing : Theme.lineStrong }
    }
}
