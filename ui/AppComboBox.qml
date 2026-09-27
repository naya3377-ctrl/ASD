// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Drop-down in a thin frame; the list opens as a framed sheet with the
// chosen row inverted.
ComboBox {
    id: box
    implicitHeight: 34
    font.pixelSize: Theme.body
    opacity: enabled ? 1 : .3
    contentItem: Text {
        leftPadding: 12; rightPadding: 8; text: box.displayText; font: box.font
        color: Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
    }
    indicator: Icon {
        x: box.width-width-10; y: (box.height-height)/2; name: "down"; size: 14; tone: Theme.ink
        rotation: box.popup.visible ? 180 : 0
    }
    background: Rectangle {
        color: box.hovered || box.popup.visible ? Theme.hover : Theme.field
        border.width: box.visualFocus || box.popup.visible ? Theme.borderStrong : Theme.border; border.color: Theme.lineStrong
    }
    delegate: ItemDelegate {
        required property var modelData; required property int index
        width: box.width; height: 34
        highlighted: box.highlightedIndex === index
        contentItem: Text {
            text: typeof parent.modelData === "string" ? parent.modelData : box.textAt(parent.index); font: box.font
            color: parent.highlighted ? Theme.inkOnAccent : Theme.ink; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        background: Rectangle { color: parent.highlighted ? Theme.accent : "transparent" }
    }
    popup.background: Block { fill: Theme.surface }
}
