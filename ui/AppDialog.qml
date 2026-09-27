// SPDX-License-Identifier: AGPL-3.0-or-later
import QtQuick
import QtQuick.Controls

// Every dialog: a rounded sheet on a soft shadow, a quiet title, buttons at
// the lower right with the accepting one in indigo. It fades and settles in, and
// closes at once so the next click reaches the window.
Dialog {
    id: dialog
    padding: 22; topPadding: 12
    background: Block { fill: Theme.raised; radius: Theme.radiusLarge+2; shadow: "large"; outline: Theme.lineSoft }
    header: Item {
        implicitHeight: dialog.title.length > 0 ? 54 : 0
        visible: dialog.title.length > 0
        Text {
            x: 22; y: 22; width: parent.width-44; elide: Text.ElideRight
            text: dialog.title; font.family: Theme.family; font.pixelSize: Theme.title3; font.weight: Font.Bold
            color: Theme.ink
        }
    }
    footer: DialogButtonBox {
        visible: count > 0
        padding: 18; topPadding: 4; spacing: 8
        background: Item { }
        delegate: ActionButton {
            outlined: DialogButtonBox.buttonRole !== DialogButtonBox.AcceptRole
            primary: DialogButtonBox.buttonRole === DialogButtonBox.AcceptRole
            implicitWidth: Math.max(84, implicitContentWidth + 32)
        }
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.smooth; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: .96; to: 1; duration: Theme.smooth; easing.type: Easing.OutCubic }
    }
    Overlay.modal: Rectangle { color: Theme.scrim; Behavior on opacity { NumberAnimation { duration: Theme.smooth } } }
}
