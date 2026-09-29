// SPDX-License-Identifier: AGPL-3.0-or-later
// Sheet: rounded panel with a soft shadow, title in semibold, buttons at the
// bottom right with the default action in the accent colour.
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.Dialog {
    id: control
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
    exit: Transition { } // Release popup/modal input immediately on close.
    padding: 20; topPadding: 8
    font.pixelSize: 13
    background: Item {
        SoftShadow { anchors.fill: parent; radius: Theme.radiusLarge; spread: 26; offsetY: 10 }
        Rectangle { anchors.fill: parent; radius: Theme.radiusLarge; color: Theme.dark ? "#2c2c2e" : "#ffffff"; border.width: 1; border.color: Theme.line }
    }
    header: Text {
        visible: control.title.length > 0
        text: control.title; padding: 20; bottomPadding: 6
        font.pixelSize: 15; font.weight: Font.DemiBold; color: Theme.ink; elide: Text.ElideRight
    }
    // Our DialogButtonBox, so standard buttons get the accent default action.
    footer: DialogButtonBox { visible: count > 0 }
    B.Overlay.modal: Rectangle { color: Theme.dark ? "#80000000" : "#33000000" }
}
