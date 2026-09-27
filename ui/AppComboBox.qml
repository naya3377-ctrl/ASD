// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// A macOS pop-up button: a raised bezel with a chevron; the list opens as a
// rounded menu with the highlighted row in indigo.
ComboBox {
    id: box
    implicitHeight: 30
    font.family: Theme.family
    font.pixelSize: Theme.body
    opacity: enabled ? 1 : .38
    contentItem: Text {
        leftPadding: 11; rightPadding: 8; text: box.displayText; font: box.font
        color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Icon {
        x: box.width-width-9; y: (box.height-height)/2; name: "down"; size: 13; tone: Theme.inkMuted
    }
    background: Item {
        Shadow { target: bezel; level: "small"; opacity: .7 }
        Rectangle {
            id: bezel; anchors.fill: parent; radius: Theme.radius
            color: box.pressed ? Qt.darker(Theme.raised, 1.05) : Theme.raised
            border.width: Theme.hairline; border.color: box.visualFocus ? Theme.focusRing : Theme.line
        }
    }
    delegate: ItemDelegate {
        required property var modelData; required property int index
        width: box.popup.availableWidth; height: 30
        highlighted: box.highlightedIndex === index
        contentItem: Text {
            text: typeof parent.modelData === "string" ? parent.modelData : box.textAt(parent.index); font: box.font
            color: parent.highlighted ? Theme.inkOnAccent : Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        background: Rectangle { radius: Theme.radiusSmall; color: parent.highlighted ? Theme.accent : "transparent" }
    }
    popup.padding: 5
    popup.background: Block { fill: Theme.raised; radius: Theme.radius+2; shadow: "medium" }
}
