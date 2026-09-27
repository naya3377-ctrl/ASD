// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Drop-down in a bordered white box with a square black arrow cell.
ComboBox {
    id: box
    implicitHeight: 36
    font.pixelSize: 13
    opacity: enabled ? 1 : .35
    contentItem: Text {
        leftPadding: 12; rightPadding: 8; text: box.displayText; font.family: box.font.family; font.pixelSize: box.font.pixelSize; font.weight: Font.Medium
        color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Rectangle {
        x: box.width-width; width: box.height; height: box.height; color: box.pressed || box.popup.visible ? Theme.yellow : Theme.lineStrong
        Icon { anchors.centerIn: parent; name: "down"; size: 14; tone: box.pressed || box.popup.visible ? Theme.black : (Theme.dark ? Theme.black : Theme.white) }
    }
    background: Rectangle {
        color: box.hovered ? Theme.hover : Theme.field
        border.width: Theme.border; border.color: box.visualFocus ? Theme.focusRing : Theme.lineStrong
    }
}
