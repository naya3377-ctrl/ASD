// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A menu row: 32 px tall, the highlighted row on the quiet selection colour,
// a check mark for the chosen entry. A hidden row takes no space.
MenuItem {
    id: item
    implicitHeight: visible ? 32 : 0
    implicitWidth: leftPadding + rightPadding + label.implicitWidth + (checkable ? 20 : 0)
    leftPadding: checkable ? 30 : 12; rightPadding: 16
    font.family: Theme.family
    font.pixelSize: Theme.body
    contentItem: Text {
        id: label
        text: item.text.split("\t")[0]; font: item.font
        color: item.enabled ? Theme.ink : Theme.inkFaint
        verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        Text {
            // Keyboard shortcut after a tab, right-aligned in the row.
            visible: item.text.indexOf("\t") >= 0
            text: item.text.split("\t")[1] || ""
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            font.family: Theme.family; font.pixelSize: Theme.small; color: Theme.inkMuted
        }
    }
    indicator: Icon {
        visible: item.checkable && item.checked
        x: 9; anchors.verticalCenter: parent.verticalCenter; name: "check"; size: 15; tone: Theme.accent
    }
    arrow: Icon {
        visible: !!item.subMenu
        x: item.width - width - 8; anchors.verticalCenter: parent.verticalCenter; name: "right"; size: 13; tone: Theme.inkMuted
    }
    background: Rectangle {
        implicitWidth: 180
        radius: Theme.radius
        color: item.highlighted && item.enabled ? Theme.accentSoft : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.hoverMs } }
    }
}
