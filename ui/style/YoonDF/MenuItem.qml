// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic as B
import "../.."
B.MenuItem {
    id: control
    implicitHeight: 28
    leftPadding: 10; rightPadding: 10
    font.pixelSize: 13
    opacity: enabled ? 1 : .4
    contentItem: Text {
        leftPadding: control.checkable ? 20 : 0
        text: control.text; font: control.font; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
        color: control.highlighted ? Theme.inkOnAccent : Theme.ink
    }
    indicator: Icon {
        x: control.leftPadding; anchors.verticalCenter: parent.verticalCenter
        visible: control.checkable && control.checked; name: "check"; size: 14
        tone: control.highlighted ? Theme.inkOnAccent : Theme.ink
    }
    arrow: Icon {
        x: control.width - width - 8; anchors.verticalCenter: parent.verticalCenter
        visible: !!control.subMenu; name: "right"; size: 12; tone: control.highlighted ? Theme.inkOnAccent : Theme.inkMuted
    }
    background: Rectangle {
        implicitWidth: 190
        radius: Theme.radiusSmall
        color: control.highlighted ? Theme.accent : "transparent"
    }
}
